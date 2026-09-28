# ADR 0012 — Tool router names the source, then the model router sees the text

- **Status:** Accepted
- **Date:** 2026-09-25
- **Supersedes:** the "no Jira proxy this week" line in [ADR 0001](0001-decision-layer-not-a-chatbot.md), for a named-source fetch only

## Context

A prompt such as `summarize the ticket JIRA-1234` needs the ticket body before a model can summarize it. [ADR 0001](0001-decision-layer-not-a-chatbot.md) kept a Jira proxy out of the Friday demo. [ADR 0008](0008-optional-mid-tier-and-retrieval-stub.md) says a live client replaces the fixture, not the interface.

## Decision

Add a tool router in front of classify. It returns `jira`, `confluence`, `notion`, or none. It does not fetch and it does not pick a model.

- One match fetches that fixture through the lookup seam. The model router classifies the fetched text.
- No match leaves the Friday path unchanged.
- Two matches call neither source.
- A miss does not escalate. The original prompt is classified and a notice is set.
- Tokens, when a live client exists, come from the environment. The MVP reads fixture files and ignores tokens.
- An MCP wrapper is not on this path.

This record does not supersede [ADR 0008](0008-optional-mid-tier-and-retrieval-stub.md) or [ADR 0009](0009-role-list-gaps.md). A plain policy lookup still returns the fixture and skips the model.

## Consequences

- The classifier names the job, not the source. That is why the tool router stays in front of classify. Moving it after classify would pick a model route before the document exists.
- The classifier and the model router do not import a source client.
- Unset live clients do not change the paste-box savings pair.
- A comment button inside Jira is still a later client of `POST /route`, not this fetch.

## Related

- [ADR 0001](0001-decision-layer-not-a-chatbot.md)
- [ADR 0008](0008-optional-mid-tier-and-retrieval-stub.md)
- [Tool router plan](../plans/05-tool-router.md)
- [Tool router diagram](../architecture/tool-router-diagram.html)
