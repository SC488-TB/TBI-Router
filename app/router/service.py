"""Fan-out only. Does not call models, cache, or the quality gate."""

from __future__ import annotations

from dataclasses import dataclass

from app.router.policy import route_for
from app.schemas import Classification, RouteName


@dataclass(frozen=True)
class RouteDecision:
    route: RouteName
    cacheable: bool


class Router:
    def decide(self, classification: Classification, force_premium: bool) -> RouteDecision:
        route, cacheable = route_for(classification.intent, force_premium)
        return RouteDecision(route=route, cacheable=cacheable)
