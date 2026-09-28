# ADR 0001 — Build a decision layer, not a chatbot or a Copilot replacement

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Hackathon pair

## Context

Almost every request is sent to an expensive model, including high-volume language chores (summaries, rephrases, email drafts). The bill grows faster than the value. A new chat app would ask people to change how they work. Replacing Copilot is a platform project, not a one-week proof.

## Decision

Build a decision layer in front of models that already exist.

- Classify the job, route it to the cheapest capable path, cache repeats, log cost against an always-premium baseline, escalate once when quality is not good enough.
- Do not build chat history, multi-turn memory, or a new assistant personality.
- Do not replace GitHub Copilot. Code stays on the premium path. Copilot stays in the IDE.
- The Friday artifact is a number: what the labeled set would have cost on premium, what it cost after routing, and whether the cheap answers were still usable.

## Consequences

- One service and one paste-box UI for the judge demo. No Slack proxy this week. A named-source fetch is allowed by [ADR 0012](0012-tool-router-names-the-source.md). That record supersedes only this sentence's Jira-proxy ban.
- A single IDE command may call `POST /route`. It must not pick a model or replace Copilot. See [ADR 0011](0011-ide-command-calls-the-router.md).
- Out of scope: SSO, per-team budgets, fine-tuning, a multi-team gateway, security hardening as the product.
- After the hackathon, if the idea holds, the same layer sits as a proxy in front of Slack, Jira, email, and docs. That is a later chapter, not this build.

## Related

- [Solution write-up](../plans/00-solution-writeup.md)
- [ADR 0007](0007-hackathon-stack.md)
