"""Names a source. Does not fetch, classify, or pick a model. See ADR 0012."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Policy ids such as TICKET-123 stay on the retrieval fixture. They are not Jira keys.
_NOT_JIRA = {"TICKET"}
_JIRA = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
_JIRA_URL = re.compile(r"/browse/([A-Z][A-Z0-9]+-\d+)\b", re.IGNORECASE)
# Confluence and Notion are pages, not tickets. A link selects them. A word does not.
_CONF_URL = re.compile(
    r"https?://[^\s]+/wiki/(?:spaces/[^/\s]+/)?pages/(\d+)(?:/[^\s]*)?",
    re.IGNORECASE,
)
_NOTION_URL = re.compile(r"https?://(?:www\.)?notion\.so/([^\s]+)", re.IGNORECASE)
_WORD = re.compile(r"\b(jira|confluence|notion)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ToolDecision:
    source: Optional[str]
    item_id: Optional[str]
    ambiguous: bool = False


def decide(prompt: str) -> ToolDecision:
    """Return one source, none, or an ambiguous pair. Never calls a tool."""
    hits = []
    jira = _JIRA.search(prompt)
    if jira and jira.group(1).split("-", 1)[0].upper() not in _NOT_JIRA:
        hits.append(("jira", jira.group(1).upper()))
    jira_url = _JIRA_URL.search(prompt)
    if jira_url and not any(source == "jira" for source, _ in hits):
        hits.append(("jira", jira_url.group(1).upper()))
    conf_url = _CONF_URL.search(prompt)
    if conf_url:
        hits.append(("confluence", conf_url.group(1)))
    notion_url = _NOTION_URL.search(prompt)
    if notion_url:
        hits.append(("notion", notion_url.group(1).rstrip(".,)")))
    words = {match.group(1).lower() for match in _WORD.finditer(prompt)}
    # A bare source word does not select a tool. An id does.
    if len(hits) > 1 or (len(words) > 1 and not hits):
        return ToolDecision(source=None, item_id=None, ambiguous=True)
    if len(hits) == 1:
        source, item_id = hits[0]
        return ToolDecision(source=source, item_id=item_id)
    return ToolDecision(source=None, item_id=None)
