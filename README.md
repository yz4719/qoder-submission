# LeadGuard — Moomoo × Qoder AI Trading Agent Challenge submission

A runnable, auditable paper-trading agent plus the strategy, risk limits, decision
log, demo, and presentation deck required by the challenge.

Start here:

- **Deck** — `deck/index.html` (standalone, arrow keys to navigate)
- **Decision report** — `dashboard/report.html` (generated from the JSONL log)
- **Strategy** — `docs/STRATEGY.md`
- **Risk limits** — `docs/RISK_LIMITS.md`
- **Decision log** — `docs/DECISIONS.md` + `dashboard/data/decisions.jsonl`
- **Trading journal** — `docs/TRADING_JOURNAL.md` (reported vs inferred fills)
- **Runbook** — `docs/RUNBOOK.md`
- **Agent package** — `agent/` (`README.md` inside)

## Reproduce in two minutes

```bash
cd agent
python3 -m unittest discover -s tests -v   # 9 risk-gate tests
python3 -m leadguard demo                  # 4 scenarios, competition profile
python3 -m leadguard --config config/guard.json demo
open ../dashboard/report.html
```

No credentials are required. The demo runs against point-in-time fixtures and
writes every decision to `dashboard/data/`.

## Contents

```
deck/index.html                 presentation deck (Qoder-generated)
dashboard/report.html           decision report (competition profile)
dashboard/report_guard.html     decision report (guard profile)
dashboard/data/*.jsonl          append-only decision logs
docs/                           strategy, risk limits, decisions, runbook
agent/                          runnable Python package
  leadguard/                    signals, risk gates, broker, log, report
  config/competition.json       competition profile (5% per trade)
  config/guard.json             conservative profile (1.5% per trade)
  config/chase.json             step-change profile (15% per trade, 30% total)
  fixtures/                     quotes, reconstructed account, scenarios
  prompts/                      coordinator, researcher, risk auditor, executor, advisor
  tests/                        9 unit tests
qoder/skill/leadguard/SKILL.md  Qoder skill wrapper
qoder/leadguard.zip             skill packaged for Cloud Agents upload
```

## Qoder and Cloud Agent usage

- **Local Qoder** built the package, ran the demo and tests, generated the report
  and this deck, and produced the docs.
- **Qoder Cloud Agents** (Personal workspace, created 21 Nov 2026):
  - Coordinator `agent_00w4cqrf9q4u876oa3j2`
  - Researcher `agent_00w4cqea6yy9t8kjkhqr`
  - Risk Auditor `agent_00w4cqeflqy2otw9450h`
  - Executor `agent_00w4cqejwke0w1omxxja`
  - Advisor `agent_00w4cqenzwkqol4j4nb2`
  - Environment `env_00w4crigtnpxdgjignzq` (Python 3, stdlib only)

  The Agent definitions are live; running a session requires mounting this package
  (GitHub repo or file resource) — see `docs/RUNBOOK.md`.

## Verified vs inferred

Verified: 20 Nov 2026 closes, competition dates, rules and fee schedule.

Inferred: the NVDA short-stock position reconstructed from the ITM put assignment,
the AMD position state, and all option debits in the fixtures. Every such figure
is labelled in the report and in `docs/DECISIONS.md`.

Simulated results only. Not investment advice. Organisers' backend records prevail.

## Deadline and submission link

Deadline: **30 Nov 2026, 23:59 SGT**. The Luma event page's "Submission link:
HERE" points to a survey that, as of 21 Nov 2026, still serves the QwenWork x
Hashmeta OPC Hackathon. Re-check the page before submitting. The participant
handbook is at https://moomoo-qoder-challenge-rgkelnyuzbm.qoder.website/.
