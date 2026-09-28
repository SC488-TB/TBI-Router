# Named-source miss — fix plan

Hand this to the engineer who patches the tool path. Not a platform team. No service code in this document.

## 1. The bug

A named source with no fixture and no token still classifies the URL, so a model writes a summary of a link and the log looks like a fetch.

`Summarize the https://tailored-prod.atlassian.net/browse/RFW-6529` logged `source=ui`, first route `cheap`, then one escalate for `quality_fail:meaning`. The answer came from `xai/grok-4.20-non-reasoning`. `jira.json` has no `RFW-6529`. That summary was not loaded from Jira.

## 2. Named id, no fixture, no token

1. Tool router names the source and the id. It does not fetch.
2. `read_fixture` misses. `fetch_atlassian` returns `None` because `ATLASSIAN_SITE`, `ATLASSIAN_EMAIL`, and `ATLASSIAN_API_TOKEN` are unset.
3. Stop. Do not classify the URL. Do not call the gateway. Do not run the quality gate.
4. Return the existing response shape. No new route id.
   - `notice`: `Document was not found.`
   - `answer`: the same sentence. Not a model summary.
   - `model`: `none`
   - `route`: `retrieval`
   - `intent`: `lookup`
   - `escalated`: false
   - `can_escalate`: false
   - `cost_usd`: 0
   - `cache_hit`: false
5. Log `source` as the request source (`ui` or `ide`). Do not write `jira`, `confluence`, or `notion`. Those values mean a body was fetched.

`RFW-6529` must not be a model summary of a URL. The test that proves it is `test_jira_url_miss_does_not_call_a_model`.

## 3. Named id, three ATLASSIAN_* values set

1. Fixture first. `JIRA-1234` and the wiki page `1290207249` never call Atlassian.
2. Fixture miss and the three values set: one read.
   - Jira: `GET {ATLASSIAN_SITE}/rest/api/3/issue/{key}?fields=summary,description`
   - Confluence: `GET {ATLASSIAN_SITE}/wiki/api/v2/pages/{id}?body-format=storage`
3. A body comes back. Classify that body, not the URL. The existing model router picks one of the five routes. A function body is `code` / premium. Other text is `summarize`.
4. Log `source=jira` or `source=confluence` only after that body exists.
5. HTTP error, timeout, or an empty body: same as section 2. One try. No second read. No model call.

Notion has no Atlassian call. A Notion miss stays on section 2.

## 4. What stays on fixtures

| Prompt | Read | Model |
|---|---|---|
| wiki link `.../pages/1290207249` | `confluence.json` | Existing summarize path |
| `JIRA-1234` | `jira.json` | Cheap summarize |
| `JIRA-9999` | `jira.json` | Premium, because the body is code |
| `notion.so/Launch-notes-7` | `notion.json` | Existing summarize path |
| `What's our PTO policy?` | `policies.json` through `Retriever.lookup()` | None. `model=fixture` |

Do not move PTO or `TICKET-123` into `jira.json`. [ADR 0008](../adr/0008-optional-mid-tier-and-retrieval-stub.md) stays.

## 5. Tests

| Test | Assert |
|---|---|
| `test_jira_url_miss_does_not_call_a_model` | `browse/RFW-6529`, no token. `notice` set, `model=none`, `escalated` false, gateway calls unchanged, answer is not a generated summary, logged source is not `jira` |
| `test_confluence_wiki_url_miss_does_not_call_a_model` | `/wiki/.../pages/1290207249`, no token. Same miss shape. Logged source is not `confluence` |
| `test_confluence_and_notion_fixtures_are_summarized` | The wiki link and the Notion link still summarize their fixtures. `CONF-42` is not an id |
| `test_two_sources_call_neither_and_a_miss_does_not_escalate` | Two ids still return `Name one source.` and call neither tool |
| `test_pto_lookup_still_skips_the_model` | PTO still returns `model=fixture` and does not call the gateway |

No live Atlassian call in the suite. The token path is covered by a stub of `fetch_atlassian` that returns one body, then one test that the classifier sees that body and not the URL.

## 6. Out of scope

- An MCP call inside the router. The Atlassian REST client stays behind `fetch_atlassian`.
- A second provider client. [ADR 0009](../adr/0009-role-list-gaps.md) stays.
- A second escalate. A miss never reaches the gate, so it cannot escalate.
- A new route id. `retrieval` plus `model=none` is the miss response.
- A Jira comment action, a chatbot inside Jira, or a rewrite of the model-path diagram.

## Done

`browse/RFW-6529` with no fixture and no token returns `Document was not found.`, calls no model, and does not escalate. `test_jira_url_miss_does_not_call_a_model` proves it. The Confluence wiki link, the Notion link, `JIRA-1234`, and PTO still read their fixtures. `CONF-42` and `NOTION-7` are not ids.
