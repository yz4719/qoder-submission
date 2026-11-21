# LeadGuard — version history

Maintained by local Qoder. Each entry records what changed in the deployed cloud
configuration, newest first, so a reviewer can audit the build-up.

<!--
Retrieved at (UTC): 2026-11-21T15:07:48Z
Agent IDs: agent_00w69x99gvrb4xr65vio (coordinator),
           agent_00w4cqea6yy9t8kjkhqr (researcher),
           agent_00w4cqeflqy2otw9450h (risk auditor),
           agent_00w4cqejwke0w1omxxja (executor),
           agent_00w4cqenzwkqol4j4nb2 (advisor)
Cloud versions: coordinator v1, researcher v3, risk auditor v2, executor v3, advisor v2
Local revision: repo-mounted
Change summary: repository mounted, read tools set to always_allow on the two
read-only agents, template re-pinned, first fully unattended run completed
-->

## 2026-11-21T23:06+08:00 — Repository mounted, permission fix, first unattended run

- Repository mounted from the Forward console: `repo_mwqj14le_1` →
  `/data/workspace/qoder-submission` (read-only PAT). The template system prompt
  and both schedule initial events now use that path instead of the original
  `moomoo-strategy/qoder-submission` guess.
- Risk Auditor v1→v2 and Advisor v1→v2: built-in toolset (Read, Glob, Grep) set
  to `always_allow`. Reason: unattended runs stopped three times at
  `requires_action` waiting on read approvals inside child agents (7 approvals
  across three batches). Both agents stay credential-free, so this cannot turn
  into order capability.
- Template `tmpl_061d1be5116e1ee4892304c0` re-pinned to Researcher v3 /
  Risk Auditor v2 / Executor v3 / Advisor v2, coordinator = self.
- Manual run of the pre-market schedule
  `srun_a3174bafc561c2b4852886ed` (session `sess_00w6c1i7vzo5cuio0lxf`)
  completed unattended in 411 s, `end_turn`:
  - Live reconcile: NAV 160,269.87; cash −358,973.41; buying power 0;
    NVDA −2,298 shares (mv −288,467.94, unrealised +122,120.32); gross exposure
    180.0% of NAV vs the 25% internal cap; no option at or below 2 DTE.
  - Proposal `LG-20261121T151500Z-coverNVDA`: BUY 2,298 NVDA @ limit 131.00,
    close-only, intended for the 2026-11-23 open. **REJECTED** by the Risk
    Auditor on: blocked_symbol, universe_membership, no_short_stock,
    gross_exposure, cash_buffer, buying_power (`max_buy_back_qty = 0`),
    open_order_conflict, entry_window, premium_at_risk
    ($12,570.06 = 7.84% of NAV). Invalidation was NVDA > 143.72.
  - Open risk carried forward: order `3336849` (NVDA BUY 2,298 MARKET, raw
    status 2, unsettled mapping) may queue into Monday's open. A human must
    verify or cancel it in the moomoo app; the agent does not modify orders it
    did not place.
  - `US.VIX` returns `invalid_symbol` inside Forward, so the regime line keeps
    `vix: null` rather than an estimate.
- Rule context read after the run: handbook §3 caps single stock/ETF exposure at
  40% of initial assets, and §4 allows forced liquidation when liquidity goes
  below zero. The inherited NVDA short breaches §3, and with buying power at 0
  the agent cannot cover it.

## 2026-11-21T22:49+08:00 — Schedules and MCP smoke test

- Smoke session `sess_00w6ata5zso3k1b5b3xu` under identity
  `idn_9a3d6bbc269ad6a6d830ce80`:
  - moomoo MCP reachable; `quote_stock_quote` returned US.NVDA 125.53
    (data_date 2026-11-20, after-hours 130.01)
  - skills mounted at `/mnt/skills` (8 zips)
  - package not mounted at `/data/moomoo-strategy/qoder-submission`; the agent
    reported the blocker and placed no orders
- Schedules created against the template, both **paused** until the repository is
  mounted:
  - `sched_741c144265ed0bd75c524391` pre-market scan, cron `0 9 * * 1-5`,
    America/New_York
  - `sched_54e34049c9dc80173655aea0` post-close review, cron `45 15 * * 1-5`,
    America/New_York
- Both initial events instruct: reply NO REPO MOUNTED and stop when the package
  is absent.

## 2026-11-21T22:45+08:00 — Published to GitHub

- Repo: https://github.com/yz4719/qoder-submission (public, `main`)
- Two commits: package import, then README reflecting agents v2 / template /
  vault / skills.
- Forward template-level `github_repositories` binding rejected by the API
  (HTTP 400 for URL, `.git` URL, relative and absolute mount paths), so the
  repository is attached from the Forward console instead.

## 2026-11-21T22:40+08:00 — Forward template + GitHub binding

- Published package to GitHub `moomoo-strategy/qoder-submission` (recommended
  path so judges can read the code).
- Forward Template `tmpl_061d1be5116e1ee4892304c0` "LeadGuard Daily Paper
  Trading" (status: active)
  - environment `env_00w686v3axurm3lkmpae` (Default cloud)
  - vault `vault_00w688ylwd24g70flezk` (`moomoo-mcp`, MCP OAuth)
  - mcp_servers `moomoo` → `https://mcp.moomoo.com/mcp`
  - skills: moomoo-quote, news-search, stock-digest, comment-sentiment,
    unusual-capital-flows, unusual-derivatives-activity,
    unusual-technical-signal-alerts, sim-trading
  - multiagent coordinator: self + Researcher v2 + Risk Auditor v1 +
    Executor v2 + Advisor v1

## 2026-11-21T22:35+08:00 — Moomoo MCP and skills bound to agents

- Researcher v1→v2: `moomoo` MCP server, `mcp_toolset` (always_ask), 7 research
  skills.
- Executor v1→v2: `moomoo` MCP server, `mcp_toolset` (always_ask), 2 skills
  (sim-trading, quote).
- Risk Auditor, Advisor: unchanged. No trading credentials (least privilege).
- Coordinator recreated as `agent_00w69x99gvrb4xr65vio` (v1) because
  `update_agent` cannot modify `multiagent`; it pins the v2 children.
  Superseded `agent_00w4cqrf9q4u876oa3j2` kept unarchived as a backup.

## 2026-11-21T01:41Z — Initial five agents

- Coordinator `agent_00w4cqrf9q4u876oa3j2`
- Researcher `agent_00w4cqea6yy9t8kjkhqr`
- Risk Auditor `agent_00w4cqeflqy2otw9450h`
- Executor `agent_00w4cqejwke0w1omxxja`
- Advisor `agent_00w4cqenzwkqol4j4nb2`

## Baseline

- 9 risk-gate unit tests, 4-scenario demo, decision log and deck generated
  locally with Qoder.
