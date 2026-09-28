# ADR 0011 — IDE command calls the router, it does not pick a model

- **Status:** Accepted
- **Date:** 2026-09-25
- **Supersedes:** the "no IDE plugin this week" line in [ADR 0001](0001-decision-layer-not-a-chatbot.md), for this command only

## Context

[ADR 0001](0001-decision-layer-not-a-chatbot.md) kept an IDE plugin out of the Friday demo so the build would not become a Copilot replacement. The write-up already says the later chapter is the same decision layer in front of real tools. A paste box is not how someone uses the router while editing.

## Decision

Ship one VS Code command, `TBI: Route selection`. It posts the selected text to `POST /route` with `source=ide` and shows the answer, route, and cost.

- The extension does not choose a model, call a provider, or replace Copilot.
- Code still routes to premium because the router says so, not because the extension says so.
- The answer opens in a TBI panel beside the editor. That panel is not the Copilot chat and has no model picker.
- `@tbi` in chat reads only the message addressed to it. It cannot read the current Copilot or Cursor turn, and it does not call `request.model`.
- No second escalate button.
- The paste-box page stays the judge demo. The command is a client of the same API.

## Consequences

- CORS allows the local page and a `vscode-webview://` origin. It does not open the API to every site. The command itself runs in the extension host and posts to `127.0.0.1`.
- A Jira or Slack proxy is still out. This record does not authorize it.
- If the command starts calling a provider SDK, that breaks [ADR 0007](0007-hackathon-stack.md).

## Related

- [ADR 0001](0001-decision-layer-not-a-chatbot.md)
- [ADR 0007](0007-hackathon-stack.md)
- [ide/README.md](../../ide/README.md)
