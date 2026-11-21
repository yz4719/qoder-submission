# LeadGuard — a runnable Moomoo paper-trading agent

Post-crash capital preservation with a defined-risk rebound trade. Python 3.10+,
standard library only, no API keys required for the demo.

The agent is deliberately rule-based at the point of execution: the LLM layer
researchs and narrates, but every order must pass the deterministic risk gates in
`leadguard/risk.py`. That split is the core design idea.

## Quick start

```bash
cd agent
python3 -m leadguard demo          # 4 scenarios + HTML report, no credentials
open ../dashboard/report.html
python3 -m unittest discover -s tests -v   # 9 risk-gate tests
```

Optional profiles:

```bash
python3 -m leadguard --config config/guard.json demo   # conservative: 1.5% per trade
python3 -m leadguard --config config/chase.json demo   # step change: 15% per trade
```

`config/competition.json` is the competition profile: 5% premium at risk per
trade, 10% total open risk, 3/6/10 drawdown ladder. `config/guard.json` tightens
that to 1.5% and 2/5/8. `config/chase.json` raises it to 15% / 30%, only if the
leaderboard demands a step change. `config/sprint.json` is an alias of the
competition profile with its own log and report. All profiles stop at the same
place: no naked options, no short stock, no 0DTE, no holding to expiry.

## Commands

| Command | What it does |
| --- | --- |
| `python3 -m leadguard demo` | Runs reconcile / bounce / breakdown / chop against fixtures and writes the HTML report |
| `python3 -m leadguard run --scenario bounce` | One decision, one log entry |
| `python3 -m leadguard live --mode dry_run` | Read-only account + quotes through the Moomoo CLI |
| `python3 -m leadguard live --mode paper --confirm` | Places the order — blocked unless the env guard below is set |
| `python3 -m leadguard report` | Re-renders the report from the JSONL log |

## Architecture

```
config/competition.json   parameters, universe, triggers, calendar
fixtures/                 point-in-time inputs (labelled illustrative)
leadguard/
  market.py               snapshot + regime + trend + breadth proxy
  signals.py              deterministic long/short/flat decision
  risk.py                 19 risk checks (hard veto + soft warnings)
  broker.py               FixtureBroker (dry run) | MoomooCliBroker (read-only / paper)
  orchestrator.py         reconcile-first run loop, decision log, state
  log.py                  append-only JSONL + atomic state writes
  report.py               standalone dark-theme HTML report
tests/test_risk.py        9 unit tests, one per critical gate
```

Decision flow:

1. Load snapshot (quotes + account).
2. **Reconcile gate** — unverified positions, short stock, or an option with
   ≤2 DTE blocks every new trade and returns `RECONCILE`.
3. Evaluate regime/trend/VIX/confirmation. No confirmed edge returns `HOLD`
   ("cash is a position").
4. Size a defined-risk vertical inside the premium budget.
5. Run the risk gates. Any hard failure means no order.
6. Append the full decision (inputs, reasons, proposal, gate results) to
   `dashboard/data/*.jsonl` and render the report.

## Safety model

Paper execution through `MoomooCliBroker` requires **all** of:

- `mode == "paper"` and a real `account_id` (not `REPLACE_WITH_SIM_ACCOUNT_ID`)
- `--confirm` passed on the command line
- `LEADGUARD_I_UNDERSTAND_PAPER=1` in the environment
- no leg note containing `placeholder` — every leg price must be replaced with a
  live bid/ask first

The agent never logs in for you. Moomoo CLI OAuth is a manual user step.

## Verified vs inferred

Verified: 2026-11-20 closes (SPY 689.81, QQQ 608.45, IWM 256.61, NVDA 125.53,
AMD 424.39, VIX 35.89), competition terms and dates.

Inferred / illustrative: the reconstructed NVDA short from the ITM put
assignment, option spread debits in `fixtures/scenario_*.json`, and all
hypothetical scenario outcomes. They are labelled in the UI and in the JSON.

Simulated results only. Not investment advice. The organisers' backend records
prevail.
