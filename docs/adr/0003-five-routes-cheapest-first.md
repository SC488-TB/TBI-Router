# ADR 0003 — Five routes, cheapest capable first

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The diagram fans one router out to five paths, ordered cheapest first. The write-up says two live models are enough and a third is optional. Collapsing the diagram to two boxes would hide the policy. Wiring five live backends would blow the week.

## Decision

The router maps an intent to exactly one of five route ids. It does not call models.

| Order | Route | Cost tier | Used for |
|---|---|---|---|
| 1 | Semantic cache | ~$0 | Near-duplicate of a cacheable intent |
| 2 | Cheap model | $ | Summarize, rephrase, grammar, email drafts |
| 3 | Retrieval first | $ | Ticket and policy lookups; model only if the lookup misses |
| 4 | Mid-tier | $$ | Reasoning and ambiguous requests, when a mid model exists |
| 5 | Premium | $$$ | Code, refactors, multi-file edits, architecture, plus escalations |

Cache is not an intent. The router marks cacheable intents; the cache module decides hit or miss, then the cheap generator runs on miss.

`force_premium` skips cache and cheap paths and sets the route to premium.

## Consequences

- Route modules do not import each other. Only the gateway talks to a provider.
- Mid-tier and retrieval may be stubs this week. See [ADR 0008](0008-optional-mid-tier-and-retrieval-stub.md). The route ids still exist so the policy table does not change when a real backend shows up.
- Ambiguous work must not be silently sent to premium. That erases the savings number the demo exists to show.

## Related

- [Architecture diagram](../architecture/tbi-router-diagram.html)
- [ADR 0005](0005-semantic-cache-cheap-intents.md)
- [ADR 0008](0008-optional-mid-tier-and-retrieval-stub.md)
