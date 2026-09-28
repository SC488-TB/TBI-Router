# ADR 0009 — Role-list gaps after the MVP

- **Status:** Accepted
- **Date:** 2026-09-25

## Context

A role list arrived after the week plan shipped: train a classifier, connect Ollama and a Grok/Cursor API, build the live demo, write the pitch, and leave a path for non-ML contributors. [ADR 0002](0002-rules-first-classifier.md) and [ADR 0007](0007-hackathon-stack.md) already reject parts of that list. The running service already covers the rest. Treating the role list as new requirements would reopen settled decisions.

This record does not replace 0002 or 0007. It records what is still allowed.

## Decision

Validate the role list against the repo. Do not build a line just because a role owns it.

| Role line | Status | Evidence | Follow-on |
|---|---|---|---|
| Hand-labeled test set | Built | [app/eval/prompts.jsonl](../../app/eval/prompts.jsonl), `POST /eval/replay` | Add a row only when a real prompt misses a rule |
| Train a routing classifier | Rejected | No train script. Rules, then one label call | [ADR 0002](0002-rules-first-classifier.md) stands |
| Quality-vs-cost evaluation | Partial | Cost is `GET /savings`. Quality is the heuristic gate, not a scored model | One 10-row note. No second quality model |
| Router API | Built | [app/main.py](../../app/main.py) | None |
| Ollama client | Rejected | Stub or LiteLLM only | A local model id may be set on `CHEAP_MODEL`. No new client |
| Grok or Cursor API client | Rejected | Same gateway. No vendor SDK in `app/` | A premium model id may be set on `PREMIUM_MODEL`. No Cursor integration |
| Live demo: route, savings, latency | Built | [app/ui/](../../app/ui/) and `latency_ms` | Optional one-line route mix under the strip, from `GET /savings` |
| Demo story | Partial | Chips and the strip | Ten-line click script. Not a page in the app |
| Real-work prompts | Partial | Slack, email, docs, and IDE-shaped rows | Extend the jsonl. Do not relabel to force 100% |
| Pitch | Not a module | README is run instructions | Speaker notes stay outside the service |
| Non-ML contributor path | Partial | Stub runs with no key and no Apple Silicon requirement | README lists editable files: prompts, chips, copy. Model ids stay in env |

Allowed remaining work, in order:

1. Route mix line under the savings pair, if the strip is still hard to read. Source is `by_route` and `escalated` on `GET /savings`. No new endpoint. No chart library.
2. A 10-row quality-vs-cost note from a live replay: prompt, route, gate pass/fail, cost, baseline. Keep one premium or escalated row. Do not delete it to improve the number.
3. Extra labeled prompts only after a real miss. Fix the rule or the label. Accuracy floor stays about 90% of the set.
4. A ten-line demo script and a five-line contributor boundary in the README.

Optional, not required: one live model behind the existing gateway. Stub stays the default.

```bash
export TBI_GATEWAY=litellm
export CHEAP_MODEL=ollama/llama3.2
export PREMIUM_MODEL=openrouter/x-ai/grok-3
```

No `OLLAMA_HOST`, Grok SDK, or Cursor key in config. If the cheap alias fails, the existing one-time failover to premium applies. Unset `TBI_GATEWAY` and the stub returns.

## Consequences

- A training pipeline, an Ollama module, or a Grok/Cursor client is a decision change, not a gap. Write a new ADR that supersedes 0002 or 0007 before starting that work.
- The 40-row file remains an accuracy fixture, not training data.
- Closing this record means the dashboard still matches `GET /savings`, the 10-row note matches the log, and `app/` still has no train script and no second provider import.
- Apple Silicon is irrelevant to the stub demo.

## Related

- [ADR 0001](0001-decision-layer-not-a-chatbot.md)
- [ADR 0002](0002-rules-first-classifier.md)
- [ADR 0007](0007-hackathon-stack.md)
- [Implementation plan §8](../plans/01-implementation-plan.md)
