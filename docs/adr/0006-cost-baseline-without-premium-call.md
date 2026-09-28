# ADR 0006 — Log every call; baseline cost is estimated, never a premium call

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The savings number is the demo. It is only honest if every terminal outcome is logged and if "what always-premium would have cost" does not itself call the premium model. Calling premium to measure the baseline would erase the savings and the point of the week.

## Decision

Append one cost row per request before the response is returned. Update that row in place on escalate. Do not clip negative savings — an escalate that wasted a cheap call should show up.

Required fields: `request_id`, `timestamp`, `source`, `intent`, `classifier_method`, `route`, `first_route`, `model`, token counts, `cost_usd`, `cache_hit`, `baseline_cost_usd`, `escalated`, `escalate_reason`, `saved_usd`.

Baseline formula, one formula, used by the live path and the replay:

`baseline_cost = price(premium, this request's prompt tokens, estimated completion tokens)`

Estimated completion tokens = cheap completion tokens, or `max(cheap_completion_tokens, 0.5 * prompt_tokens)` if there are no completion tokens. Pick one in `prices.py`. Do not mix formulas. Do not call premium to learn the number.

Logger failure must not hide the answer. The UI says the call was not logged.

The page a judge sees first is three numbers: always premium $X, routed $Y, saved $Z (P%). The per-request table is below that. `GET /savings` is the source of truth if the page and the endpoint disagree.

## Consequences

- Prices live in config next to model aliases, not in the gateway and not in the UI.
- Eval replays are tagged `source=eval` so the demo total is the labeled set, not whatever was just pasted.
- Cache hits log cost $0 and still log a non-zero baseline.

## Related

- [Implementation plan §6](../plans/01-implementation-plan.md)
- [ADR 0004](0004-quality-gate-escalate-once.md)
