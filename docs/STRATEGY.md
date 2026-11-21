# LeadGuard — one-week competition playbook

Moomoo x Qoder AI Trading Agent Challenge · trading window 17–28 Nov 2026 ·
submission deadline 30 Nov 2026 23:59 SGT · $100,000 paper start.

This document is the strategy the package implements. It has three profiles with
the same hard rules and different size: `competition` (the default, 5% per trade),
`guard` (conservative, 1.5% per trade) and `chase` (15% per trade, only for a step
change). The competition profile is the one designed to win.

---

## 1. Where we actually stand

| Item | Value | Status |
| --- | --- | --- |
| Start NAV | $100,000.00 | verified rule |
| Current NAV (11-20) | $158,740.37 | reported by user screenshot |
| Return | +58.74% | derived |
| Position | NVDA short ≈ 2,600 shares, inferred from ITM 11-20 put assignment | **inferred — must verify** |
| Expired | AMD 11-20 462.50C ×3, −$2,770 | reported |
| Buying power | $485,118.37 reported (pre-settlement; not cash) | needs reconciliation |

The +58.7% is the result of one deep-ITM NVDA put held into expiry. That is a real
lead, and it also created an unhedged short-stock position that violates every
risk rule in this playbook. Monday's first job is not a new trade — it is covering
the short and confirming the settled position list. The package enforces this with
the reconcile gate: while positions are unverified or a short stock exists, every
new proposal is replaced by `RECONCILE`.

## 2. The one-week thesis

Friday 2026-11-20 was a broad risk-off day: S&P 500 6910.39 (−3.7%), NDX −5.6%,
VIX 35.89 (+26%), NVDA −14%, AMD −13%. That combination usually produces one of
three short-term paths:

1. **Violent mean-reversion bounce** (most common after a VIX spike with no
   systemic credit event): indices reclaim part of the loss over 2–5 sessions.
2. **Continuation lower** if the selloff was the start of a de-risking cycle.
3. **Chop** around the new range while the market waits for data.

The agent does not predict which one. It requires confirmation and buys a
defined-risk spread only after the tape picks a side. That is the edge: **the
strategy is paid for its patience, not its forecast**. In a one-week sprint most
of the return has to come from one or two asymmetric, already-confirmed moves,
and the rest of the value comes from not giving the +58.7% back.

### Confirmation rules (deterministic, from `config/*.json`)

Long (bounce) requires all three at the 09:45–15:30 ET check:

- SPY ≥ 695.00
- QQQ ≥ 612.00
- VIX ≤ 34.00 (cooling, not spiking)

Short (breakdown) requires all three:

- SPY ≤ 686.75 (below Friday's close)
- QQQ ≤ 606.23
- VIX ≥ 34.00 (stress persisting)

Anything else is `HOLD`. Cash is a position.

### Why a vertical spread and not the underlying

- Defined risk: the maximum loss is the debit, known before entry.
- No assignment: a long option can be auto-exercised at expiry; a spread requires
  an explicit close, and the agent closes before expiry by rule.
- No naked short exposure, no margin call, no overnight gap risk beyond the debit.
- The rubric scores risk design. A spread with a stated max loss and invalidation
  scores better than a leveraged single-name bet, even at the same P&L.

## 3. Trade plan (competition profile)

| Scenario | Structure | Debit (illustrative) | Size | Max loss | Payoff at short strike |
| --- | --- | --- | --- | --- | --- |
| Bounce confirmed | SPY 18-Dec 700/720 call spread | 8.00 | 9 contracts | $7,200 (4.5%) | +$10,800 (+6.8%) |
| Breakdown confirmed | SPY 18-Dec 680/660 put spread | 9.00 | 8 contracts | $7,200 (4.5%) | +$8,800 (+5.5%) |

If the leaderboard requires a step change, `config/chase.json` raises the caps to
15% per trade and 30% total: 29 call spreads ($23,200, 14.6%) or 26 put spreads
($23,400, 14.7%), with a +$58,000 payoff at the short strike and roughly −$11,600
(−7.3%) if the −50% stop is hit. It is deliberately **not** 40%: a 40% debit with
a −50% stop would give back ~20% of NAV in one failed bounce and destroy the
risk-adjusted score that is 25% of the rubric.

Sizing is computed by the agent, not typed in:
`qty = min(max_contracts, floor(risk_budget / (debit × 100)))` with
`risk_budget = NAV × 5%`. If the debit is too high for one contract, the agent
holds instead of oversizing.

Exit ladder for any open spread:

| Trigger | Action |
| --- | --- |
| +50% of debit | sell half |
| +80–100% of debit | close the rest |
| −50% of debit | close, no averaging down |
| Wednesday 13:00 ET | no new positions; manage only |
| Friday 12:30 ET | flatten everything, no exceptions |

The 18-Dec expiry is deliberate: enough DTE to survive a headline, close enough
that the payoff is not a slow theta bleed, and closed long before expiry so the
auto-exercise rule never applies.

## 4. Risk ladder

| Level | Trigger | Response |
| --- | --- | --- |
| Daily loss | −3% of NAV in one session | stop opening risk for the day |
| Soft stop | −6% from peak NAV | no new positions; manage exits only |
| Kill switch | −10% from peak NAV | flatten all, stop trading, write post-mortem |
| Reconcile | unverified / short stock / option ≤2 DTE | block new risk until flat and verified |
| Calendar | after Wed 13:00 ET | no new positions |
| Final | Fri 12:30 ET | flat |

The guard profile tightens these to 2% / 5% / 8% and 1.5% per trade. The chase
profile loosens them to 4% / 8% / 12% and 15% per trade. Same code, different
JSON. The report shows which profile produced each decision.

## 5. Anti-cheating and platform compliance

- US-listed stocks, ETFs, and options only. No crypto, no non-US names.
- Stock/ETF exposure may not exceed 40% of initial account assets; options are
  excluded from that cap but a single option contract is capped at 1,000 contracts.
  The inferred NVDA short is far above the cap but is exempt because it arose from
  an option exercise — another reason to cover it immediately.
- Final ranking uses the regular-market closing price on the final day; after-hours
  trades on that day do not count. The Friday 12:30 ET flatten sits inside RTH.
- Max 200 executed orders/day, max 100 positions, stocks under USD 1 and companies
  under USD 500m market cap are ineligible. None bind this plan.
- No exploitation of platform bugs, latency, or pricing errors — disqualifying per
  the rules, and not needed: the edge is process, not arbitrage.
- One account, no resets. Every decision is logged with inputs and gate results,
  so the strategy can be audited against the organisers' backend.
- Option fees are modelled from the handbook: USD 0.65 commission + USD 0.30
  platform + USD 0.00279 activity + USD 0.015 regulatory ≈ USD 0.968 per contract,
  minimum USD 1.99 per order. A 9-contract spread is 18 contracts ≈ USD 17.42 per
  side, ≈ USD 34.84 round trip, about 0.5% of the debit.
- The agent never claims a fill without an order id.

## 6. Judging alignment

| Criterion | Weight | How this package scores |
| --- | --- | --- |
| Risk-adjusted return | 25% | Defined risk, 10% max open risk, kill switch, +58.7% protected |
| Qoder & Cloud Agent usage | 30% | Local Qoder built the package; Cloud Agent runs the coordinator/researcher/auditor loop; prompts in `agent/prompts/` |
| Strategy & risk design | 30% | Explicit thesis, confirmation levels, invalidation, sizing math, drawdown ladder |
| Reusability & documentation | 15% | Config-driven, stdlib-only, tests, skill, runbook, decision log, HTML report |

## 7. What could go wrong

| Risk | Response |
| --- | --- |
| Bounce never confirms | Agent holds; zero P&L cost, lead preserved |
| Confirmed long fails immediately | −50% stop ≈ −$3,600 (−2.3% NAV) |
| Gap through the short strike | Loss capped at debit; no assignment |
| NVDA short not covered before Monday open | Unbounded risk — cover first, this is the top priority |
| OAuth / CLI unavailable | Dry run still produces decisions and the report; execution waits |
| Leaderboard leader far ahead | Do not chase with lottery tickets; the rubric still scores risk design. If chasing is required, switch to `config/chase.json` (15% per trade / 30% total, 12% kill switch) — never remove the stops |

## 8. Upload plan

The submission requires a Qoder-generated deck plus the runnable package, a
decision log, results, and a demo of what worked and failed. This repo provides:
`deck/index.html`, `agent/`, `dashboard/report.html`, `docs/`, and the JSONL log.

The Luma submission link was checked on 21 Nov and currently serves a different
event's survey (QwenWork x Hashmeta OPC Hackathon). Before the deadline, re-open
the Luma event page and use the current "Submit" link; if none appears, the
fallback is a shareable repo/report link submitted through the event's contact
channel. Do not wait until 30 Nov to check.
