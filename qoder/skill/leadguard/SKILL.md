---
name: leadguard
description: Run the LeadGuard paper-trading agent for the Moomoo x Qoder AI Trading Agent Challenge — evaluate SPY/QQQ/IWM regime, size a defined-risk vertical spread, enforce 19 risk gates, log the decision, and render the HTML decision report. Use when asked to evaluate a trading session, produce the daily trading decision, review risk limits, or regenerate the competition report.
---

# LeadGuard skill

Wraps the runnable package in `agent/`. The execution path is deterministic Python;
this skill exists so the agent invokes it consistently and never bypasses a gate.

## Commands

All commands run from `agent/`:

```bash
python3 -m leadguard demo
python3 -m leadguard --config config/guard.json demo
python3 -m leadguard run --scenario bounce
python3 -m leadguard live --mode dry_run
python3 -m leadguard report
```

## Workflow

1. Refresh `agent/fixtures/quotes_2026-11-20.json` (or point `paths.quotes` at a
   fresh snapshot) with verified quotes. Mark the `_meta.as_of` date.
2. Refresh the account fixture only from a verified position list. If positions
   are unknown, leave them as-is: the reconcile gate will block new risk, which is
   the correct outcome.
3. Run `demo` (or `run --scenario ...`) and read the printed decision lines.
4. If the decision is a spread, verify both legs against the live option chain
   before anything else. Fixture debits are illustrative, not quotes.
5. Regenerate the report and update `docs/DECISIONS.md` with the decision id.

## Non-negotiables

- Paper execution requires `--confirm` **and** `LEADGUARD_I_UNDERSTAND_PAPER=1`.
- Never edit a gate result to make a trade pass.
- Never place a trade on the user's behalf without explicit confirmation.
- Never claim a fill without an order id and a broker status.

## Output

The skill returns: decision id, action, gate verdict, max loss if approved, and
the path to `dashboard/report.html`.
