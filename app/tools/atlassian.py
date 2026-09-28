"""One Atlassian read client for Jira and Confluence. Not called during classify.

Unset ATLASSIAN_API_TOKEN means no network call. The fixture path stays the demo.
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def configured() -> bool:
    return bool(os.environ.get("ATLASSIAN_API_TOKEN", "").strip())


def fetch(source: str, item_id: str) -> Optional[dict]:
    """Return {id, title, body} or None. None means the caller keeps the fixture miss."""
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    email = os.environ.get("ATLASSIAN_EMAIL", "").strip()
    site = os.environ.get("ATLASSIAN_SITE", "").strip().rstrip("/")
    if not token or not email or not site:
        return None
    if source == "jira":
        url = f"{site}/rest/api/3/issue/{quote(item_id)}?fields=summary,description"
    elif source == "confluence":
        url = f"{site}/wiki/api/v2/pages/{quote(item_id)}?body-format=storage"
    else:
        return None
    request = Request(url, headers={"Accept": "application/json"})
    # Basic auth is the Atlassian Cloud API token, not a session cookie.
    raw = f"{email}:{token}".encode()
    request.add_header("Authorization", "Basic " + base64.b64encode(raw).decode())
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return _shape(source, item_id, payload)


def _shape(source: str, item_id: str, payload: dict) -> Optional[dict]:
    if source == "jira":
        fields = payload.get("fields") or {}
        title = str(fields.get("summary") or item_id)
        body = _plain(fields.get("description"))
    else:
        title = str(payload.get("title") or item_id)
        storage = (payload.get("body") or {}).get("storage") or {}
        body = _plain(storage.get("value"))
    body = body.strip()
    if not body:
        return None
    return {"id": item_id, "title": title, "body": body}


def _plain(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = _TAG.sub(" ", value)
        return _SPACE.sub(" ", text).strip()
    if isinstance(value, dict):
        parts = [_plain(value.get("text"))]
        for child in value.get("content") or []:
            parts.append(_plain(child))
        return " ".join(part for part in parts if part)
    if isinstance(value, list):
        return " ".join(_plain(item) for item in value)
    return ""
