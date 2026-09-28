"""Premium passthrough. Does not decide whether to escalate."""

from __future__ import annotations

from app.gateway import Gateway
from app.schemas import GatewayResult


def run_premium(gateway: Gateway, prompt: str, max_tokens: int, reason: str) -> GatewayResult:
    return gateway.complete(
        "premium",
        [
            {
                "role": "system",
                "content": (
                    "Answer the user prompt directly. Do not shorten it. "
                    f"This call reached premium because: {reason}."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
