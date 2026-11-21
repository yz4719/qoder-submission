# Trading journal (competition account)

Status: reconstructed from user screenshots on 2026-11-20/21. No broker fill export
was available, so every row is marked **reported** (visible in the app) or
**inferred** (derived from the rules or the mark). Nothing here is a claimed fill.

## Known events

| Date | Event | Detail | P&L | Status |
| --- | --- | --- | --- | --- |
| 2026-11-20 | NVDA 261120 172.50 PUT | 26 contracts, mark 45.500, +71.49% on the position | +$49,322 at the mark (entry ≈ 26.53, inferred) | reported mark, entry inferred |
| 2026-11-20 (after close) | Auto-exercise of the ITM put | Per handbook §5, ITM options are exercised after the close; the account becomes short 2,600 NVDA at 172.50 | Unrealized +$122,122 at the 125.53 close | inferred from the rule |
| 2026-11-20 | AMD 261120 462.50 CALL | 3 contracts, cost 9.2333, OTM at expiry | −$2,770 | reported cost, expiry inferred |
| 2026-11-20 | NAV | $158,740.37 | +$58,740.37 since start (+58.74%) | reported |

Residual ≈ +$12,188.37 (marks and other activity not visible in the screenshots).
The P&L attribution in the report shows these three buckets separately so the
inferred parts are never mixed with reported ones.

## Open action

The short NVDA position is the only material risk left from these events. It is
outside the 40% stock/ETF exposure cap (exempt only because it came from an option
exercise) and violates the agent's `no_short_stock` gate. Buying to cover at the
current mark realizes the gain and restores a clean, verifiable account.

## Decision log (agent runs)

The demo run on 2026-11-21 produced four decisions, all logged in
`dashboard/data/decisions.jsonl`:

- `…-reconcile`: blocked — unverified positions, short stock, expired option.
- `…-bounce`: approved — SPY 700/720 Dec-18 call spread.
- `…-breakdown`: approved — SPY 680/660 Dec-18 put spread.
- `…-chop`: held — no confirmation.

These are hypothetical scenario runs against fixtures, not real fills. They exist
to show the gate behaviour and are labelled as such in the report.
