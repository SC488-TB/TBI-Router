"""One baseline formula. Used by the live path and the replay. Do not mix."""

from __future__ import annotations

from app.config import Settings


def cost_usd(settings: Settings, alias: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = settings.prices[alias]
    return (
        prompt_tokens * price.input_per_million
        + completion_tokens * price.output_per_million
    ) / 1_000_000


def baseline_cost_usd(
    settings: Settings,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Always-premium estimate. Never calls the premium model.

    Completion estimate = max(actual completion tokens, ratio * prompt tokens).
    """
    estimated = max(
        completion_tokens,
        int(settings.baseline_completion_ratio * prompt_tokens),
    )
    return cost_usd(settings, "premium", prompt_tokens, estimated)
