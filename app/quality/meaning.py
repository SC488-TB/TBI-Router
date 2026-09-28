"""Overlap and entity checks. Not a generation call."""

from __future__ import annotations

from app.config import Settings
from app.textutil import content_words, entities, jaccard


def overlap_score(intent: str, source: str, answer: str) -> float | None:
    """Counted overlap, 0 to 1. None when this intent has no meaning check.

    This is the same count the pass/fail uses. It does not call a model and
    it does not move the threshold.
    """
    if intent == "summarize":
        words = content_words(answer)
        if not words:
            return 0.0
        source_set = set(content_words(source))
        return sum(1 for word in words if word in source_set) / len(words)
    if intent in {"rephrase", "email_rewrite"}:
        return jaccard(set(content_words(source)), set(content_words(answer)))
    if intent == "grammar":
        source_entities = entities(source)
        if not source_entities:
            return 1.0
        kept = source_entities & entities(answer)
        return len(kept) / len(source_entities)
    return None


def meaning_preserved(intent: str, source: str, answer: str, settings: Settings) -> bool:
    source_entities = entities(source)
    answer_entities = entities(answer)
    if intent == "summarize":
        overlap = overlap_score(intent, source, answer)
        invented = answer_entities - source_entities
        return bool(overlap) and overlap >= settings.summarize_overlap_floor and not invented
    if intent in {"rephrase", "email_rewrite"}:
        score = overlap_score(intent, source, answer) or 0.0
        dropped = source_entities - answer_entities
        return score >= settings.rewrite_jaccard_floor and not dropped
    if intent == "grammar":
        return not (source_entities - answer_entities)
    return True
