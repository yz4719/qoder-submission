"""Generate a standalone HTML report from the decision log.

The report embeds its data, so it can be opened from the filesystem or attached
to a submission without running a server.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .log import load_decisions


def generate(
    state_path: str | Path,
    decisions_path: str | Path,
    output_path: str | Path,
) -> Path:
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    decisions = load_decisions(decisions_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render(state, decisions), encoding="utf-8")
    return out


def _render(state: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    account = state.get("account", {})
    decision = state.get("decision", {})
    proposal = decision.get("proposal", {})
    risk = decision.get("risk", {})
    market = state.get("market", {})
    nav = _f(account.get("nav"))
    initial = 100000.0
    total_pnl = nav - initial
    total_pct = total_pnl / initial * 100 if initial else 0.0
    drawdown = _f(account.get("drawdown_pct"))
    cash_pct = _f(account.get("cash_pct"))
    latest_action = proposal.get("action", "N/A")
    approved = bool(risk.get("approved"))
    no_order = latest_action in ("HOLD", "RECONCILE") or not proposal.get("legs")
    gate_foot = "no order submitted" if no_order else ("risk gate: pass" if approved else "risk gate: blocked")
    regime = market.get("regime", "N/A")
    vix = _f(market.get("vix"))
    demo_runs = state.get("demo_runs", [])
    reported = state.get("reported_account") or _reported_account(state)
    positions = reported.get("positions", []) if reported else []
    latest_checks = risk.get("checks", [])
    blockers = risk.get("blockers", [])
    limits = state.get("limits") or {}
    daily_limit = _f(limits.get("daily_loss_pct", 3.0))
    soft_stop = _f(limits.get("soft_stop_pct", 6.0))
    kill_switch = _f(limits.get("kill_switch_pct", 10.0))
    min_cash = _f(limits.get("min_cash_pct", 80.0))
    day_loss_pct = _f(account.get("day_pnl")) / nav * 100 if nav else 0.0

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeadGuard — Decision Report</title>
<style>
:root {{
  --bg:#0b1020; --panel:#141b31; --panel2:#1b2440; --text:#e8edf8; --muted:#9aa8c7;
  --green:#38d39f; --red:#ff6b7a; --amber:#ffcc66; --blue:#6aa8ff; --line:#2a3658;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:linear-gradient(160deg,#080c18 0%,#0b1020 55%,#101a33 100%); color:var(--text);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:34px 22px 60px; }}
header {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-end; border-bottom:1px solid var(--line); padding-bottom:20px; }}
h1 {{ margin:0; font-size:32px; letter-spacing:-.5px; }}
h2 {{ margin:32px 0 12px; font-size:20px; letter-spacing:-.2px; }}
h3 {{ margin:0 0 8px; font-size:14px; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.08em; }}
.sub {{ color:var(--muted); margin-top:6px; }}
.badge {{ display:inline-block; padding:5px 10px; border-radius:999px; font-size:12px; font-weight:700; border:1px solid var(--line); }}
.badge.ok {{ color:var(--green); border-color:#1d6b51; background:#0d2a22; }}
.badge.no {{ color:var(--red); border-color:#7a2b38; background:#2a1017; }}
.badge.warn {{ color:var(--amber); border-color:#715a22; background:#2a230f; }}
.grid {{ display:grid; gap:14px; }}
.kpis {{ grid-template-columns:repeat(6,1fr); margin-top:22px; }}
.card {{ background:linear-gradient(180deg,var(--panel),var(--panel2)); border:1px solid var(--line); border-radius:14px; padding:16px; }}
.kpi .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.kpi .value {{ font-size:24px; font-weight:750; margin-top:6px; letter-spacing:-.5px; }}
.kpi .foot {{ color:var(--muted); font-size:12px; margin-top:4px; }}
.pos {{ color:var(--green); }} .neg {{ color:var(--red); }} .warn {{ color:var(--amber); }} .blue {{ color:var(--blue); }}
.two {{ grid-template-columns:1.25fr .75fr; }}
.three {{ grid-template-columns:repeat(3,1fr); }}
.table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.table th {{ text-align:left; color:var(--muted); font-weight:600; padding:8px 10px; border-bottom:1px solid var(--line); }}
.table td {{ padding:9px 10px; border-bottom:1px solid #202a47; vertical-align:top; }}
.table tr:last-child td {{ border-bottom:none; }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; }}
.decision {{ border-left:3px solid var(--line); padding:10px 12px; margin:10px 0; background:#0f1730; border-radius:0 10px 10px 0; }}
.decision.ok {{ border-left-color:var(--green); }}
.decision.no {{ border-left-color:var(--red); }}
.decision.hold {{ border-left-color:var(--amber); }}
.decision .top {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
.decision .name {{ font-weight:700; }}
.decision .why {{ color:var(--muted); font-size:13px; margin-top:6px; }}
.chart {{ width:100%; height:auto; display:block; }}
.legend {{ color:var(--muted); font-size:12px; margin-top:8px; }}
.code {{ background:#080d1a; border:1px solid var(--line); border-radius:10px; padding:12px 14px; overflow:auto; font-size:12px; }}
.note {{ color:var(--muted); font-size:12px; }}
.fail {{ border-left:3px solid var(--red); padding-left:12px; margin:12px 0; }}
footer {{ margin-top:40px; border-top:1px solid var(--line); padding-top:16px; color:var(--muted); font-size:12px; }}
@media (max-width:900px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} .two,.three {{ grid-template-columns:1fr; }} header {{ flex-direction:column; align-items:flex-start; }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <div class="badge blue">MOOMOO × QODER · PAPER TRADING AGENT</div>
    <h1>LeadGuard</h1>
    <div class="sub">Post-crash capital preservation with defined-risk rebound. Decision report generated from the append-only log.</div>
  </div>
  <div style="text-align:right">
    <div class="badge {'ok' if approved else 'warn'}">{'RISK APPROVED' if approved else 'NO NEW RISK'}</div>
    <div class="sub mono">as of {html.escape(str(decision.get('ts_et','') or '2026-11-20'))}</div>
  </div>
</header>

<div class="grid kpis">
  <div class="card kpi"><div class="label">NAV</div><div class="value">${nav:,.2f}</div><div class="foot">initial $100,000</div></div>
  <div class="card kpi"><div class="label">Total P&amp;L</div><div class="value {'pos' if total_pnl>=0 else 'neg'}">{'+' if total_pnl>=0 else ''}{total_pnl:,.2f}</div><div class="foot">{total_pct:+.2f}%</div></div>
  <div class="card kpi"><div class="label">Drawdown</div><div class="value {'neg' if drawdown>=5 else ''}">{drawdown:.2f}%</div><div class="foot">kill switch {kill_switch:.2f}%</div></div>
  <div class="card kpi"><div class="label">Cash</div><div class="value">{cash_pct:.1f}%</div><div class="foot">minimum {min_cash:.0f}%</div></div>
  <div class="card kpi"><div class="label">Regime</div><div class="value">{html.escape(str(regime)).title()}</div><div class="foot">VIX {vix:.2f}</div></div>
  <div class="card kpi"><div class="label">Latest action</div><div class="value">{html.escape(str(latest_action))}</div><div class="foot">{gate_foot}</div></div>
</div>

<h2>What the agent decided</h2>
<div class="two grid">
  <div class="card">
    {_decision_cards(demo_runs)}
  </div>
  <div class="card">
    <h3>Risk gates on the latest proposal</h3>
    {_checks_table(latest_checks)}
    {_blockers(blockers)}
  </div>
</div>

<h2>Account reconstruction</h2>
<div class="two grid">
  <div class="card">
    <h3>Reported positions (unverified)</h3>
    {_positions_table(positions)}
    <div class="note" style="margin-top:10px">The NVDA short is <b>inferred</b> from the ITM 11-20 put assignment; the AMD call is shown as expired. Verify both in the app before trading. This is why the first decision is RECONCILE, not a new trade.</div>
  </div>
  <div class="card">
    <h3>Known P&amp;L attribution</h3>
    {_pnl_chart()}
    <div class="note" style="margin-top:8px">NVDA put entry is inferred from the screenshot's +71.49% at a 45.50 mark. Residual includes marks and trades not visible in the screenshot.</div>
  </div>
</div>

<h2>Risk budget</h2>
<div class="card">
  {_risk_chart(daily_limit, soft_stop, kill_switch, drawdown, day_loss_pct)}
  <div class="legend">Daily loss limit {daily_limit:.0f}% · soft stop {soft_stop:.0f}% · hard kill {kill_switch:.0f}%. The agent stops opening new risk at {soft_stop:.0f}% drawdown and flattens at {kill_switch:.0f}%.</div>
</div>

<h2>What failed, and what changed</h2>
<div class="card">
  <div class="fail"><b>Holding a deep-ITM option to expiry.</b> The 11-20 172.50 put was auto-exercised after Friday's close, converting an option into a leveraged short stock position. The fix is a reconcile-first gate and a hard no-hold-to-expiry rule.</div>
  <div class="fail"><b>Concentrated AI single-name risk.</b> NVDA fell 14% and AMD 13% on Friday. The new universe is SPY/QQQ/IWM only; NVDA and AMD are blocked until the account is verified flat.</div>
  <div class="fail"><b>Lottery-ticket call.</b> AMD 462.50C cost 2,770 and expired worthless. The fix is a 5% max premium-at-risk budget (1.5% in guard) and a defined-risk spread, not a cheap OTM call.</div>
  <div class="fail"><b>No pre-defined exit or reconciliation.</b> The account was not checked before expiry. The fix is a daily reconciliation step, a structured decision log, and a kill switch.</div>
</div>

<h2>How to run the package</h2>
<div class="card">
  <div class="code mono">cd agent<br>python3 -m leadguard demo<br># open ../dashboard/report.html<br><br># live read-only (after Moomoo CLI OAuth):<br>python3 -m leadguard live --mode dry_run</div>
  <div class="note" style="margin-top:10px">Dry-run needs no credentials. Paper execution is blocked unless live option bid/ask replaces every placeholder price, <span class="mono">--confirm</span> is passed, and <span class="mono">LEADGUARD_I_UNDERSTAND_PAPER=1</span> is set.</div>
</div>

<footer>
  Simulated results only; not investment advice. Some figures are inferred from user screenshots and are labelled as such. The organisers' backend records prevail. Competition rules: U.S.-listed stocks/ETFs/options only; options may be auto-exercised at expiry; system exploitation is prohibited.
</footer>
</div>
</body>
</html>"""


def _decision_cards(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return '<div class="note">No demo runs yet. Run <span class="mono">python3 -m leadguard demo</span>.</div>'
    parts = []
    for run in runs:
        action = str(run.get("action", "N/A"))
        approved = bool(run.get("approved"))
        cls = "ok" if approved else ("hold" if action in {"HOLD", "RECONCILE"} else "no")
        reasons = run.get("reasons") or []
        blockers = run.get("blockers") or []
        why = " · ".join(str(x) for x in reasons[:3])
        if blockers:
            why += " · BLOCKED: " + "; ".join(str(x) for x in blockers[:3])
        parts.append(
            f'<div class="decision {cls}"><div class="top"><div class="name">{html.escape(str(run.get("scenario","")).title())} · {html.escape(action)}</div>'
            f'<div class="badge {"ok" if approved else "warn"}">{"APPROVED" if approved else "NO ORDER"}</div></div>'
            f'<div class="why">{html.escape(why)}</div></div>'
        )
    return "".join(parts)


def _checks_table(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return '<div class="note">No checks recorded.</div>'
    rows = []
    for check in checks:
        passed = bool(check.get("passed"))
        rows.append(
            f'<tr><td class="mono">{html.escape(str(check.get("name","")))}</td>'
            f'<td class="{"pos" if passed else "neg"}">{"PASS" if passed else "BLOCK"}</td>'
            f'<td class="note">{html.escape(str(check.get("detail","")))}</td></tr>'
        )
    return f'<table class="table"><thead><tr><th>Gate</th><th>Result</th><th>Detail</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def _blockers(blockers: list[str]) -> str:
    if not blockers:
        return ""
    items = "".join(f"<li>{html.escape(str(item))}</li>" for item in blockers)
    return f'<div class="fail" style="margin-top:12px"><b>Blockers</b><ul>{items}</ul></div>'


def _positions_table(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return '<div class="note">No positions in the verified example account.</div>'
    rows = []
    for p in positions:
        qty = _f(p.get("qty"))
        pnl = _f(p.get("unrealized_pnl"))
        rows.append(
            f'<tr><td class="mono">{html.escape(str(p.get("symbol","")))}</td>'
            f'<td>{qty:g}</td><td>${_f(p.get("market_value")):,.2f}</td>'
            f'<td class="{"pos" if pnl>=0 else "neg"}">{pnl:+,.2f}</td>'
            f'<td class="note">{html.escape(str(p.get("note","")))}</td></tr>'
        )
    return f'<table class="table"><thead><tr><th>Symbol</th><th>Qty</th><th>Value</th><th>Unrealized</th><th>Note</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def _pnl_chart() -> str:
    items = [("NVDA put (inferred)", 49322.0, "pos"), ("AMD call", -2770.0, "neg"), ("Residual / other marks", 12188.37, "warn")]
    width, height = 560, 160
    max_abs = max(abs(v) for _, v, _ in items) or 1
    bars = []
    for i, (label, value, cls) in enumerate(items):
        y = 18 + i * 46
        w = abs(value) / max_abs * 300
        x = 190 if value >= 0 else 190 - w
        color = {"pos": "#38d39f", "neg": "#ff6b7a", "warn": "#ffcc66"}[cls]
        bars.append(f'<text x="0" y="{y+13}" fill="#9aa8c7" font-size="12">{html.escape(label)}</text>')
        bars.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="4" fill="{color}" opacity=".85"/>')
        bars.append(f'<text x="{x + w + 8 if value>=0 else x - 8}" y="{y+14}" fill="{color}" font-size="12" text-anchor="{"start" if value>=0 else "end"}">{value:+,.0f}</text>')
    return f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="P and L attribution">{"".join(bars)}</svg>'


def _risk_chart(daily: float, soft: float, kill: float, drawdown: float, day_loss: float) -> str:
    width, height = 900, 120
    levels = [("0%", 0.0, "#38d39f"), (f"{daily:.0f}% daily loss", daily, "#ffcc66"), (f"{soft:.0f}% soft stop", soft, "#ff9f43"), (f"{kill:.0f}% kill", kill, "#ff6b7a")]
    usable = 760
    x0 = 90
    scale = max(kill, 1.0)
    marks = []
    for label, pct, color in levels:
        x = x0 + pct / scale * usable
        marks.append(f'<line x1="{x}" y1="25" x2="{x}" y2="78" stroke="{color}" stroke-width="2"/>')
        marks.append(f'<text x="{x}" y="98" fill="{color}" font-size="12" text-anchor="middle">{html.escape(label)}</text>')
    fill = max(0.0, min(drawdown, scale)) / scale * usable
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Risk budget">'
        f'<rect x="{x0}" y="42" width="{usable}" height="14" rx="7" fill="#223055"/>'
        f'<rect x="{x0}" y="42" width="{fill}" height="14" rx="7" fill="#38d39f"/>'
        f'{"".join(marks)}'
        f'<text x="{x0}" y="20" fill="#9aa8c7" font-size="12">Current drawdown {drawdown:.2f}% · day P&amp;L {day_loss:+.2f}% of NAV</text>'
        f'</svg>'
    )


def _reported_account(state: dict[str, Any]) -> dict[str, Any] | None:
    for item in state.get("demo_states", []):
        if item.get("scenario") == "reconcile":
            return item.get("account")
    return None


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
