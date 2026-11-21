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

## Live dashboard

```bash
python3 dashboard/serve.py          # http://127.0.0.1:8765/live.html
```

It reads `dashboard/data/state.json` and `decisions.jsonl` and renders NAV, cash,
P&L, drawdown, gross exposure against the 40% rule, positions labelled
verified/inferred, the equity curve, the risk limits, and every decision
including the rejected ones.

The Cloud Agents panel needs a Qoder Personal Access Token. Create one at
<https://qoder.com/cloud/pat-keys>, put it in a `.env` at the repo root
(`QODER_PAT=...`, already gitignored — see `.env.example`), and restart the
server. Requests to `https://api.qoder.com/api/v1/cloud` are made server-side
only; the token is never sent to the browser and never committed. Without a
token the panel says so and the local panels keep working.

## Contents

```
deck/index.html                 presentation deck (Qoder-generated)
dashboard/live.html             live dashboard (served by dashboard/serve.py)
dashboard/serve.py              local server; proxies Cloud Agents reads
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
  - Coordinator `agent_00w69x99gvrb4xr65vio` ("LeadGuard Coordinator v2",
    pins the researcher/executor versions below)
  - Researcher `agent_00w4cqea6yy9t8kjkhqr` (v3)
  - Risk Auditor `agent_00w4cqeflqy2otw9450h` (v2)
  - Executor `agent_00w4cqejwke0w1omxxja` (v3)
  - Advisor `agent_00w4cqenzwkqol4j4nb2` (v2)
  - Forward Template `tmpl_061d1be5116e1ee4892304c0`
    ("LeadGuard Daily Paper Trading"), vault `vault_00w688ylwd24g70flezk`
    (`moomoo-mcp`), Environment `env_00w686v3axurm3lkmpae`
  - This repository is mounted at `/data/workspace/qoder-submission`
    (`repo_mwqj14le_1`, read-only) and is the working copy used by every cloud
    run.
  - Moomoo MCP (`https://mcp.moomoo.com/mcp`) is bound to Researcher and
    Executor; the risk auditor, advisor and coordinator stay credential-free.
    The two read-only agents have Read/Glob/Grep set to `always_allow` so that
    scheduled runs do not stall on approval prompts; they hold no credentials,
    so this cannot become order capability.
  - Eight Moomoo skills (quote, news, digest, sentiment, three unusual-activity
    packs, sim trading) are bound at template level.
  - Version history: `AGENTS.md`.

  The pre-market schedule (`sched_741c144265ed0bd75c524391`) has run end to end
  unattended: reconcile, session brief, proposal, audit, decision log, report.
  The post-close schedule (`sched_54e34049c9dc80173655aea0`) is created but
  still paused.

## Current paper account state

The competition paper account (5830188) came into this build with a pre-existing
NVDA short of 2,298 shares, roughly 180% of NAV. That breaches the handbook's
40% single-name exposure cap, and with buying power at 0 (`max_buy_back_qty = 0`)
the agent cannot cover it on its own. The 2026-11-21 proposal to cover was
correctly rejected by the Risk Auditor. Closing the short requires either broker
liquidity or an organiser-side reset; the agent does not place, amend or cancel
orders it did not create. Figures in this repository are the ones the agent
verified at 2026-11-21T15:02Z; the organisers' backend prevails.

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
