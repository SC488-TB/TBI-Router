# TBI Router docs

Decision layer in front of existing models. Not a chatbot. Not a Copilot replacement.

Classify the job, route it to the cheapest capable model, cache the repeats, measure the savings, and escalate only when quality is not good enough.

## Read in this order

| Doc | What it is |
|---|---|
| [Solution write-up](plans/00-solution-writeup.md) | Problem, one-week bet, what "done" means on Friday |
| [Implementation plan](plans/01-implementation-plan.md) | Module-by-module build plan for the person writing the code |
| [Counted score plan](plans/04-counted-score-implementation.md) | Lite ML add-on: score the prompt, show it, do not train |
| [Architecture](architecture/README.md) | Model path, tool router, current request flow, and module map |
| [ADRs](adr/README.md) | Decisions already made. Do not relitigate them during the week |

## Conflict rule

If two docs disagree, the write-up wins on **scope**, the diagram wins on the **request path**, and the ADRs win on **decisions**. The implementation plan follows all three.

## Status

Hackathon MVP. Nothing here is a production platform spec.
