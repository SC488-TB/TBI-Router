"""Near-duplicate cache for the four cheap intents. See ADR 0005."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import Settings
from app.textutil import jaccard, normalize, shingles, words


@dataclass
class CacheHit:
    answer: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cache_key: str


class SemanticCache:
    def __init__(self, conn, settings: Settings) -> None:
        self._conn = conn
        self._settings = settings
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                intent TEXT NOT NULL,
                normalized TEXT NOT NULL,
                answer TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def lookup(self, intent: str, prompt: str) -> Optional[CacheHit]:
        normalized = normalize(prompt)
        if not normalized:
            return None
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self._settings.cache_ttl_days)
        ).isoformat()
        rows = self._conn.execute(
            """
            SELECT cache_key, normalized, answer, model, prompt_tokens, completion_tokens
            FROM cache
            WHERE intent = ? AND created_at >= ?
            """,
            (intent, cutoff),
        ).fetchall()
        incoming = shingles(words(normalized))
        best: Optional[CacheHit] = None
        best_score = 0.0
        for key, stored, answer, model, p_tok, c_tok in rows:
            if stored == normalized:
                return CacheHit(answer, model, p_tok, c_tok, key)
            score = jaccard(incoming, shingles(words(stored)))
            if score >= self._settings.cache_jaccard_threshold and score > best_score:
                best_score = score
                best = CacheHit(answer, model, p_tok, c_tok, key)
        return best

    def store(
        self,
        intent: str,
        prompt: str,
        answer: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        normalized = normalize(prompt)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO cache (
                cache_key, intent, normalized, answer, model,
                prompt_tokens, completion_tokens, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                answer = excluded.answer,
                model = excluded.model,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                created_at = excluded.created_at
            """,
            (f"{intent}:{normalized}", intent, normalized, answer, model, prompt_tokens, completion_tokens, now),
        )
        self._conn.commit()

    def delete(self, cache_key: str) -> None:
        self._conn.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
        self._conn.commit()
