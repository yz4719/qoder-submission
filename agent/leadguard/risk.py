"""Hard risk gates.

Every check is explicit and logged.  A failed hard check blocks the order; the
LLM cannot override it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .config import Config
from .models import (
    Account,
    Action,
    Proposal,
    RiskCheck,
    RiskResult,
    SecurityType,
)


ET = ZoneInfo("America/New_York")


@dataclass
class RiskContext:
    now_et: datetime
    trades_today: int = 0
    open_positions: int | None = None

    @classmethod
    def at(cls, now_et: datetime | None = None, trades_today: int = 0) -> "RiskContext":
        if now_et is None:
            now_et = datetime.now(ET)
        elif now_et.tzinfo is None:
            now_et = now_et.replace(tzinfo=ET)
        else:
            now_et = now_et.astimezone(ET)
        return cls(now_et=now_et, trades_today=trades_today)


def check(
    proposal: Proposal,
    account: Account,
    config: Config,
    ctx: RiskContext | None = None,
) -> RiskResult:
    ctx = ctx or RiskContext.at()
    checks: list[RiskCheck] = []
    blockers: list[str] = []
    warnings: list[str] = []

    def add(name: str, passed: bool, detail: str, hard: bool = True) -> None:
        checks.append(RiskCheck(name=name, passed=passed, detail=detail, hard=hard))
        if not passed:
            if hard:
                blockers.append(f"{name}: {detail}")
            else:
                warnings.append(f"{name}: {detail}")

    if proposal.action in {Action.HOLD, Action.RECONCILE}:
        add("trade_proposal", False, f"{proposal.action.value}: no order to approve", hard=False)
        return RiskResult(approved=False, checks=checks, blockers=blockers, warnings=warnings)

    risk = config.risk
    nav = account.nav

    unverified = [p.symbol for p in account.positions if not p.verified]
    add("positions_reconciled", not unverified, f"unverified={unverified}" if unverified else "all positions verified")

    short_stock = [p.symbol for p in account.positions if p.is_short_stock]
    add("no_short_stock", not short_stock, f"short stock={short_stock}" if short_stock else "no short stock")

    expiring = [
        p.symbol
        for p in account.positions
        if p.sec_type is SecurityType.OPTION and (p.days_to_expiry is not None and p.days_to_expiry <= 2)
    ]
    add("no_expiring_options", not expiring, f"expiring={expiring}" if expiring else "no option with DTE <= 2")

    add(
        "kill_switch",
        account.drawdown_pct < risk["kill_switch_drawdown_pct"],
        f"drawdown={account.drawdown_pct:.2f}% < kill={risk['kill_switch_drawdown_pct']:.2f}%",
    )
    add(
        "soft_stop",
        account.drawdown_pct < risk["soft_stop_drawdown_pct"],
        f"drawdown={account.drawdown_pct:.2f}% < soft={risk['soft_stop_drawdown_pct']:.2f}%",
    )
    daily_limit = nav * risk["daily_loss_limit_pct"] / 100.0
    add(
        "daily_loss",
        account.day_pnl > -daily_limit,
        f"day_pnl={account.day_pnl:.2f} vs limit={-daily_limit:.2f}",
    )

    add(
        "blocked_symbol",
        proposal.symbol.upper() not in config.blocked_symbols,
        f"symbol={proposal.symbol} blocked={sorted(config.blocked_symbols)}",
    )

    projected_gross = account.gross_exposure + proposal.max_loss
    max_gross = nav * risk["max_gross_exposure_pct"] / 100.0
    add(
        "gross_exposure",
        projected_gross <= max_gross,
        f"projected={projected_gross:.2f} <= max={max_gross:.2f}",
    )

    max_single = nav * risk["max_single_name_pct"] / 100.0
    add(
        "single_name",
        proposal.max_loss <= max_single,
        f"max_loss={proposal.max_loss:.2f} <= max={max_single:.2f}",
    )

    add(
        "premium_at_risk",
        proposal.risk_pct <= risk["max_premium_at_risk_pct_per_trade"],
        f"risk={proposal.risk_pct:.2f}% <= max={risk['max_premium_at_risk_pct_per_trade']:.2f}%",
    )

    max_total_risk = nav * risk["max_total_open_risk_pct"] / 100.0
    add(
        "total_open_risk",
        account.gross_exposure + proposal.max_loss <= max_total_risk,
        f"projected={account.gross_exposure + proposal.max_loss:.2f} <= max={max_total_risk:.2f}",
        hard=False,
    )

    open_count = ctx.open_positions if ctx.open_positions is not None else len(account.positions)
    add(
        "open_positions",
        open_count < risk["max_open_positions"],
        f"open={open_count} < max={risk['max_open_positions']}",
    )

    add(
        "new_trades_today",
        ctx.trades_today < risk["max_new_trades_per_day"],
        f"today={ctx.trades_today} < max={risk['max_new_trades_per_day']}",
    )

    add(
        "cash_buffer",
        account.cash_pct >= risk["min_cash_pct"],
        f"cash={account.cash_pct:.2f}% >= min={risk['min_cash_pct']:.2f}%",
    )

    if proposal.dte is not None:
        add(
            "days_to_expiry",
            proposal.dte >= risk["min_days_to_expiry"],
            f"dte={proposal.dte} >= min={risk['min_days_to_expiry']}",
        )
    else:
        add("days_to_expiry", proposal.legs and all(leg.sec_type is SecurityType.STOCK for leg in proposal.legs), "stock legs have no expiry")

    if proposal.bid_ask_pct is not None:
        add(
            "bid_ask_spread",
            proposal.bid_ask_pct <= risk["max_bid_ask_pct"],
            f"spread={proposal.bid_ask_pct:.2f}% <= max={risk['max_bid_ask_pct']:.2f}%",
        )
    else:
        add("bid_ask_spread", True, "not provided; live check required before execution", hard=False)

    legs_valid = bool(proposal.legs) and all(leg.qty > 0 and leg.limit_price > 0 for leg in proposal.legs)
    add("limit_only", legs_valid, f"legs={len(proposal.legs)}; every leg needs qty>0 and a limit price")

    window_ok, window_detail = _time_window_ok(ctx.now_et, config)
    add("entry_window", window_ok, window_detail)
    add("final_flatten", _final_flatten_ok(ctx.now_et, config), _final_flatten_detail(ctx.now_et, config))

    approved = not blockers
    return RiskResult(approved=approved, checks=checks, blockers=blockers, warnings=warnings)


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _time_window_ok(now_et: datetime, config: Config) -> tuple[bool, str]:
    day = now_et.date().isoformat()
    dates = config.dates
    if day in set(dates.get("market_closed", [])):
        return False, f"{day} is a market holiday"
    if day > dates["final_trading_day"]:
        return False, f"{day} is after the final trading day {dates['final_trading_day']}"
    if day > dates["last_new_position_day"]:
        return False, f"{day} is after the last new-position day {dates['last_new_position_day']}"
    if day == dates["last_new_position_day"]:
        cutoff = _minutes(dates["last_new_position_time_et"])
        if now_et.hour * 60 + now_et.minute >= cutoff:
            return False, f"after {dates['last_new_position_time_et']} ET on {day}"
    start, end = config.execution["entry_window_et"]
    current = now_et.hour * 60 + now_et.minute
    if not (_minutes(start) <= current <= _minutes(end)):
        return False, f"{now_et.strftime('%H:%M')} ET outside {start}-{end} ET"
    return True, f"{now_et.strftime('%Y-%m-%d %H:%M')} ET inside entry window"


def _final_flatten_ok(now_et: datetime, config: Config) -> bool:
    day = now_et.date().isoformat()
    final_day = config.dates["final_trading_day"]
    if day != final_day:
        return True
    cutoff = _minutes(config.dates["final_flatten_time_et"])
    return now_et.hour * 60 + now_et.minute < cutoff


def _final_flatten_detail(now_et: datetime, config: Config) -> str:
    if not _final_flatten_ok(now_et, config):
        return f"final-day flatten window passed ({config.dates['final_flatten_time_et']} ET)"
    return f"final-day cutoff {config.dates['final_flatten_time_et']} ET"
