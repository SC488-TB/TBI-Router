# Architecture decision records

Decisions for the one-week TBI Router. Each record is accepted unless the status line says otherwise.

Format: title, status, date, context, decision, consequences. Supersede a record by writing a new one that points at it. Do not silently edit an accepted decision.

| ADR | Title |
|---|---|
| [0001](0001-decision-layer-not-a-chatbot.md) | Build a decision layer, not a chatbot or a Copilot replacement |
| [0002](0002-rules-first-classifier.md) | Rules-first classifier, small-model fallback, no training |
| [0003](0003-five-routes-cheapest-first.md) | Five routes, cheapest capable first |
| [0004](0004-quality-gate-escalate-once.md) | Quality gate on cheap paths only, escalate once |
| [0005](0005-semantic-cache-cheap-intents.md) | Semantic cache for cheap, repeat-heavy intents only |
| [0006](0006-cost-baseline-without-premium-call.md) | Log every call; baseline cost is estimated, never a premium call |
| [0007](0007-hackathon-stack.md) | Hackathon stack: Python, FastAPI, LiteLLM or OpenRouter, one page |
| [0008](0008-optional-mid-tier-and-retrieval-stub.md) | Mid-tier and retrieval ship as stubs if the real backends are not available |
| [0009](0009-role-list-gaps.md) | Role-list gaps after the MVP: what is already built, what is still allowed, what stays rejected |
| [0010](0010-counted-margin-not-a-fitted-model.md) | Counted margin beside the rules, not a fitted model |
| [0011](0011-ide-command-calls-the-router.md) | IDE command calls the router, it does not pick a model |
| [0012](0012-tool-router-names-the-source.md) | Tool router names the source, then the model router sees the text |

Related: [implementation plan](../plans/01-implementation-plan.md), [tool router plan](../plans/05-tool-router.md), [architecture](../architecture/README.md), [tool-router diagram](../architecture/tool-router-diagram.html).
