"""Market snapshot helpers.

Quotes may come from the Moomoo adapter or from a checked-in fixture.  The
fixture schema is intentionally simple: one object per symbol plus an optional
``_meta`` object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Quote


@dataclass
class MarketSnapshot:
    quotes: dict[str, Quote]
    as_of: str
    meta: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path, default_as_of: str = "") -> "MarketSnapshot":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        meta = raw.pop("_meta", {}) if isinstance(raw, dict) else {}
        quotes: dict[str, Quote] = {}
        for symbol, data in raw.items():
            if not isinstance(data, dict) or "close" not in data:
                continue
            quotes[symbol.replace("^", "").upper()] = Quote(
                symbol=symbol.replace("^", "").upper(),
                close=float(data["close"]),
                prev_close=float(data.get("prev_close", data["close"])),
                day_high=_f(data.get("day_high")),
                day_low=_f(data.get("day_low")),
                high_20d=_f(data.get("high_20d")),
                low_20d=_f(data.get("low_20d")),
                sma20=_f(data.get("sma20")),
                sma50=_f(data.get("sma50")),
                rsi14=_f(data.get("rsi14")),
                atr14=_f(data.get("atr14")),
                realized_vol20_annual_pct=_f(data.get("realized_vol20_annual_pct")),
                as_of=str(data.get("as_of", meta.get("as_of", default_as_of))),
            )
        if not quotes:
            raise ValueError(f"no quotes found in {path}")
        as_of = str(meta.get("as_of") or default_as_of or next(iter(quotes.values())).as_of)
        return cls(quotes=quotes, as_of=as_of, meta=meta)

    @property
    def spy(self) -> Quote:
        return self.quotes["SPY"]

    @property
    def qqq(self) -> Quote:
        return self.quotes["QQQ"]

    @property
    def iwm(self) -> Quote:
        return self.quotes["IWM"]

    @property
    def vix(self) -> float:
        if "VIX" in self.quotes:
            return self.quotes["VIX"].close
        value = self.meta.get("vix")
        if value is None:
            raise ValueError("VIX is missing from the snapshot")
        return float(value)

    @property
    def regime(self) -> str:
        vix = self.vix
        if vix >= 32:
            return "panic"
        if vix >= 25:
            return "high_vol"
        if vix >= 20:
            return "normal"
        return "calm"

    @property
    def trend(self) -> str:
        spy = self.spy
        if spy.sma20 is not None and spy.sma50 is not None:
            if spy.close < spy.sma20 < spy.sma50:
                return "down"
            if spy.close > spy.sma20 > spy.sma50:
                return "up"
        return "mixed"

    @property
    def breadth_proxy(self) -> float:
        """IWM minus SPY one-day change, in percentage points."""
        return self.iwm.change_pct - self.spy.change_pct

    def option_debit(self, key: str, default: float | None = None) -> float | None:
        options = self.meta.get("options", {})
        value = options.get(key)
        if value is None:
            value = default
        return None if value is None else float(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "regime": self.regime,
            "trend": self.trend,
            "vix": self.vix,
            "breadth_proxy_pp": round(self.breadth_proxy, 2),
            "quotes": {name: q.to_dict() for name, q in self.quotes.items()},
            "meta": self.meta,
        }


def _f(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
