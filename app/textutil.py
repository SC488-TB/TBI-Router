"""Shared tokenization. Used by the cache and the meaning check. No I/O."""

from __future__ import annotations

import re
from typing import Iterable, Set

_STOP = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "to", "of", "in",
    "on", "for", "with", "at", "by", "from", "as", "is", "are", "was", "were",
    "be", "been", "being", "it", "this", "that", "these", "those", "i", "you",
    "we", "they", "he", "she", "my", "your", "our", "their", "me", "him", "her",
    "us", "them", "not", "no", "do", "does", "did", "can", "could", "should",
    "would", "will", "just", "please", "thanks", "thank", "hi", "hello",
}

_GREETINGS = re.compile(
    r"\b(hi|hello|hey|thanks|thank you|please|pls)\b",
    re.IGNORECASE,
)
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_ENTITY = re.compile(
    r"""
    (?:[A-Z]{2,}-\d+)               # TICKET-123
    | (?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})
    | (?:\$\d+(?:,\d{3})*(?:\.\d+)?)  # $12 or $1,200.50
    | (?:\b\d{4}-\d{2}-\d{2}\b)       # 2026-09-24
    | (?:\b\d{1,2}/\d{1,2}/\d{2,4}\b)
    | (?:\b\d+(?:\.\d+)?%?\b)         # numbers and percents
    """,
    re.VERBOSE,
)


def normalize(text: str) -> str:
    cleaned = _GREETINGS.sub(" ", text.lower())
    return _WS.sub(" ", cleaned).strip()


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def content_words(text: str) -> list[str]:
    return [w for w in words(text) if w not in _STOP and not w.isdigit()]


def shingles(tokens: Iterable[str], size: int = 3) -> Set[str]:
    toks = list(tokens)
    if len(toks) < size:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + size]) for i in range(len(toks) - size + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def entities(text: str) -> Set[str]:
    found = set()
    for match in _ENTITY.findall(text):
        token = match.strip().lower()
        if token:
            found.add(token)
    return found


def looks_like_code(text: str) -> bool:
    if "```" in text:
        return True
    cues = (
        "def ", "class ", "function ", "import ", "SELECT ", "const ", "let ",
        "fn ", "pub fn", "stack trace", "traceback", "syntaxerror", "compile error",
    )
    lowered = text.lower()
    if any(c.lower() in lowered for c in cues):
        return True
    fences = text.count("\n")
    symbols = sum(text.count(ch) for ch in "{}[];=()")
    return fences > 20 and symbols > 12
