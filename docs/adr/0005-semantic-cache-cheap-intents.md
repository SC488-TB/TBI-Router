# ADR 0005 — Semantic cache for cheap, repeat-heavy intents only

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The same ticket gets summarized more than once. The same paragraph gets rephrased in Slack. Those repeats are where a cache pays for itself. Caching code, lookups, and ambiguous prompts is how a stale or wrong answer gets served with high confidence.

## Decision

Cache only `summarize`, `rephrase`, `email_rewrite`, and `grammar`. Do not cache `code`, `lookup`, `reasoning`, or `ambiguous`.

Lookup order, stop at the first that works on the eval set:

1. Normalized exact key (lowercase, collapsed whitespace, greetings stripped), same intent.
2. Token-shingle Jaccard ≥ 0.85, same intent, stored answer younger than 7 days.
3. Embedding cosine ≥ 0.92 only if 1–2 miss obvious repeats. Do not block the demo on an embedding provider.

A hit still passes through the quality gate. If the gate fails, delete that row, then escalate. Do not serve it again.

## Consequences

- Cache stores the answer, intent, normalized prompt, original model, and original token counts. It does not store the premium baseline. The logger recomputes that.
- A hit costs ~$0 and still counts in the savings view against the always-premium baseline.
- No org-wide shared cache this week. In-process or SQLite is enough.

## Related

- [ADR 0003](0003-five-routes-cheapest-first.md)
- [ADR 0004](0004-quality-gate-escalate-once.md)
