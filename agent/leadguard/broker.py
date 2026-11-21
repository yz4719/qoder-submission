"""Broker adapters.

``FixtureBroker`` is the default and needs no credentials.  ``MoomooCliBroker``
wraps the read-only and simulated-trading commands of the Moomoo CLI.  It never
calls real-money trading commands.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

from .market import MarketSnapshot
from .models import Account, Leg, Position, SecurityType


class Broker(Protocol):
    def get_account(self) -> Account: ...
    def get_quotes(self) -> MarketSnapshot: ...
    def place_orders(self, legs: list[Leg], confirm: bool = False) -> list[dict[str, Any]]: ...


class FixtureBroker:
    def __init__(self, account_path: str | Path, quotes_path: str | Path):
        self.account_path = Path(account_path)
        self.quotes_path = Path(quotes_path)

    def get_account(self) -> Account:
        raw = json.loads(self.account_path.read_text(encoding="utf-8"))
        positions = [_position_from_dict(item) for item in raw.get("positions", [])]
        return Account(
            nav=float(raw["nav"]),
            peak_nav=float(raw.get("peak_nav", raw["nav"])),
            cash=float(raw.get("cash", 0.0)),
            day_pnl=float(raw.get("day_pnl", 0.0)),
            positions=positions,
            account_id=str(raw.get("account_id", "FIXTURE")),
            as_of=str(raw.get("as_of", "")),
            source=str(raw.get("source", "fixture")),
        )

    def get_quotes(self) -> MarketSnapshot:
        return MarketSnapshot.load(self.quotes_path)

    def place_orders(self, legs: list[Leg], confirm: bool = False) -> list[dict[str, Any]]:
        if confirm:
            raise RuntimeError("FixtureBroker is dry-run only; use MoomooCliBroker for paper orders")
        return [
            {
                "leg": leg.to_dict(),
                "status": "DRY_RUN",
                "fill_price": None,
                "order_id": None,
            }
            for leg in legs
        ]


class MoomooCliBroker:
    """Thin, simulated-only wrapper around the Moomoo CLI.

    Safety properties:
    - only ``moomoo sim ...`` and ``moomoo quote ...`` are allowed;
    - paper orders require both ``confirm=True`` and the environment variable
      ``LEADGUARD_I_UNDERSTAND_PAPER=1``;
    - the token file is never read or printed.
    """

    def __init__(
        self,
        account_id: str,
        binary: str | None = None,
        market: str = "US",
        timeout: int = 30,
    ):
        self.account_id = account_id
        self.market = market
        self.timeout = timeout
        self.binary = binary or _find_binary()

    def _run(self, args: list[str], timeout: int | None = None) -> dict[str, Any] | list[Any] | str:
        cmd = [self.binary, *args, "--format", "json", "--source", "skill"]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "moomoo CLI failed").strip()
            raise RuntimeError(message[:800])
        text = completed.stdout.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def list_accounts(self) -> Any:
        return self._run(["sim", "account", "list"])

    def get_account(self) -> Account:
        funds = self._run(["sim", "account", "funds", "--account", self.account_id])
        stock = self._run(["sim", "position", "--account", self.account_id, "--market", self.market])
        options = self._run(["sim", "position", "--account", self.account_id, "--market", "US_OPTION"])
        cash_info = _first_dict(funds, "cash_info", "data", "funds")
        nav = _num(cash_info.get("totalAsset") or cash_info.get("total_asset") or cash_info.get("balance"))
        cash = _num(cash_info.get("balance") or cash_info.get("cash"))
        day_pnl = _num(cash_info.get("unrealizedProfit") or cash_info.get("dayPnl"))
        positions = _parse_positions(stock) + _parse_positions(options)
        return Account(
            nav=nav,
            peak_nav=nav,
            cash=cash,
            day_pnl=day_pnl,
            positions=positions,
            account_id=self.account_id,
            as_of="live",
            source="moomoo-cli",
        )

    def get_quotes(self) -> MarketSnapshot:
        raw = self._run(["quote", "US.SPY", "US.QQQ", "US.IWM", "US.VIX"])
        quotes = _parse_quotes(raw)
        return MarketSnapshot(quotes=quotes, as_of="live", meta={"source": "moomoo-cli"})

    def place_orders(self, legs: list[Leg], confirm: bool = False) -> list[dict[str, Any]]:
        if not confirm:
            raise RuntimeError("paper order blocked: confirm=False")
        if os.environ.get("LEADGUARD_I_UNDERSTAND_PAPER") != "1":
            raise RuntimeError("paper order blocked: set LEADGUARD_I_UNDERSTAND_PAPER=1")
        if any("placeholder" in leg.note.lower() for leg in legs):
            raise RuntimeError("paper order blocked: live option bid/ask must replace placeholder prices")
        results: list[dict[str, Any]] = []
        for leg in legs:
            market = "US_OPTION" if leg.sec_type is SecurityType.OPTION else self.market
            args = [
                "sim",
                "order",
                "place",
                str(leg.qty),
                "--symbol",
                leg.symbol,
                "--side",
                leg.side.value,
                "--account",
                self.account_id,
                "--market",
                market,
                "--type",
                "limit",
                "--price",
                f"{leg.limit_price:.4f}",
                "--text",
                "leadguard",
            ]
            results.append({"leg": leg.to_dict(), "response": self._run(args)})
        return results

    def order_history(self, page_size: int = 50) -> Any:
        return self._run(
            [
                "sim",
                "order",
                "history",
                "--account",
                self.account_id,
                "--market",
                self.market,
                "--page-size",
                str(page_size),
            ]
        )


def _find_binary() -> str:
    found = shutil.which("moomoo")
    if found:
        return found
    common = Path.home() / ".moomoo" / "bin" / "moomoo"
    if common.exists():
        return str(common)
    raise FileNotFoundError("moomoo CLI not found; install it or pass binary=")


def _position_from_dict(item: dict[str, Any]) -> Position:
    sec_type = SecurityType(str(item.get("sec_type", "STOCK")).upper())
    return Position(
        symbol=str(item["symbol"]),
        sec_type=sec_type,
        qty=float(item.get("qty", 0)),
        avg_cost=float(item.get("avg_cost", 0)),
        last=float(item.get("last", 0)),
        market_value=float(item.get("market_value", 0)),
        unrealized_pnl=float(item.get("unrealized_pnl", 0)),
        expiry=item.get("expiry"),
        strike=_optional_float(item.get("strike")),
        option_type=item.get("option_type"),
        verified=bool(item.get("verified", True)),
        note=str(item.get("note", "")),
    )


def _parse_positions(raw: Any) -> list[Position]:
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("positions") or raw.get("data") or raw.get("list") or []
    else:
        rows = []
    positions: list[Position] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or row.get("code") or "")
        if not symbol:
            continue
        qty = _num(row.get("qty") or row.get("quantity") or row.get("position"))
        last = _num(row.get("last") or row.get("price") or row.get("nominalPrice"))
        market_value = _num(row.get("market_value") or row.get("marketVal") or row.get("marketValue"))
        if not market_value:
            market_value = qty * last * (100 if _looks_like_option(symbol) else 1)
        positions.append(
            Position(
                symbol=symbol,
                sec_type=SecurityType.OPTION if _looks_like_option(symbol) else SecurityType.STOCK,
                qty=qty,
                avg_cost=_num(row.get("avg_cost") or row.get("costPrice") or row.get("averageCost")),
                last=last,
                market_value=market_value,
                unrealized_pnl=_num(row.get("unrealized_pnl") or row.get("unrealizedPl")),
                verified=True,
                note="live Moomoo position",
            )
        )
    return positions


def _parse_quotes(raw: Any) -> dict[str, Any]:
    from .models import Quote

    rows = raw
    if isinstance(raw, dict):
        rows = raw.get("data") or raw.get("quotes") or raw.get("list") or []
    if not isinstance(rows, list):
        raise RuntimeError("unexpected quote response shape")
    quotes: dict[str, Quote] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or row.get("code") or "").replace("US.", "").replace("^", "")
        if not symbol:
            continue
        quotes[symbol] = Quote(
            symbol=symbol,
            close=_num(row.get("last_price") or row.get("lastPrice") or row.get("price")),
            prev_close=_num(row.get("prev_close") or row.get("prevClose") or row.get("close")),
            day_high=_optional_float(row.get("high") or row.get("dayHigh")),
            day_low=_optional_float(row.get("low") or row.get("dayLow")),
            as_of="live",
        )
    if not quotes:
        raise RuntimeError("no quotes parsed from Moomoo CLI response")
    return quotes


def _first_dict(raw: Any, *keys: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        for key in keys:
            value = raw.get(key)
            if isinstance(value, dict):
                return value
        return raw
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        return raw[0]
    return {}


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _looks_like_option(symbol: str) -> bool:
    upper = symbol.upper()
    return len(upper) >= 15 and ("C" in upper[8:] or "P" in upper[8:])
