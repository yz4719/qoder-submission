# Decision log

Append-only source of truth is `dashboard/data/decisions.jsonl` (written by the
agent, one JSON object per run). This page explains the decisions in plain
language, including the ones that were rejected.

## Open action before the next session

| # | Action | Why | Status |
| --- | --- | --- | --- |
| A-0 | **Buy to cover the inferred NVDA short (~2,600 shares)** | The 11-20 172.50 put was ITM at Friday's close and was auto-exercised into short stock. An uncovered short has unbounded risk, violates `no_short_stock`, and blocks every new trade in the package. | **Pending user action — not executed by the agent** |
| A-0b | Verify the AMD 11-20 462.50C is gone | OTM at expiry → worthless per the rules; confirm it no longer shows as a position | Pending user verification |

Until A-0 is done, the reconcile gate replaces every proposal with `RECONCILE`.
This is intentional and is the first demo scenario.

## Demo decisions (2026-11-21 run, reproducible)

| Decision id | Scenario | Action | Gate result | Sizing | Why |
| --- | --- | --- | --- | --- | --- |
| `LG-20261121T015032Z-reconcile` | Account as reported 11-20 | `RECONCILE` | blocked | none | Unverified positions + short stock + expired option. No new risk permitted. |
| `LG-20261121T015032Z-bounce` | SPY 701.20, QQQ 620.50, VIX 31.20 | `BUY_CALL_SPREAD` SPY 700/720 Dec-18 | approved | 9 × $8.00 = $7,200 (competition, 4.5%); 2 × $8.00 = $1,600 (guard, 1.0%) | All three long confirmations met after a −3.7% index day; defined risk caps the failed-bounce cost. |
| `LG-20261121T015032Z-breakdown` | SPY 682.40, QQQ 600.10, VIX 39.50 | `BUY_PUT_SPREAD` SPY 680/660 Dec-18 | approved | 8 × $9.00 = $7,200 (competition, 4.5%); 2 × $9.00 = $1,800 (guard, 1.1%) | Breakdown confirmation with VIX still elevated; participates without naked short exposure. |
| `LG-20261121T015032Z-chop` | SPY 692.30, QQQ 611.80, VIX 35.20 | `HOLD` | no order | none | No confirmation in either direction. Cash is a position. |

The bounce and breakdown proposals are alternatives, not a simultaneous pair. The
account allows at most 2 open positions and 10% total open risk in the competition
profile.

## Rejected decisions (and the rule that rejects them)

| Rejected idea | Why it looked attractive | Why it is rejected |
| --- | --- | --- |
| Buy NVDA calls after −14% | Cheap, high beta, huge bounce potential | Single-name AI concentration caused the current risk profile; NVDA/AMD blocked until flat and verified |
| Buy AMD 462.50C again | Cost only $2,770 | Lottery ticket: expired worthless; 1.5–5% premium budget must buy a defined-risk spread, not a cheap OTM call |
| Hold the ITM NVDA put to expiry | It was up 71% | Auto-exercise converted it into short stock; hard rule: close before expiry, no exceptions |
| Naked short puts for premium | High IV, “safe” strikes | Undefined risk, disallowed by config and by the risk rubric |
| 0DTE index options | Fastest way to catch a bounce | Path-dependent, wide spreads, disallowed |
| Size up to 40% NAV to chase the leader | Necessary if behind | Removes the drawdown protection that makes the +58.7% defensible; max open risk stays 10%, or 30% in `chase.json` with a 12% kill switch |

## How to append a real decision

```bash
cd agent
python3 -m leadguard live --mode dry_run
python3 -m leadguard report
```

The decision id, inputs, signal, proposal, gate results, and any order ids are
written together. If the broker rejects an order, the rejection is logged as the
outcome — never edited afterwards.
