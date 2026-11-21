"""Core data types for LeadGuard.

The package deliberately uses only the Python standard library so judges can
run it without installing a dependency tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SecurityType(str, Enum):
    STOCK = "STOCK"
    OPTION = "OPTION"


class Action(str, Enum):
    HOLD = "HOLD"
    RECONCILE = "RECONCILE"
    BUY_CALL_SPREAD = "BUY_CALL_SPREAD"
    BUY_PUT_SPREAD = "BUY_PUT_SPREAD"
    CLOSE = "CLOSE"


@dataclass
class Quote:
    symbol: str
    close: float
    prev_close: float
    day_high: float | None = None
    day_low: float | None = None
    high_20d: float | None = None
    low_20d: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    rsi14: float | None = None
    atr14: float | None = None
    realized_vol20_annual_pct: float | None = None
    as_of: str = ""

    @property
    def change_pct(self) -> float:
        if not self.prev_close:
            return 0.0
        return (self.close / self.prev_close - 1.0) * 100.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["change_pct"] = round(self.change_pct, 2)
        return data


@dataclass
class Position:
    symbol: str
    sec_type: SecurityType
    qty: float
    avg_cost: float = 0.0
    last: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    verified: bool = True
    note: str = ""

    @property
    def is_short_stock(self) -> bool:
        return self.sec_type is SecurityType.STOCK and self.qty < 0

    @property
    def days_to_expiry(self) -> int | None:
        if not self.expiry:
            return None
        exp = date.fromisoformat(self.expiry)
        return (exp - date.today()).days

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sec_type"] = self.sec_type.value
        data["is_short_stock"] = self.is_short_stock
        data["days_to_expiry"] = self.days_to_expiry
        return data


@dataclass
class Account:
    nav: float
    peak_nav: float
    cash: float
    day_pnl: float = 0.0
    positions: list[Position] = field(default_factory=list)
    account_id: str = ""
    as_of: str = ""
    source: str = ""

    @property
    def drawdown_pct(self) -> float:
        if self.peak_nav <= 0:
            return 0.0
        return max(0.0, (self.peak_nav - self.nav) / self.peak_nav * 100.0)

    @property
    def cash_pct(self) -> float:
        if self.nav <= 0:
            return 0.0
        return self.cash / self.nav * 100.0

    @property
    def gross_exposure(self) -> float:
        return sum(abs(p.market_value) for p in self.positions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "as_of": self.as_of,
            "source": self.source,
            "nav": round(self.nav, 2),
            "peak_nav": round(self.peak_nav, 2),
            "cash": round(self.cash, 2),
            "cash_pct": round(self.cash_pct, 2),
            "day_pnl": round(self.day_pnl, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "gross_exposure": round(self.gross_exposure, 2),
            "positions": [p.to_dict() for p in self.positions],
        }


@dataclass
class Leg:
    symbol: str
    side: Side
    qty: int
    limit_price: float
    sec_type: SecurityType = SecurityType.OPTION
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side"] = self.side.value
        data["sec_type"] = self.sec_type.value
        return data


@dataclass
class Proposal:
    action: Action
    symbol: str
    legs: list[Leg] = field(default_factory=list)
    max_loss: float = 0.0
    risk_pct: float = 0.0
    target_debit: float | None = None
    max_debit: float | None = None
    expiry: str | None = None
    dte: int | None = None
    thesis: str = ""
    invalidation: str = ""
    bid_ask_pct: float | None = None
    close_only: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "symbol": self.symbol,
            "legs": [leg.to_dict() for leg in self.legs],
            "max_loss": round(self.max_loss, 2),
            "risk_pct": round(self.risk_pct, 2),
            "target_debit": self.target_debit,
            "max_debit": self.max_debit,
            "expiry": self.expiry,
            "dte": self.dte,
            "thesis": self.thesis,
            "invalidation": self.invalidation,
            "bid_ask_pct": self.bid_ask_pct,
            "close_only": self.close_only,
            "reason": self.reason,
        }


@dataclass
class RiskCheck:
    name: str
    passed: bool
    detail: str = ""
    hard: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskResult:
    approved: bool
    checks: list[RiskCheck]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "checks": [c.to_dict() for c in self.checks],
            "blockers": self.blockers,
            "warnings": self.warnings,
        }


@dataclass
class Decision:
    decision_id: str
    ts_utc: str
    ts_et: str
    mode: str
    agent: str
    account_id: str
    nav: float
    peak_nav: float
    drawdown_pct: float
    regime: str
    signal: dict[str, Any]
    proposal: Proposal
    risk: RiskResult
    executed: bool = False
    orders: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "ts_utc": self.ts_utc,
            "ts_et": self.ts_et,
            "mode": self.mode,
            "agent": self.agent,
            "account_id": self.account_id,
            "nav": round(self.nav, 2),
            "peak_nav": round(self.peak_nav, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "regime": self.regime,
            "signal": self.signal,
            "proposal": self.proposal.to_dict(),
            "risk": self.risk.to_dict(),
            "executed": self.executed,
            "orders": self.orders,
            "note": self.note,
        }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
