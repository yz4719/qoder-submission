# LeadGuard — version history

Maintained by local Qoder. Each entry records what changed in the deployed cloud
configuration, newest first, so a reviewer can audit the build-up.

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
