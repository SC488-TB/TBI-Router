"""Cheap-model label call. Closed set only. Temperature is the caller's concern."""

from __future__ import annotations

from typing import Optional

from app.gateway import Gateway, GatewayError
from app.schemas import Intent

INTENTS = (
    "code",
    "lookup",
    "summarize",
    "email_rewrite",
    "rephrase",
    "grammar",
    "reasoning",
    "ambiguous",
)

_SYSTEM = (
    "Label the user job with exactly one of: "
    + ", ".join(INTENTS)
    + ". Reply with the label only. No explanation."
)


def classify_with_model(gateway: Gateway, excerpt: str, context: str) -> Optional[Intent]:
    try:
        result = gateway.complete(
            "cheap",
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Context: {context}\n\n{excerpt}"},
            ],
            max_tokens=16,
            temperature=0,
        )
    except GatewayError:
        return None
    label = result.text.strip().lower().split()[0].strip(".,:;") if result.text.strip() else ""
    if label in INTENTS:
        return label  # type: ignore[return-value]
    return None
