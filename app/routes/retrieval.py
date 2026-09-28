"""Fixture lookup. A live client replaces the file, not the interface. See ADR 0008."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.gateway import Gateway
from app.schemas import GatewayResult

_FIXTURE = Path(__file__).resolve().parents[1] / "eval" / "fixtures" / "policies.json"
_ID = re.compile(r"\b([A-Z]{2,}-\d+)\b", re.IGNORECASE)


@dataclass
class RetrievalResult:
    result: GatewayResult
    model_called: bool
    retrieval_miss: bool


class Retriever:
    def __init__(self, path: Path = _FIXTURE) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._items = payload["items"]

    def lookup(self, prompt: str) -> Optional[dict]:
        lowered = prompt.lower()
        for match in _ID.findall(prompt):
            key = match.upper()
            for item in self._items:
                if item["id"].upper() == key:
                    return item
        for item in self._items:
            if item["title"].lower() in lowered or item["id"].lower() in lowered:
                return item
        return None

    def run(self, gateway: Gateway, prompt: str, max_tokens: int) -> RetrievalResult:
        hit = self.lookup(prompt)
        if hit is not None:
            text = f"{hit['title']}: {hit['body']}"
            return RetrievalResult(
                result=GatewayResult(
                    text=text,
                    prompt_tokens=0,
                    completion_tokens=0,
                    model_id="fixture",
                    finish_reason="stop",
                ),
                model_called=False,
                retrieval_miss=False,
            )
        result = gateway.complete(
            "cheap",
            [
                {
                    "role": "system",
                    "content": "No internal document matched. Answer from the prompt only, and say you could not find a source doc.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return RetrievalResult(result=result, model_called=True, retrieval_miss=True)
