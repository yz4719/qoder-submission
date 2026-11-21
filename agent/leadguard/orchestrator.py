"""LeadGuard orchestration.

One run = one decision cycle:
    account -> market snapshot -> signal -> proposal -> hard risk gates -> log
In dry-run mode nothing is sent to a broker.  In paper mode the caller must
also pass confirm=True and set LEADGUARD_I_UNDERSTAND_PAPER=1.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from . import signals
from .broker import Broker, FixtureBroker, MoomooCliBroker
from .config import Config
from .log import DecisionLogger, merge_demo_state, write_json
from .market import MarketSnapshot
from .models import Action, Decision, utc_now
from .risk import RiskContext, check


ET = "America/New_York"


class LeadGuard:
    def __init__(self, config: Config, broker: Broker, logger: DecisionLogger):
        self.config = config
        self.broker = broker
        self.logger = logger

    def run_once(
        self,
        now_et: datetime | None = None,
        trades_today: int = 0,
        confirm: bool = False,
        broker: Broker | None = None,
        scenario: str = "live",
        note: str = "",
    ) -> tuple[Decision, dict[str, Any]]:
        active_broker = broker or self.broker
        account = active_broker.get_account()
        account.peak_nav = max(account.peak_nav, float(self.config.data["peak_nav"]))
        snapshot = active_broker.get_quotes()
        signal = signals.evaluate(snapshot, self.config, account)
        proposal = signals.build_proposal(signal, snapshot, account, self.config)
        ctx = RiskContext.at(now_et=now_et, trades_today=trades_today)
        risk = check(proposal, account, self.config, ctx)

        now_utc = utc_now()
        decision = Decision(
            decision_id=_decision_id(scenario),
            ts_utc=now_utc.isoformat(),
            ts_et=ctx.now_et.isoformat(),
            mode=self.config.mode,
            agent="leadguard-orchestrator",
            account_id=account.account_id,
            nav=account.nav,
            peak_nav=account.peak_nav,
            drawdown_pct=account.drawdown_pct,
            regime=snapshot.regime,
            signal=signal.to_dict(),
            proposal=proposal,
            risk=risk,
            executed=False,
            note=note,
        )

        if risk.approved and self.config.mode == "paper" and confirm:
            try:
                orders = active_broker.place_orders(proposal.legs, confirm=True)
                decision.executed = True
                decision.orders = orders
            except Exception as exc:  # surfaced in the log, never silently ignored
                decision.note = f"{decision.note} | execution blocked: {exc}".strip(" |")
        elif risk.approved and self.config.mode == "paper" and not confirm:
            decision.note = f"{decision.note} | paper mode: confirm=False, not executed".strip(" |")

        self.logger.append(decision)
        state = {
            "scenario": scenario,
            "generated_at_utc": now_utc.isoformat(),
            "mode": self.config.mode,
            "account": account.to_dict(),
            "market": snapshot.to_dict(),
            "signal": signal.to_dict(),
            "decision": decision.to_dict(),
            "risk": risk.to_dict(),
            "limits": {
                "daily_loss_pct": self.config.risk["daily_loss_limit_pct"],
                "soft_stop_pct": self.config.risk["soft_stop_drawdown_pct"],
                "kill_switch_pct": self.config.risk["kill_switch_drawdown_pct"],
                "max_total_open_risk_pct": self.config.risk["max_total_open_risk_pct"],
                "max_premium_at_risk_pct": self.config.risk["max_premium_at_risk_pct_per_trade"],
                "min_cash_pct": self.config.risk["min_cash_pct"],
            },
        }
        self.logger.write_state(state)
        return decision, state

    def demo(self) -> dict[str, Any]:
        """Run the reconciliation, bounce, breakdown, and chop scenarios."""
        self.logger.reset()
        root = self.config.base_dir or self.config.path.parent
        fixtures = root / "fixtures"
        runs = [
            (
                "reconcile",
                fixtures / "account_2026-11-20.json",
                fixtures / "quotes_2026-11-20.json",
                datetime(2026, 11, 23, 9, 50),
                "Unverified post-expiry account: the only correct action is to reconcile.",
            ),
            (
                "bounce",
                fixtures / "account_verified_example.json",
                fixtures / "scenario_bounce.json",
                datetime(2026, 11, 23, 10, 0),
                "ILLUSTRATIVE bounce scenario; option debit is an assumption.",
            ),
            (
                "breakdown",
                fixtures / "account_verified_example.json",
                fixtures / "scenario_breakdown.json",
                datetime(2026, 11, 23, 10, 0),
                "ILLUSTRATIVE breakdown scenario; option debit is an assumption.",
            ),
            (
                "chop",
                fixtures / "account_verified_example.json",
                fixtures / "scenario_chop.json",
                datetime(2026, 11, 23, 10, 0),
                "ILLUSTRATIVE chop scenario; cash is the correct position.",
            ),
        ]
        states: list[dict[str, Any]] = []
        for scenario, account_path, quotes_path, when, note in runs:
            broker = FixtureBroker(account_path, quotes_path)
            _, state = self.run_once(now_et=when, broker=broker, scenario=scenario, note=note)
            states.append(state)
        combined = merge_demo_state(states, states[-1])
        combined["demo_states"] = states
        combined["reported_account"] = states[0]["account"]
        combined["demo_runs"] = [
            {
                "scenario": state["scenario"],
                "decision_id": state["decision"]["decision_id"],
                "action": state["decision"]["proposal"]["action"],
                "approved": state["decision"]["risk"]["approved"],
                "nav": state["decision"]["nav"],
                "signal_bias": state["signal"]["bias"],
                "reasons": state["signal"]["reasons"],
                "blockers": state["decision"]["risk"]["blockers"],
            }
            for state in states
        ]
        self.logger.write_state(combined)
        return combined

    def live(self, mode: str = "dry_run", confirm: bool = False) -> tuple[Decision, dict[str, Any]]:
        account_id = str(self.config.data["account_id"])
        if not account_id or account_id.startswith("REPLACE"):
            raise RuntimeError("Set account_id in config/competition.json before running live.")
        broker = MoomooCliBroker(account_id=account_id)
        old_mode = self.config.data["mode"]
        self.config.data["mode"] = mode
        try:
            return self.run_once(now_et=None, confirm=confirm, broker=broker, scenario=f"live-{mode}", note="live Moomoo CLI")
        finally:
            self.config.data["mode"] = old_mode


def _decision_id(scenario: str) -> str:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in scenario)[:24]
    return f"LG-{stamp}-{safe}"


def build_from_paths(config_path: str | Path, account_path: str | Path | None = None, quotes_path: str | Path | None = None) -> LeadGuard:
    config = Config.load(config_path)
    root = config.base_dir or Path(config_path).resolve().parent
    account = Path(account_path) if account_path else config.path_for("account", root)
    quotes = Path(quotes_path) if quotes_path else config.path_for("quotes", root)
    logger = DecisionLogger(config.path_for("decisions", root), config.path_for("state", root))
    return LeadGuard(config, FixtureBroker(account, quotes), logger)
