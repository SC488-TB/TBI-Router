"""Language-chore templates. One per cacheable intent."""

from __future__ import annotations

from app.gateway import Gateway
from app.schemas import GatewayResult

_TEMPLATES = {
    "summarize": "Summarize the following in a few sentences. Keep every number, id, and amount.\n\n{prompt}",
    "email_rewrite": "Rewrite the following as a clear email. Keep every date, amount, name, and ticket id.\n\n{prompt}",
    "rephrase": "Rephrase the following. Keep every number, email, date, and ticket id.\n\n{prompt}",
    "grammar": "Fix grammar and spelling. Do not change meaning, numbers, or names.\n\n{prompt}",
}


def run_cheap(gateway: Gateway, intent: str, prompt: str, max_tokens: int) -> GatewayResult:
    template = _TEMPLATES.get(intent, "Respond briefly.\n\n{prompt}")
    return gateway.complete(
        "cheap",
        [
            {"role": "system", "content": "You do the task. You do not refuse language chores."},
            {"role": "user", "content": template.format(prompt=prompt)},
        ],
        max_tokens=max_tokens,
    )
