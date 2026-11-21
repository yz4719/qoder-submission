# Risk limits (human-readable)

Every order is checked against all of these before it can exist. Hard gates block
the order; soft gates annotate it. The same table is rendered in the HTML report.

## Profile comparison

| Limit | guard | competition | Gate name in `risk.py` |
| --- | --- | --- | --- |
| Max premium at risk per trade | 1.5% NAV | 5.0% NAV | `premium_at_risk` |
| Max total open risk | 4.0% NAV | 10.0% NAV | `total_open_risk` (soft) |
| Max contracts per spread | 3 | 12 | sizing in `signals.py` |
| Max open positions | 2 | 2 | `open_positions` |
| Max new trades per day | 3 | 4 | `new_trades_today` |
| Min cash | 80% | 80% | `cash_buffer` |
| Max gross exposure | 20% NAV | 25% NAV | `gross_exposure` |
| Max single name | 10% NAV | 15% NAV | `single_name` |
| Daily loss limit | 2% NAV | 3% NAV | `daily_loss` |
| Soft stop (no new risk) | 5% drawdown | 6% drawdown | `soft_stop` |
| Kill switch (flatten) | 8% drawdown | 10% drawdown | `kill_switch` |
| Min DTE | 7 | 7 | `days_to_expiry` |
| Max bid/ask | 10% | 10% | `bid_ask_spread` |
| Universe | SPY QQQ IWM | SPY QQQ IWM | `blocked_symbol` |
| Blocked | NVDA AMD | NVDA AMD | `blocked_symbol` |

`config/chase.json` is the only profile that goes beyond this: 15% per trade, 30%
total open risk, 40 contracts, 4/8/12 drawdown ladder, 60% minimum cash. It exists
for a step change only; the absolute rules below still apply unchanged.

## Absolute rules (not configurable per trade)

1. No naked short options.
2. No short stock — if the account holds one, the only allowed action is covering it.
3. No 0DTE and no holding any option into its expiry day. Options ≤2 DTE block new risk.
4. Limit orders only; every leg needs a limit price and a positive quantity.
5. No new positions after Wed 2026-11-25 13:00 ET; flat by Fri 2026-11-27 12:30 ET.
6. Entry window 09:45–15:30 ET; Thanksgiving 2026-11-26 closed.
7. Reconcile first: any unverified position blocks new risk.
8. A paper order requires `--confirm` and `LEADGUARD_I_UNDERSTAND_PAPER=1`, and no
   leg may still carry a placeholder price.

## What each failure means in practice

| Gate fails | The agent does this |
| --- | --- |
| `positions_reconciled` / `no_short_stock` | Emits `RECONCILE`, instructs to verify/cover, no order |
| `kill_switch` / `soft_stop` / `daily_loss` | Emits `HOLD`, no new risk |
| `premium_at_risk` | Shrinks contracts; if still over, holds |
| `entry_window` | Holds; the next evaluation is the next session |
| `final_flatten` | Only closing orders are allowed |
| `bid_ask_spread` | Waits for a tighter market; never crosses a wide spread |

## Drawdown ladder (why these numbers)

The account is up 58.7% on one trade. Giving back more than 10% of peak would
erase the risk-adjusted-return advantage of the whole competition. The soft stop
at 6% stops new risk while leaving room for an open spread to work; the kill
switch at 10% is below the level where a single bounce trade could undo the lead.
