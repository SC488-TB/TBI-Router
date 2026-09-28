# Tool router — implementation plan

**Status: shipped.** The fixture path is in `app/tools/`. Live clients are still later.

**Goal.** When a prompt names one source, fetch that document, then let the existing model router route the document text.

The first fixture is `app/eval/fixtures/jira.json`. It is read by `app/tools/fixtures.read_fixture` before classify. It does not plug into `Retriever.lookup()`. That seam still owns `policies.json` (`PTO`, `TICKET-123`). This plan does not break [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) or [ADR 0009](../adr/0009-role-list-gaps.md).

Diagram: [tool-router-diagram.html](../architecture/tool-router-diagram.html). Decision: [ADR 0012](../adr/0012-tool-router-names-the-source.md).

## 1. Goal and non-goals

### In scope

| Item | Ship |
|---|---|
| Tool router | Names `jira`, `confluence`, `notion`, or none. Does not fetch. |
| Three fixture files | One known id per source. No live API. |
| Lookup seam | `read_fixture(source, id)` reads the named fixture. `Retriever.lookup()` is not this seam. |
| Second classify | The fetched text, not the user's sentence, is what the model router sees. |
| New ADR | Supersedes only the "no Jira proxy this week" line in [ADR 0001](../adr/0001-decision-layer-not-a-chatbot.md). |
| Unset clients | Paste box works as it does today. |

### Out of scope

- An MCP gateway on the request path. A wrapper may sit in front of the clients later, for other agents. It is not called during classify.
- A live Jira, Confluence, or Notion call. That replaces the fixture behind the same interface.
- A new model, a provider client, or a second escalate.
- A chatbot inside Jira. A comment action that posts to `POST /route` is a later client, not this plan.
- Hosting MCP servers inside the router process.
- Changing the savings pair, the five route ids, or the quality-gate rules.

## 2. Two routers

| | Tool router | Model router |
|---|---|---|
| Question | Which system has this? | How hard is this text? |
| Input | The user prompt | The fetched document, or the original prompt if no tool matched |
| Output | `jira`, `confluence`, `notion`, or none | `cache`, `cheap`, `retrieval`, `mid`, or `premium` |
| Must not call | A model, an MCP server, or more than one source | Jira, Confluence, Notion, or an MCP server |

The classifier stays rules-first. It does not import a source client.

## 3. Request path

1. Prompt arrives at `POST /route`.
2. Tool router reads the prompt. It returns one source or none.
3. None: classify the original prompt. Existing path. No tool call.
4. One source: the matching client fetches that id. MVP client reads a fixture file.
5. Classify the fetched text. Do not classify the user's sentence again for the model pick.
6. Existing model router picks one of the five routes.
7. Quality gate runs on cheap paths only, including a cheap stub of mid. Premium and a real mid response skip it, as today.
8. Fail escalates once. The answer is shown. Never escalate twice.
9. Log the row. `source` is `jira`, `confluence`, or `notion` when a tool ran. The savings strip still reads `source=ui` first.

`summarize these notes` stops at step 3.

`summarize the ticket JIRA-1234` reaches step 4, then the ticket body is what step 5 classifies.

A plain lookup such as `What's our PTO policy?` does not name a new source. It still hits `policies.json` and skips the model. [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) stays in force for that path.

## 4. Source catalog

| Source | Selects it | Fixture now | Live call later |
|---|---|---|---|
| Jira | `JIRA-1234` or `PROJ-123`. Phrase `jira` plus an id. | `app/eval/fixtures/jira.json` key `JIRA-1234` | `GET /rest/api/3/issue/JIRA-1234`. Summary and description only. |
| Confluence | A page link, `/wiki/.../pages/{id}`. Not a ticket id. The word `confluence` alone does not select it. | `app/eval/fixtures/confluence.json` key `1290207249` | `GET /wiki/api/v2/pages/{id}?body-format=storage`. Title and body text only. |
| Notion | A `notion.so/{slug}` link. Not a ticket id. The word `notion` alone does not select it. | `app/eval/fixtures/notion.json` key `Launch-notes-7` | Retrieve that page's blocks. Plain text only. |

One id, one source. `TICKET-123` stays on the old fixture. Do not move those rows into `jira.json`.

## 5. Modules

### Tool router

- **Owns:** source name, or none. The matched id.
- **Must not own:** fetch, classify, model pick, tokens.
- **Calls:** nothing. Returns a decision.
- **MVP:** three id patterns and three phrases. First match wins only if the other two do not also match.
- **Later:** a fourth source is a new pattern, not a new router.

### Jira, Confluence, and Notion clients

- **Owns:** one fetch by id. Fixture file in the MVP.
- **Must not own:** routing, a model call, another source.
- **Calls:** the fixture reader now. The live HTTP call later.
- **MVP:** return `{id, title, body}` or a miss.
- **Later:** swap the reader. Same return shape. Token comes from the environment, not from code.

### Fixture files

- **Owns:** one known document per source.
- **Must not own:** routing rules.
- **Calls:** nothing.
- **MVP:** `jira.json` ships first. The other two files may be empty until that source is demoed.
- **Later:** delete a fixture only after the live call returns the same shape.

### Token store

- **Owns:** nothing in the repo.
- **Must not own:** a token checked into git, `.env` committed, or a token in the paste box.
- **Calls:** process environment when a live client is turned on. Names: `JIRA_API_TOKEN`, `CONFLUENCE_API_TOKEN`, `NOTION_API_TOKEN`.
- **MVP:** unset. Fixtures do not read them.
- **Later:** a secret store. Not a new service this plan.

### Lookup seam

- **Owns:** one fixture read by source and id. `app/tools/fixtures.read_fixture`.
- **Must not own:** the tool decision, or `policies.json`. `Retriever.lookup()` still owns PTO and `TICKET-123`.
- **Calls:** the JSON file for the named source. Not `Retriever.lookup()`.
- **MVP:** `jira.json`, `confluence.json`, `notion.json`. Friday paste box is unchanged when the tool router returns none.
- **Later:** a live client replaces the file behind this function. [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) is not superseded.

### MCP wrapper

- **Owns:** a tool list for some other agent, if that agent appears.
- **Must not own:** the request path, classify, or the model router.
- **Calls:** the same three clients. Not the router process in reverse.
- **MVP:** do not build it.
- **Later:** one wrapper process. The router does not start it.

### ADR 0012

- **Owns:** the decision to add a tool router. Written as [ADR 0012](../adr/0012-tool-router-names-the-source.md).
- **Must not own:** a repeal of [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) or [ADR 0009](../adr/0009-role-list-gaps.md).
- **Calls:** none.
- **MVP:** write it before the first fixture is wired. Supersede only the "no Jira proxy this week" sentence in [ADR 0001](../adr/0001-decision-layer-not-a-chatbot.md).
- **Later:** a live client does not need another ADR if the interface stays `lookup()`.

## 6. Failure rules

| Case | Do |
|---|---|
| Unknown source | No tool call. Classify the original prompt. |
| Two sources match | Do not call either. Return a notice: name one source. |
| Source down, or fixture miss | No model call for the fetch. Classify the original prompt and set a notice that the document was not found. Do not escalate for a miss. |
| Empty document | Same as a miss. Do not send an empty body to a model. |
| Cheap answer fails the gate | Escalate once, as today. |
| Second failure | Show the premium answer. Never escalate twice. |
| Two tools | Never. One match, or none. |

## 7. Done criteria

- `summarize the ticket JIRA-1234` reads `jira.json` and summarizes that body. It does not return the raw fixture.
- A Confluence wiki link whose page id is `1290207249` reads `confluence.json`. `CONF-42` is not an id.
- A `notion.so/Launch-notes-7` link reads `notion.json`. `NOTION-7` is not an id.
- `summarize these notes` does not open any of those files.
- A fixture body that contains a function is classified from that body and takes the premium route. The same sentence with a short status note takes the low-cost route.
- The paste box still shows always premium $X vs routed $Y first. Unset tool clients do not change that pair.
- [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) still describes the PTO fixture path. [ADR 0009](../adr/0009-role-list-gaps.md) still rejects a second provider client.
