# ADR 0004 — Quality gate on cheap paths only, escalate once

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

People will route around the system if a bad cheap answer is shown with no way up. They will also route around it if every cheap answer is second-guessed by a frontier model — that spends the money the router is supposed to save. Escalating more than once, or hopping cheap → mid → premium, hides the miss and inflates cost.

## Decision

Run a deterministic quality gate on cheap-path answers only: semantic cache, cheap model, and retrieval-first model text. Mid-tier and premium skip the gate. A cheap stub standing in for mid-tier does not skip the gate.

Checks, first failure wins: not empty, not truncated, not a refusal, not absurdly short, and — for summaries, rephrases, and email rewrites — meaning preserved. Meaning is a token-overlap and entity check (numbers, ids, emails, dates, money). It is not another model call.

- Pass → show the cheap answer. The UI may still offer "Try the smart model".
- Fail → escalate once to premium, then show that answer even if it is imperfect. Never run the gate on the premium answer. Never escalate twice.
- User override joins the same premium path. If this request already escalated, return the existing premium answer. Do not call premium again.
- A direct retrieval fixture hit checks non-empty only. Meaning-preserved does not apply.

## Consequences

- The escalate flag is set before the premium call starts, so a timeout cannot double-fire.
- Gate thresholds live in config, not in the check functions. Day 6 may move them if the eval set shows false fails.
- One honest miss stays in the demo. Do not delete it to make the savings number prettier.
- A second model inside the gate is a rejected alternative for this week.

## Related

- [Implementation plan §5](../plans/01-implementation-plan.md)
- [ADR 0006](0006-cost-baseline-without-premium-call.md)
