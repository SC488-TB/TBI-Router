"""Replay the labeled set. Idempotent: deletes prior source=eval rows first."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.cost.savings import summarize
from app.orchestrator import Orchestrator
from app.schemas import RouteRequest, SavingsReport

_SET = Path(__file__).resolve().parent / "prompts.jsonl"


def load_prompts(path: Path = _SET) -> List[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def replay_set(orchestrator: Orchestrator, path: Path = _SET) -> SavingsReport:
    conn = orchestrator._logger._conn
    conn.execute("DELETE FROM cost_log WHERE source = 'eval'")
    conn.commit()
    prompts = load_prompts(path)
    for row in prompts:
        request = RouteRequest(
            prompt=row["prompt"],
            source="eval",
            looks_like_code=row.get("looks_like_code"),
        )
        orchestrator.route(request, source_override="eval")
    events = orchestrator._logger.list("eval", limit=10_000)
    return summarize(events)


def quality_note(orchestrator: Orchestrator, path: Path = _SET, limit: int = 10) -> List[dict]:
    """Ten live rows for the quality-vs-cost note. Includes one premium or escalated row."""
    replay_set(orchestrator, path)
    events = list(reversed(orchestrator._logger.list("eval", limit=10_000)))
    chosen = events[: limit - 1]
    held = next(
        (row for row in events if row.escalated or row.route == "premium"),
        None,
    )
    if held is not None and all(row.request_id != held.request_id for row in chosen):
        if len(chosen) >= limit:
            chosen[-1] = held
        else:
            chosen.append(held)
    return [_note_row(row) for row in chosen[:limit]]


def _note_row(row) -> dict:
    if row.escalated:
        gate = "fail"
    elif row.route == "premium":
        gate = "skipped"
    else:
        gate = "pass"
    return {
        "prompt": row.prompt,
        "route": row.route,
        "gate": gate,
        "cost_usd": row.cost_usd,
        "baseline_cost_usd": row.baseline_cost_usd,
    }


def accuracy(orchestrator_classify, path: Path = _SET) -> dict:
    """Classifier-only score. Does not spend a generation call."""
    rows = load_prompts(path)
    correct = 0
    misses = []
    for row in rows:
        result = orchestrator_classify(row["prompt"], row.get("source"), row.get("looks_like_code"))
        if result.intent == row["intent"]:
            correct += 1
        else:
            misses.append({"id": row["id"], "expected": row["intent"], "got": result.intent})
    total = len(rows) or 1
    return {"total": len(rows), "correct": correct, "accuracy": correct / total, "misses": misses}
