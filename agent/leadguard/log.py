"""Append-only JSONL decision log and atomic state snapshots."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .models import Decision


class DecisionLogger:
    def __init__(self, decisions_path: str | Path, state_path: str | Path):
        self.decisions_path = Path(decisions_path)
        self.state_path = Path(state_path)
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, decision: Decision) -> None:
        with self.decisions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def reset(self) -> None:
        self.decisions_path.write_text("", encoding="utf-8")

    def write_state(self, state: dict[str, Any]) -> None:
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def read(self) -> list[dict[str, Any]]:
        return load_decisions(self.decisions_path)


def load_decisions(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_demo_state(states: Iterable[dict[str, Any]], latest: dict[str, Any]) -> dict[str, Any]:
    combined = dict(latest)
    combined["demo_runs"] = [
        {
            "scenario": item.get("scenario"),
            "decision_id": item.get("decision", {}).get("decision_id"),
            "action": item.get("decision", {}).get("proposal", {}).get("action"),
            "approved": item.get("decision", {}).get("risk", {}).get("approved"),
            "nav": item.get("decision", {}).get("nav"),
        }
        for item in states
    ]
    return combined
