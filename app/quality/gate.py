"""Pass or fail a cheap-path answer. Does not escalate or log."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.config import Settings
from app.quality.meaning import meaning_preserved, overlap_score

_REFUSAL = re.compile(
    r"(as an ai|i can(?:not|'t) help|i cannot assist|i'm sorry, but i can't|"
    r"i am sorry, but i cannot)",
    re.IGNORECASE,
)
_END = re.compile(r"[.!?]$")
_MEANING_INTENTS = {"summarize", "email_rewrite", "rephrase", "grammar"}
_LENGTH_INTENTS = {"summarize", "email_rewrite", "rephrase"}


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason: Optional[str] = None
    # Counted overlap for meaning intents. None on premium, which never gets here.
    score: Optional[float] = None


def check(
    intent: str,
    source: str,
    answer: str,
    finish_reason: str,
    max_tokens: int,
    settings: Settings,
    check_meaning: bool,
) -> GateResult:
    raw = overlap_score(intent, source, answer or "") if answer else None
    score = round(raw, 2) if raw is not None else None
    if not answer or not answer.strip():
        return GateResult(False, "empty", score)
    text = answer.strip()
    if finish_reason == "length" or (
        not _END.search(text) and len(text) >= int(0.9 * max_tokens)
    ):
        return GateResult(False, "truncated", score)
    if _REFUSAL.search(text):
        return GateResult(False, "refusal", score)
    if intent in _LENGTH_INTENTS:
        if len(text) < settings.too_short_chars:
            return GateResult(False, "too_short", score)
        if len(source) > settings.too_short_source_floor and len(text) < settings.too_short_ratio * len(source):
            return GateResult(False, "too_short", score)
    if check_meaning and intent in _MEANING_INTENTS:
        if not meaning_preserved(intent, source, text, settings):
            return GateResult(False, "meaning", score)
    return GateResult(True, None, score)
