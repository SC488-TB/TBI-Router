"""Mid-tier, or the cheap stub when MID_MODEL is unset. See ADR 0008."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.gateway import Gateway
from app.schemas import GatewayResult


@dataclass
class MidResult:
    result: GatewayResult
    used_stub: bool
    alias: str


def run_mid(gateway: Gateway, settings: Settings, prompt: str, max_tokens: int) -> MidResult:
    if not settings.mid_available:
        result = gateway.complete(
            "cheap",
            [
                {"role": "system", "content": "Give a short, careful answer. Mid-tier is unavailable."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return MidResult(result=result, used_stub=True, alias="cheap")
    result = gateway.complete(
        "mid",
        [
            {"role": "system", "content": "Reason about the request. Be direct."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
    return MidResult(result=result, used_stub=False, alias="mid")
