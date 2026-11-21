"""Configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "mode": "dry_run",
    "account_id": "REPLACE_WITH_SIM_ACCOUNT_ID",
    "initial_nav": 100000.0,
    "nav": 158740.37,
    "peak_nav": 158740.37,
    "timezone": "America/New_York",
    "risk": {
        "max_drawdown_pct": 10.0,
        "soft_stop_drawdown_pct": 6.0,
        "daily_loss_limit_pct": 3.0,
        "max_gross_exposure_pct": 25.0,
        "max_single_name_pct": 15.0,
        "max_premium_at_risk_pct_per_trade": 5.0,
        "max_total_open_risk_pct": 10.0,
        "max_open_positions": 2,
        "max_new_trades_per_day": 4,
        "max_contracts_per_spread": 12,
        "min_cash_pct": 80.0,
        "min_days_to_expiry": 7,
        "max_bid_ask_pct": 10.0,
        "no_naked_short_options": True,
        "no_short_stock": True,
        "no_0dte": True,
        "kill_switch_drawdown_pct": 10.0,
    },
    "universe": ["SPY", "QQQ", "IWM"],
    "blocked_symbols": ["NVDA", "AMD"],
    "triggers": {
        "spy_long": 695.0,
        "qqq_long": 612.0,
        "vix_long_max": 34.0,
        "spy_short": 686.75,
        "qqq_short": 606.23,
        "vix_short_min": 34.0,
    },
    "dates": {
        "as_of": "2026-11-20",
        "first_trading_day": "2026-11-23",
        "last_new_position_day": "2026-11-25",
        "last_new_position_time_et": "13:00",
        "final_trading_day": "2026-11-27",
        "final_flatten_time_et": "12:30",
        "market_closed": ["2026-11-26"],
    },
    "execution": {
        "entry_window_et": ["09:45", "15:30"],
        "no_new_after_et": "15:30",
        "max_slippage_pct": 10.0,
        "limit_only": True,
        "paper_requires_confirm": True,
    },
    "paths": {
        "quotes": "fixtures/quotes_2026-11-20.json",
        "account": "fixtures/account_2026-11-20.json",
        "decisions": "../dashboard/data/decisions.jsonl",
        "state": "../dashboard/data/state.json",
        "report": "../dashboard/report.html",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class Config:
    data: dict[str, Any]
    path: Path | None = None
    base_dir: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        p = Path(path)
        raw = json.loads(p.read_text(encoding="utf-8"))
        merged = _deep_merge(DEFAULTS, raw)
        cfg = cls(merged, p)
        cfg.base_dir = p.resolve().parent.parent if p.resolve().parent.name == "config" else p.resolve().parent
        cfg.validate()
        return cfg

    @classmethod
    def default(cls) -> "Config":
        return cls(dict(DEFAULTS))

    def validate(self) -> None:
        risk = self.risk
        required = [
            "max_drawdown_pct",
            "daily_loss_limit_pct",
            "max_gross_exposure_pct",
            "max_premium_at_risk_pct_per_trade",
            "min_cash_pct",
        ]
        missing = [key for key in required if key not in risk]
        if missing:
            raise ValueError(f"missing risk limits: {missing}")
        if risk["max_premium_at_risk_pct_per_trade"] > risk["max_total_open_risk_pct"]:
            raise ValueError("per-trade risk cannot exceed total open risk")
        if risk["max_drawdown_pct"] < risk["daily_loss_limit_pct"]:
            raise ValueError("drawdown limit must be >= daily loss limit")
        if self.data["initial_nav"] <= 0:
            raise ValueError("initial_nav must be positive")

    def path_for(self, key: str, base: Path | None = None) -> Path:
        raw = self.paths[key]
        p = Path(raw)
        if p.is_absolute():
            return p
        root = base or self.base_dir or (self.path.parent if self.path else Path.cwd())
        return (root / p).resolve()

    @property
    def risk(self) -> dict[str, Any]:
        return self.data["risk"]

    @property
    def dates(self) -> dict[str, Any]:
        return self.data["dates"]

    @property
    def execution(self) -> dict[str, Any]:
        return self.data["execution"]

    @property
    def paths(self) -> dict[str, Any]:
        return self.data["paths"]

    @property
    def universe(self) -> list[str]:
        return list(self.data["universe"])

    @property
    def blocked_symbols(self) -> set[str]:
        return set(self.data.get("blocked_symbols", []))

    @property
    def triggers(self) -> dict[str, float]:
        return {key: float(value) for key, value in self.data["triggers"].items()}

    @property
    def mode(self) -> str:
        return str(self.data.get("mode", "dry_run"))

    def to_dict(self) -> dict[str, Any]:
        return self.data
