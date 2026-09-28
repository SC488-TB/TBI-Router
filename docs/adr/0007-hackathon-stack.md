# ADR 0007 — Hackathon stack: Python, FastAPI, LiteLLM or OpenRouter, one page

- **Status:** Accepted
- **Date:** 2026-09-24

## Context

The week has to produce a replayable demo, not a platform. Picking a framework, a gateway, and a UI kit is how day 3 disappears.

## Decision

- Python service, FastAPI, one process.
- LiteLLM or OpenRouter behind a single gateway module. No other module imports a provider SDK.
- One Streamlit app or one HTML page. Paste box, answer, dollars, savings strip. No model picker for the user.
- SQLite for the cost log. In-memory escalate set is acceptable if the flag is also on the log row.
- Config holds model aliases (`cheap`, `premium`, optional `mid`, optional `embed`), prices, and gate thresholds. No scattered model-id strings.

The gateway times out at 30s and retries once on 429/5xx. If the cheap alias fails, escalate once to premium and log `gateway_failover`. If premium fails, return the error. Do not retry premium into itself.

## Consequences

- We do not build a gateway, an auth layer, or a design system.
- Swapping cheap vs premium model is a config change, not a code change.
- The UI reads `GET /savings` and `GET /logs`. It does not recompute the savings total from the table.

## Related

- [ADR 0001](0001-decision-layer-not-a-chatbot.md)
- [Implementation plan §7](../plans/01-implementation-plan.md)
- [ADR 0009](0009-role-list-gaps.md) — Ollama and Grok are model ids on this gateway, not new clients
