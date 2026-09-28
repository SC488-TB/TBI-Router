"""Static intent → route table. Cache is a flag, not an intent."""

from __future__ import annotations

from typing import Dict, Tuple

from app.schemas import Intent, RouteName

# route, cacheable
POLICY: Dict[Intent, Tuple[RouteName, bool]] = {
    "code": ("premium", False),
    "lookup": ("retrieval", False),
    "summarize": ("cheap", True),
    "email_rewrite": ("cheap", True),
    "rephrase": ("cheap", True),
    "grammar": ("cheap", True),
    "reasoning": ("mid", False),
    "ambiguous": ("mid", False),
}

CACHEABLE_INTENTS = {intent for intent, (_, flag) in POLICY.items() if flag}


def route_for(intent: Intent, force_premium: bool) -> Tuple[RouteName, bool]:
    if force_premium:
        return "premium", False
    return POLICY[intent]
