"""Keyword rules. First match wins. `code` is first so it outranks 'summarize'."""

from __future__ import annotations

import re
from typing import List, Optional, Pattern, Tuple

from app.textutil import looks_like_code as text_looks_like_code

# (rule name, intent, pattern). Order is priority.
RULES: List[Tuple[str, str, Pattern[str]]] = [
    (
        "code-keywords",
        "code",
        re.compile(
            r"\b(refactor|debug|stack\s*trace|traceback|compile\s+error|"
            r"write\s+a\s+function|implement\s+a|multi-?file|pull\s+request|"
            r"unit\s+test|this\s+function|this\s+class|architecture\s+of)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "lookup",
        "lookup",
        re.compile(
            r"\b(what(?:'s| is) our|policy|status of|ticket-\d+|jira-\d+|"
            r"confluence|where do i find|what does the .+ say)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "email",
        "email_rewrite",
        re.compile(
            r"\b(rewrite this email|draft (?:a |an )?(?:reply|email)|"
            r"sound more professional|email draft|this email)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "rephrase",
        "rephrase",
        re.compile(r"\b(rephrase|say this differently|paraphrase)\b", re.IGNORECASE),
    ),
    (
        "grammar",
        "grammar",
        re.compile(r"\b(fix grammar|proofread|clean this up|grammar)\b", re.IGNORECASE),
    ),
    (
        "summarize",
        "summarize",
        re.compile(
            r"\b(summarize|summarise|tl;?dr|bullet these|make this shorter|"
            r"into bullets|key points)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "reasoning",
        "reasoning",
        re.compile(
            r"\b(why did|compare these|what should we do|trade-?offs?|"
            r"pros and cons|root cause)\b",
            re.IGNORECASE,
        ),
    ),
]


def match_rules(
    prompt: str,
    looks_like_code: Optional[bool],
    length: int,
) -> Optional[Tuple[str, str]]:
    """Return (rule name, intent) or None when unsure."""
    if length < 20 and not any(rule[2].search(prompt) for rule in RULES):
        return None

    code_signal = bool(looks_like_code) or text_looks_like_code(prompt)
    # A short snippet inside an email, grammar fix, or summary is not a code job.
    language_chore = bool(
        RULES[2][2].search(prompt)
        or RULES[3][2].search(prompt)
        or RULES[4][2].search(prompt)
        or RULES[5][2].search(prompt)
    )
    if code_signal and not language_chore:
        return ("code-context", "code")

    hits = [(name, intent) for name, intent, pattern in RULES if pattern.search(prompt)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        # First-match priority already encoded by RULES order.
        return hits[0]
    return None
