"""Aggregates the log. The page does not recompute this."""

from __future__ import annotations

from typing import Iterable

from app.schemas import CostEvent, SavingsReport

_ROUTES = ("cache", "cheap", "retrieval", "mid", "premium")


def summarize(events: Iterable[CostEvent]) -> SavingsReport:
    rows = list(events)
    by_route = {name: 0 for name in _ROUTES}
    always = 0.0
    routed = 0.0
    escalated = 0
    cache_hits = 0
    for row in rows:
        by_route[row.route] = by_route.get(row.route, 0) + 1
        always += row.baseline_cost_usd
        routed += row.cost_usd
        if row.escalated:
            escalated += 1
        if row.cache_hit and not row.escalated:
            cache_hits += 1
    saved = always - routed
    pct = (saved / always * 100.0) if always else 0.0
    return SavingsReport(
        requests=len(rows),
        always_premium_usd=_money(always),
        routed_usd=_money(routed),
        saved_usd=_money(saved),
        saved_pct=round(pct, 1),
        by_route=by_route,
        escalated=escalated,
        cache_hits=cache_hits,
    )


def _money(value: float) -> float:
    return round(value, 6)
