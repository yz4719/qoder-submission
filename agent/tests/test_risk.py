from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from leadguard.config import Config
from leadguard.models import Account, Action, Leg, Position, Proposal, SecurityType, Side
from leadguard.risk import RiskContext, check


class RiskTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.config = Config.load(root / "config" / "competition.json")
        self.now = datetime(2026, 11, 23, 10, 0)

    def _account(self, **overrides):
        base = dict(
            nav=158740.37,
            peak_nav=158740.37,
            cash=158740.37,
            day_pnl=0.0,
            positions=[],
        )
        base.update(overrides)
        return Account(**base)

    def _proposal(self, **overrides):
        base = dict(
            action=Action.BUY_CALL_SPREAD,
            symbol="SPY",
            legs=[
                Leg("US.SPY261218C700000", Side.BUY, 2, 8.0),
                Leg("US.SPY261218C720000", Side.SELL, 2, 0.01, note="PLACEHOLDER"),
            ],
            max_loss=1600.0,
            risk_pct=1.01,
            expiry="2026-12-18",
            dte=25,
            bid_ask_pct=4.0,
        )
        base.update(overrides)
        return Proposal(**base)

    def test_clean_account_is_approved(self):
        result = check(self._proposal(), self._account(), self.config, RiskContext.at(self.now))
        self.assertTrue(result.approved, result.blockers)

    def test_unverified_position_blocks(self):
        account = self._account(
            positions=[Position("NVDA", SecurityType.STOCK, -2600, verified=False)]
        )
        result = check(self._proposal(), account, self.config, RiskContext.at(self.now))
        self.assertFalse(result.approved)
        self.assertTrue(any("positions_reconciled" in b for b in result.blockers))

    def test_short_stock_blocks(self):
        account = self._account(positions=[Position("NVDA", SecurityType.STOCK, -2600)])
        result = check(self._proposal(), account, self.config, RiskContext.at(self.now))
        self.assertFalse(result.approved)
        self.assertTrue(any("no_short_stock" in b for b in result.blockers))

    def test_kill_switch_blocks(self):
        account = self._account(nav=142000.0, cash=142000.0)
        result = check(self._proposal(), account, self.config, RiskContext.at(self.now))
        self.assertFalse(result.approved)
        self.assertTrue(any("kill_switch" in b for b in result.blockers))

    def test_daily_loss_blocks(self):
        account = self._account(day_pnl=-5000.0)
        result = check(self._proposal(), account, self.config, RiskContext.at(self.now))
        self.assertFalse(result.approved)
        self.assertTrue(any("daily_loss" in b for b in result.blockers))

    def test_premium_at_risk_blocks(self):
        result = check(self._proposal(risk_pct=6.0, max_loss=9600.0), self._account(), self.config, RiskContext.at(self.now))
        self.assertFalse(result.approved)
        self.assertTrue(any("premium_at_risk" in b for b in result.blockers))

    def test_entry_window_blocks(self):
        result = check(self._proposal(), self._account(), self.config, RiskContext.at(datetime(2026, 11, 23, 9, 35)))
        self.assertFalse(result.approved)
        self.assertTrue(any("entry_window" in b for b in result.blockers))

    def test_holiday_blocks(self):
        result = check(self._proposal(), self._account(), self.config, RiskContext.at(datetime(2026, 11, 26, 10, 0)))
        self.assertFalse(result.approved)
        self.assertTrue(any("entry_window" in b for b in result.blockers))

    def test_wednesday_cutoff_blocks(self):
        result = check(self._proposal(), self._account(), self.config, RiskContext.at(datetime(2026, 11, 25, 14, 0)))
        self.assertFalse(result.approved)
        self.assertTrue(any("entry_window" in b for b in result.blockers))


if __name__ == "__main__":
    unittest.main()
