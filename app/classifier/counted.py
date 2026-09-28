"""Counted intent margin. Not a fitted model.

The labeled set has 40 rows. That is too small to train on, so each intent
keeps a hand list of tokens. A score is how many of those tokens appear in
the prompt, divided by the length of the list. The margin is the top score
minus the second score.

Rules still win. This score is only allowed to pick an intent when no rule
matched and the margin is clear. It never calls a model.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.textutil import words

# Hand lists, not weights fit to prompts.jsonl. Keep them short so one shared
# word cannot clear the margin by itself.
TOKENS: Dict[str, List[str]] = {
    "code": ["refactor", "debug", "function", "traceback", "compile", "implement"],
    "lookup": ["policy", "ticket", "confluence", "status", "find"],
    "summarize": ["summarize", "summary", "tldr", "skim", "shorter"],
    "email_rewrite": ["email", "rewrite", "draft", "professional"],
    "rephrase": ["rephrase", "paraphrase", "differently"],
    "grammar": ["grammar", "proofread", "spelling"],
    "reasoning": ["why", "compare", "tradeoffs", "cause"],
}

# One hit in a 3-token list is 0.33. Require a clearer top than that, and a
# gap so two weak intents do not look like a decision.
MIN_SCORE = 0.34
MIN_MARGIN = 0.17


def score_intents(prompt: str) -> List[Tuple[str, float]]:
    """Return (intent, score) for every listed intent, highest first."""
    found = set(words(prompt))
    scored = []
    for intent, tokens in TOKENS.items():
        hits = sum(1 for token in tokens if token in found)
        scored.append((intent, hits / len(tokens)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def margin(prompt: str) -> Tuple[str, float, float]:
    """Return (top intent, top score, top minus second)."""
    ranked = score_intents(prompt)
    top_intent, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return top_intent, top_score, top_score - second


def confident(prompt: str) -> Tuple[str, float, float] | None:
    """Return the counted pick only when the margin is clear. Else None."""
    intent, score, gap = margin(prompt)
    if score >= MIN_SCORE and gap >= MIN_MARGIN:
        return intent, score, gap
    return None
