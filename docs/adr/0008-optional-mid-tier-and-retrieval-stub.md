# ADR 0008 — Mid-tier and retrieval ship as stubs if the real backends are not available

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The diagram has a mid-tier model and a retrieval-first path. The write-up says two models are enough, and a live Jira or policy search is not available this week. Dropping the route ids would force a policy rewrite the day a third model appears. Pretending a stub is the real backend would make the demo dishonest.

## Decision

Both route ids exist in the policy table this week. Their backends may be stubs.

**Retrieval.** Ship `eval/fixtures/policies.json` with 8–15 fake tickets and policy blurbs keyed by id. A known id returns that text and skips the model. A miss calls the cheap model and sets `retrieval_miss=true`. Do not build a search stack. The interface stays `lookup(query) -> hit | miss`.

**Mid-tier.** If `MID_MODEL` is unset, serve `reasoning` and `ambiguous` with the cheap model and set `used_mid_stub=true`. The UI labels the route `cheap (mid unavailable)`. Do not silently send these to premium.

A real mid-tier response skips the quality gate. The cheap stub does not — the gate runs when `used_mid_stub=true`.

## Consequences

- Turning on a real mid model is a config flip, not a router change.
- Savings numbers must not count stub traffic as mid-tier traffic.
- A live retrieval client is a later replacement of the fixture file, behind the same interface.

## Related

- [ADR 0003](0003-five-routes-cheapest-first.md)
- [ADR 0004](0004-quality-gate-escalate-once.md)
