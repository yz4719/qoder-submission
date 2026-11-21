"""Command-line entry point.

Examples:
    python3 -m leadguard demo
    python3 -m leadguard run --scenario bounce
    python3 -m leadguard live --mode dry_run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Config
from .log import DecisionLogger
from .orchestrator import LeadGuard
from .report import generate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leadguard", description="LeadGuard trading-agent package")
    parser.add_argument("--config", default="config/competition.json", help="path to competition.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run reconcile/bounce/breakdown/chop scenarios and generate the report")

    run = sub.add_parser("run", help="run one fixture scenario")
    run.add_argument("--scenario", required=True, choices=["bounce", "breakdown", "chop", "reconcile"])
    run.add_argument("--account", help="override account fixture")
    run.add_argument("--quotes", help="override quotes fixture")

    live = sub.add_parser("live", help="read the Moomoo account and run one decision cycle")
    live.add_argument("--mode", choices=["dry_run", "paper"], default="dry_run")
    live.add_argument("--confirm", action="store_true", help="required for paper execution")

    sub.add_parser("report", help="regenerate the HTML report from the existing log")

    args = parser.parse_args(argv)
    config = Config.load(args.config)
    root = config.base_dir or Path(args.config).resolve().parent
    logger = DecisionLogger(config.path_for("decisions", root), config.path_for("state", root))

    if args.command == "demo":
        guard = LeadGuard(config, _fixture_broker(config, root, "quotes_2026-11-20.json", "account_2026-11-20.json"), logger)
        state = guard.demo()
        report_path = generate(config.path_for("state", root), config.path_for("decisions", root), config.path_for("report", root))
        _print_demo(state, report_path)
        return 0

    if args.command == "run":
        account = Path(args.account) if args.account else root / "fixtures" / ("account_2026-11-20.json" if args.scenario == "reconcile" else "account_verified_example.json")
        quotes = Path(args.quotes) if args.quotes else root / "fixtures" / f"scenario_{args.scenario}.json"
        if args.scenario == "reconcile":
            quotes = Path(args.quotes) if args.quotes else root / "fixtures" / "quotes_2026-11-20.json"
        guard = LeadGuard(config, _fixture_broker(config, root, quotes.name, account.name), logger)
        from datetime import datetime

        when = datetime(2026, 11, 23, 9, 50) if args.scenario == "reconcile" else datetime(2026, 11, 23, 10, 0)
        decision, _ = guard.run_once(now_et=when, scenario=args.scenario, note="manual fixture run")
        print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if args.command == "live":
        guard = LeadGuard(config, _fixture_broker(config, root, "quotes_2026-11-20.json", "account_2026-11-20.json"), logger)
        decision, _ = guard.live(mode=args.mode, confirm=args.confirm)
        print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if args.command == "report":
        path = generate(config.path_for("state", root), config.path_for("decisions", root), config.path_for("report", root))
        print(f"report: {path}")
        return 0

    parser.error("unknown command")
    return 2


def _fixture_broker(config: Config, root: Path, quotes_name: str, account_name: str):
    from .broker import FixtureBroker

    return FixtureBroker(root / "fixtures" / account_name, root / "fixtures" / quotes_name)


def _print_demo(state: dict, report_path: Path) -> None:
    print("LeadGuard demo")
    for run in state.get("demo_runs", []):
        status = "APPROVED" if run.get("approved") else "NO ORDER"
        print(f"  {run['scenario']:10} {run['action']:16} {status:10} {run.get('signal_bias','')}")
        for blocker in run.get("blockers", [])[:3]:
            print(f"      blocked: {blocker}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    raise SystemExit(main())
