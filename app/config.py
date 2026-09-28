"""Model aliases, prices, and gate thresholds. No scattered model-id strings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class ModelPrice:
    """USD per 1M tokens. Baseline math uses these, never a live premium call."""

    input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class Settings:
    cheap_model: str
    premium_model: str
    mid_model: Optional[str]
    embed_model: Optional[str]
    prices: Dict[str, ModelPrice]
    # Completion-token estimate when we did not call premium.
    # baseline completion = max(actual_completion, ratio * prompt_tokens)
    baseline_completion_ratio: float = 0.5
    max_prompt_chars: int = 8000
    cheap_max_output_tokens: int = 512
    premium_max_output_tokens: int = 2048
    classifier_max_chars: int = 1500
    gateway_timeout_s: float = 30.0
    cache_jaccard_threshold: float = 0.85
    cache_ttl_days: int = 7
    summarize_overlap_floor: float = 0.40
    rewrite_jaccard_floor: float = 0.35
    too_short_chars: int = 15
    too_short_ratio: float = 0.10
    too_short_source_floor: int = 200
    database_path: str = "tbi_router.db"

    @property
    def mid_available(self) -> bool:
        return bool(self.mid_model)


def _price(env_in: str, env_out: str, default_in: float, default_out: float) -> ModelPrice:
    return ModelPrice(
        input_per_million=float(os.environ.get(env_in, default_in)),
        output_per_million=float(os.environ.get(env_out, default_out)),
    )


def load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines into the process. Does not override existing env."""
    file = Path(path)
    if not file.is_file():
        return
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_settings() -> Settings:
    load_dotenv()
    mid = os.environ.get("MID_MODEL", "").strip() or None
    embed = os.environ.get("EMBED_MODEL", "").strip() or None
    cheap = os.environ.get("CHEAP_MODEL", "cheap-stub")
    premium = os.environ.get("PREMIUM_MODEL", "premium-stub")
    prices = {
        "cheap": _price("CHEAP_INPUT_PER_M", "CHEAP_OUTPUT_PER_M", 0.15, 0.60),
        "premium": _price("PREMIUM_INPUT_PER_M", "PREMIUM_OUTPUT_PER_M", 5.00, 15.00),
        "mid": _price("MID_INPUT_PER_M", "MID_OUTPUT_PER_M", 1.00, 4.00),
    }
    db = os.environ.get("TBI_DATABASE", "tbi_router.db")
    return Settings(
        cheap_model=cheap,
        premium_model=premium,
        mid_model=mid,
        embed_model=embed,
        prices=prices,
        database_path=db,
    )
