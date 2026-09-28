"""Request, response, and cost-log shapes. No routing or pricing math."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal[
    "code",
    "lookup",
    "summarize",
    "email_rewrite",
    "rephrase",
    "grammar",
    "reasoning",
    "ambiguous",
]
RouteName = Literal["cache", "cheap", "retrieval", "mid", "premium"]
Source = Literal[
    "slack", "jira", "email", "ide", "docs", "ui", "eval",
    "confluence", "notion",
]
ClassifierMethod = Literal["rules", "counted", "small_model"]


class PromptScore(BaseModel):
    """Counted score for the text in the box. No model call and no log row."""

    method: str
    intent: Optional[Intent] = None
    signal: str
    signal_score: float = 0
    margin: float = 0
    ranked: List[dict] = Field(default_factory=list)


class RouteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    source: Optional[Source] = None
    looks_like_code: Optional[bool] = None
    force_premium: bool = False


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class RouteResponse(BaseModel):
    request_id: str
    intent: Intent
    classifier_method: ClassifierMethod
    route: RouteName
    route_label: str
    model: str
    answer: str
    cache_hit: bool
    escalated: bool
    escalate_reason: Optional[str] = None
    can_escalate: bool
    usage: Usage
    cost_usd: float
    baseline_cost_usd: float
    saved_usd: float
    quality_passed: Optional[bool] = None
    quality_reason: Optional[str] = None
    # Counted baseline beside the rule. Does not change the savings strip.
    signal: Optional[str] = None
    signal_score: Optional[float] = None
    signal_margin: Optional[float] = None
    overlap_score: Optional[float] = None
    logger_ok: bool = True
    notice: Optional[str] = None
    # Set only after a body was fetched. Example: "Jira · RFW-6529 · live".
    tool_line: Optional[str] = None
    latency_ms: int = 0


class CostEvent(BaseModel):
    request_id: str
    timestamp: str
    source: str
    prompt: str
    intent: Intent
    classifier_method: ClassifierMethod
    route: RouteName
    first_route: RouteName
    route_label: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    first_cost_usd: float
    cache_hit: bool
    baseline_cost_usd: float
    escalated: bool
    escalate_reason: Optional[str] = None
    saved_usd: float
    answer: str


class SavingsReport(BaseModel):
    requests: int
    always_premium_usd: float
    routed_usd: float
    saved_usd: float
    saved_pct: float
    by_route: Dict[str, int]
    escalated: int
    cache_hits: int


class GatewayResult(BaseModel):
    text: str
    prompt_tokens: int
    completion_tokens: int
    model_id: str
    finish_reason: str = "stop"


class Classification(BaseModel):
    intent: Intent
    confidence: float
    method: ClassifierMethod
    matched_rule: Optional[str] = None
    # Human line for the dashboard. Score is the counted baseline, 0 to 1.
    signal: Optional[str] = None
    signal_score: Optional[float] = None
    signal_margin: Optional[float] = None
