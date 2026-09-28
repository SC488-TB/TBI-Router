# ADR 0002 — Rules-first classifier, small-model fallback, no training

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The router cannot pick a model until it knows the job. A trained classifier needs data and time we do not have. A model-only classifier spends money and latency on every request, including the obvious ones ("summarize this", "refactor this").

## Decision

Classify with rules and keywords first. Call a small model only when the rules are unsure (no match, or two rules of equal priority). Do not train a model this week.

- Closed intent set: `code`, `lookup`, `summarize`, `email_rewrite`, `rephrase`, `grammar`, `reasoning`, `ambiguous`.
- First match wins. `code` outranks a soft word like "summarize" when the prompt is actually a coding job.
- The fallback must return one label from that set, temperature 0. Unknown label or fallback failure becomes `ambiguous`.
- The classifier does not pick a vendor model id and does not call a generation model.

## Consequences

- Day 2 is classifier accuracy against the hand-labeled set. If obvious cases miss, fix rules and labels before adding features.
- New intents require a catalog change, a route-table change, and new labeled rows. Do not let the fallback invent labels.
- Very short prompts with no rule hit skip the fallback call and land on `ambiguous`.

## Related

- [Implementation plan §3.2 and §4](../plans/01-implementation-plan.md)
- [ADR 0003](0003-five-routes-cheapest-first.md)
- [ADR 0009](0009-role-list-gaps.md) — the later role list does not reopen training
- [ADR 0010](0010-counted-margin-not-a-fitted-model.md) — a counted margin may run when rules miss. It is not a trained classifier
