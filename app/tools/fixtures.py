"""Fixture readers. A live client replaces the file, not this return shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_DIR = Path(__file__).resolve().parents[1] / "eval" / "fixtures"
_FILES = {
    "jira": _DIR / "jira.json",
    "confluence": _DIR / "confluence.json",
    "notion": _DIR / "notion.json",
}


def read_fixture(source: str, item_id: str) -> Optional[dict]:
    path = _FILES.get(source)
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    wanted = item_id.upper()
    for item in payload.get("items", []):
        if str(item.get("id", "")).upper() == wanted:
            return item
    return None
