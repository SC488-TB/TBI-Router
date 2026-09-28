# TBI Router

A decision layer in front of models we already use. It classifies the job, picks the cheapest capable route, and logs the cost. It is not a chatbot and it does not replace Copilot.

## What it does

1. A named source is resolved before classify. A Jira key or a Confluence wiki link fetches a body. A named miss returns `Document was not found.` and makes no model call. Two sources stop with `Name one source.`
2. Rules classify the job. A small model is asked only when the rules are unsure.
3. The router sends the job to one of five routes: cache, low-cost model, retrieval, mid-tier, or premium.
4. The quality gate checks low-cost answers. A fail escalates once to premium. It never escalates twice.
5. Every terminal call is logged. The page shows always-premium cost against routed cost.

A fixture hit never calls Atlassian. Policy lookups such as `PTO` stay on the local fixture. `TICKET-*` is a policy fixture, not a Jira key.

## Run

```bash
python3 -m pip install -e ".[dev,gateway]"
cp .env.example .env
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8766
```

Open http://127.0.0.1:8766.

Without a `.env`, the gateway is an offline stub. No provider is called. `.env.example` sets `TBI_GATEWAY=litellm`. A model id that still ends in `-stub` stays offline even then.

## Configure

Copy [.env.example](.env.example). Do not commit `.env`.

| Variable | Effect |
|---|---|
| `TBI_GATEWAY` | `litellm` uses a live provider. Anything else is the stub. |
| `CHEAP_MODEL` | Low-cost model. Example: `ollama/gemma3:4b`. Ollama must be running. |
| `MID_MODEL` | Optional. Unset means mid-tier is not offered. |
| `PREMIUM_MODEL` | Premium model id. Pair it with that provider's key. |
| `ATLASSIAN_SITE`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` | All three must be set or Jira and Confluence stay on fixtures. This is REST, not MCP. |

Notion has no live client. A named Notion miss stops the same way as a Jira miss.

## API

| Method | Path | What it returns |
|---|---|---|
| `POST` | `/route` | Answer, route, model, cost, cache hit, and whether the UI may offer "Try the smart model." |
| `POST` | `/route/{request_id}/escalate` | Premium answer for that request. Once only. |
| `GET` | `/savings` | Always-premium total against routed total. |
| `GET` | `/logs` | Recent cost rows. |
| `POST` | `/score` | Classifier score for a prompt. No route. |

## Test

```bash
python3 -m pytest -q
```

The labeled set checks the rules. It is not an independent score. Savings use the price list in [app/config.py](app/config.py), not a company bill.

## Layout

| Path | Owns |
|---|---|
| [app/orchestrator.py](app/orchestrator.py) | Request path, miss stop, body cap, escalation |
| [app/tools/](app/tools) | Which source a prompt names, and the Atlassian read |
| [app/classifier/](app/classifier) | Intent. Rules first. |
| [app/router/](app/router) | Which of the five routes |
| [app/routes/](app/routes) | Cache, low-cost, retrieval, mid, premium |
| [app/quality/](app/quality) | Pass or fail. Does not pick a route. |
| [app/gateway.py](app/gateway.py) | The only module that talks to a provider |
| [app/cost/](app/cost) | Log and savings. Does not pick a route. |
| [ide/](ide) | VS Code command that posts a selection to `/route` |
| [docs/](docs) | Plans, ADRs, and diagrams |

## Docs

Start at [docs/README.md](docs/README.md). If two docs disagree, the write-up wins on scope, the diagram wins on the request path, and the ADRs win on decisions.

