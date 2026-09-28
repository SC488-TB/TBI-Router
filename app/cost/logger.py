"""One SQLite row per request. Updated in place on escalate."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from app.schemas import CostEvent


class CostLogger:
    def __init__(self, conn) -> None:
        self._conn = conn
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_log (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                prompt TEXT NOT NULL,
                intent TEXT NOT NULL,
                classifier_method TEXT NOT NULL,
                route TEXT NOT NULL,
                first_route TEXT NOT NULL,
                route_label TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                first_cost_usd REAL NOT NULL,
                cache_hit INTEGER NOT NULL,
                baseline_cost_usd REAL NOT NULL,
                escalated INTEGER NOT NULL,
                escalate_reason TEXT,
                saved_usd REAL NOT NULL,
                answer TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cost_source_time ON cost_log(source, timestamp)"
        )
        self._conn.commit()

    def write(self, event: CostEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO cost_log (
                request_id, timestamp, source, prompt, intent, classifier_method,
                route, first_route, route_label, model, prompt_tokens, completion_tokens,
                cost_usd, first_cost_usd, cache_hit, baseline_cost_usd, escalated,
                escalate_reason, saved_usd, answer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                timestamp = excluded.timestamp,
                route = excluded.route,
                route_label = excluded.route_label,
                model = excluded.model,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                cost_usd = excluded.cost_usd,
                cache_hit = excluded.cache_hit,
                baseline_cost_usd = excluded.baseline_cost_usd,
                escalated = excluded.escalated,
                escalate_reason = excluded.escalate_reason,
                saved_usd = excluded.saved_usd,
                answer = excluded.answer
            """,
            (
                event.request_id,
                event.timestamp,
                event.source,
                event.prompt,
                event.intent,
                event.classifier_method,
                event.route,
                event.first_route,
                event.route_label,
                event.model,
                event.prompt_tokens,
                event.completion_tokens,
                event.cost_usd,
                event.first_cost_usd,
                int(event.cache_hit),
                event.baseline_cost_usd,
                int(event.escalated),
                event.escalate_reason,
                event.saved_usd,
                event.answer,
            ),
        )
        self._conn.commit()

    def get(self, request_id: str) -> Optional[CostEvent]:
        row = self._conn.execute(
            "SELECT * FROM cost_log WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        return _event(row)

    def list(self, source: Optional[str], limit: int) -> List[CostEvent]:
        try:
            if source:
                rows = self._conn.execute(
                    """
                    SELECT * FROM cost_log WHERE source = ?
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (source, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM cost_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        except sqlite3.DatabaseError:
            return []
        return [_event(row) for row in rows]


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return "" if value is None else str(value)


def _event(row: sqlite3.Row) -> CostEvent:
    return CostEvent(
        request_id=row["request_id"],
        timestamp=row["timestamp"],
        source=row["source"],
        prompt=row["prompt"],
        intent=row["intent"],
        classifier_method=row["classifier_method"],
        route=row["route"],
        first_route=row["first_route"],
        route_label=row["route_label"],
        model=row["model"],
        prompt_tokens=row["prompt_tokens"],
        completion_tokens=row["completion_tokens"],
        cost_usd=row["cost_usd"],
        first_cost_usd=row["first_cost_usd"],
        cache_hit=bool(row["cache_hit"]),
        baseline_cost_usd=row["baseline_cost_usd"],
        escalated=bool(row["escalated"]),
        escalate_reason=row["escalate_reason"],
        saved_usd=row["saved_usd"],
        answer=_text(row["answer"]),
    )
