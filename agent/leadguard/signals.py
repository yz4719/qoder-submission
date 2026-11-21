"""Deterministic signal generation and proposal construction.

The agent is intentionally rule-based at the point of execution.  The LLM
researcher can add context, but it cannot bypass these gates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .config import Config
from .market import MarketSnapshot
from .models import (
    Account,
    Action,
    Leg,
    Position,
    Proposal,
    SecurityType,
    Side,
)


EXPIRY = "2026-12-18"


@dataclass
class Signal:
    bias: str
    score: int
    regime: str
    reasons: list[str] = field(default_factory=list)
    invalidation: str = ""
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bias": self.bias,
            "score": self.score,
            "regime": self.regime,
            "reasons": self.reasons,
            "invalidation": self.invalidation,
            "blockers": self.blockers,
        }


def evaluate(snapshot: MarketSnapshot, config: Config, account: Account | None = None) -> Signal:
    spy, qqq = snapshot.spy, snapshot.qqq
    vix = snapshot.vix
    triggers = config.triggers
    reasons: list[str] = [
        f"VIX {vix:.2f} -> {snapshot.regime}",
        f"SPY {spy.close:.2f} ({spy.change_pct:+.2f}%), QQQ {qqq.close:.2f} ({qqq.change_pct:+.2f}%)",
        f"trend={snapshot.trend}; breadth_proxy={snapshot.breadth_proxy:+.2f}pp",
    ]
    blockers: list[str] = []

    if account is not None:
        unverified = [p.symbol for p in account.positions if not p.verified]
        short_stock = [p.symbol for p in account.positions if p.is_short_stock]
        expiring = [
            p.symbol
            for p in account.positions
            if p.sec_type is SecurityType.OPTION and (p.days_to_expiry is not None and p.days_to_expiry <= 2)
        ]
        if unverified:
            blockers.append(f"unverified positions: {', '.join(unverified)}")
        if short_stock:
            blockers.append(f"short stock must be covered first: {', '.join(short_stock)}")
        if expiring:
            blockers.append(f"option at or near expiry: {', '.join(expiring)}")

    long_ok = (
        spy.close >= triggers["spy_long"]
        and qqq.close >= triggers["qqq_long"]
        and vix <= triggers["vix_long_max"]
    )
    short_ok = (
        spy.close <= triggers["spy_short"]
        and qqq.close <= triggers["qqq_short"]
        and vix >= triggers["vix_short_min"]
    )

    if long_ok and not short_ok:
        reasons.append(
            f"long confirmation: SPY >= {triggers['spy_long']:.2f}, "
            f"QQQ >= {triggers['qqq_long']:.2f}, VIX <= {triggers['vix_long_max']:.2f}"
        )
        return Signal(
            bias="long",
            score=72,
            regime=snapshot.regime,
            reasons=reasons,
            invalidation=(
                f"SPY closes below {spy.day_low or 686.75:.2f} or VIX > 40; "
                "close the spread at -50% of debit, whichever comes first"
            ),
            blockers=blockers,
        )

    if short_ok:
        reasons.append(
            f"breakdown confirmation: SPY <= {triggers['spy_short']:.2f}, "
            f"QQQ <= {triggers['qqq_short']:.2f}, VIX >= {triggers['vix_short_min']:.2f}"
        )
        return Signal(
            bias="short",
            score=70,
            regime=snapshot.regime,
            reasons=reasons,
            invalidation=(
                f"SPY reclaims {spy.sma20 or 700:.2f} or VIX < 30; "
                "close the spread at -50% of debit, whichever comes first"
            ),
            blockers=blockers,
        )

    reasons.append("no confirmed edge: wait for a reclaim or a breakdown; cash is a position")
    return Signal(
        bias="flat",
        score=0,
        regime=snapshot.regime,
        reasons=reasons,
        invalidation="re-evaluate after the first 30 minutes of the next session",
        blockers=blockers,
    )


def build_proposal(
    signal: Signal,
    snapshot: MarketSnapshot,
    account: Account,
    config: Config,
) -> Proposal:
    if signal.blockers:
        return Proposal(
            action=Action.RECONCILE,
            symbol="PORTFOLIO",
            reason="; ".join(signal.blockers),
            thesis="Reconcile the account before any new risk.",
            invalidation="A verified flat/reconciled position list is required.",
            close_only=True,
        )

    if signal.bias == "flat":
        return Proposal(
            action=Action.HOLD,
            symbol="CASH",
            reason="No confirmed edge. Preserve capital and wait.",
            thesis="The account already has a large realized edge; the marginal trade must clear a high bar.",
            invalidation=signal.invalidation,
        )

    nav = account.nav
    risk_budget = nav * config.risk["max_premium_at_risk_pct_per_trade"] / 100.0
    max_contracts = int(config.risk["max_contracts_per_spread"])

    if signal.bias == "long":
        key = "SPY_CALL_700_720"
        debit = snapshot.option_debit(key, default=8.0)
        assert debit is not None
        qty = min(max_contracts, math.floor(risk_budget / (debit * 100.0)))
        if qty < 1:
            return _too_expensive("SPY call spread", debit, risk_budget, signal)
        max_loss = qty * debit * 100.0
        legs = [
            Leg(
                symbol=option_symbol("SPY", EXPIRY, "C", 700),
                side=Side.BUY,
                qty=qty,
                limit_price=round(debit, 2),
                note="net debit; replace with live ask",
            ),
            Leg(
                symbol=option_symbol("SPY", EXPIRY, "C", 720),
                side=Side.SELL,
                qty=qty,
                limit_price=0.01,
                note="PLACEHOLDER; replace with live bid before paper execution",
            ),
        ]
        return Proposal(
            action=Action.BUY_CALL_SPREAD,
            symbol="SPY",
            legs=legs,
            max_loss=max_loss,
            risk_pct=max_loss / nav * 100.0,
            target_debit=round(debit, 2),
            max_debit=round(risk_budget / (qty * 100.0), 2),
            expiry=EXPIRY,
            dte=_dte(snapshot.as_of),
            thesis=(
                "Post-capitulation reclaim: SPY/QQQ confirm stabilization and VIX cools. "
                "Defined-risk call spread caps the loss if the bounce fails."
            ),
            invalidation=signal.invalidation,
            bid_ask_pct=snapshot.option_debit("SPY_CALL_BID_ASK_PCT", default=4.0),
        )

    key = "SPY_PUT_680_660"
    debit = snapshot.option_debit(key, default=8.0)
    assert debit is not None
    qty = min(max_contracts, math.floor(risk_budget / (debit * 100.0)))
    if qty < 1:
        return _too_expensive("SPY put spread", debit, risk_budget, signal)
    max_loss = qty * debit * 100.0
    legs = [
        Leg(
            symbol=option_symbol("SPY", EXPIRY, "P", 680),
            side=Side.BUY,
            qty=qty,
            limit_price=round(debit, 2),
            note="net debit; replace with live ask",
        ),
        Leg(
            symbol=option_symbol("SPY", EXPIRY, "P", 660),
            side=Side.SELL,
            qty=qty,
            limit_price=0.01,
            note="PLACEHOLDER; replace with live bid before paper execution",
        ),
    ]
    return Proposal(
        action=Action.BUY_PUT_SPREAD,
        symbol="SPY",
        legs=legs,
        max_loss=max_loss,
        risk_pct=max_loss / nav * 100.0,
        target_debit=round(debit, 2),
        max_debit=round(risk_budget / (qty * 100.0), 2),
        expiry=EXPIRY,
        dte=_dte(snapshot.as_of),
        thesis=(
            "Breakdown continuation: SPY loses Friday's low while VIX stays elevated. "
            "Defined-risk put spread participates without naked short exposure."
        ),
        invalidation=signal.invalidation,
        bid_ask_pct=snapshot.option_debit("SPY_PUT_BID_ASK_PCT", default=5.0),
    )


def _too_expensive(name: str, debit: float, risk_budget: float, signal: Signal) -> Proposal:
    return Proposal(
        action=Action.HOLD,
        symbol="CASH",
        reason=f"{name} debit {debit:.2f} is too high for the 1-contract risk budget {risk_budget:.2f}",
        thesis="Skip rather than oversize.",
        invalidation=signal.invalidation,
    )


def option_symbol(root: str, expiry: str, right: str, strike: float) -> str:
    """Build a Moomoo-style US option symbol, e.g. US.SPY261218C700000."""
    yymmdd = expiry[2:4] + expiry[5:7] + expiry[8:10]
    return f"US.{root}{yymmdd}{right.upper()}{int(round(strike * 1000)):08d}"


def _dte(as_of: str) -> int:
    day = date.fromisoformat(as_of[:10])
    return (date.fromisoformat(EXPIRY) - day).days
