"""Write the 10-row quality-vs-cost note. Not part of the request path."""

from __future__ import annotations

from pathlib import Path

from app.db import connect

from app.config import load_settings
from app.eval.replay import quality_note
from app.factory import build_orchestrator
from app.gateway import StubGateway

_OUT = Path(__file__).resolve().parents[2] / "docs" / "plans" / "02-quality-vs-cost.md"


def render(rows: list[dict]) -> str:
    lines = [
        "# Quality vs cost",
        "",
        "Ten rows from a live replay of [app/eval/prompts.jsonl](../../app/eval/prompts.jsonl). Gate is the heuristic in the router, not a second model. One premium or escalated row is kept on purpose.",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python3 -m app.eval.note",
        "```",
        "",
        "| # | Prompt | Route | Gate | Cost | Always premium |",
        "|---|---|---|---|---:|---:|",
    ]
    for index, row in enumerate(rows, start=1):
        prompt = row["prompt"].replace("|", "/").replace("\n", " ")
        if len(prompt) > 90:
            prompt = prompt[:87] + "..."
        lines.append(
            f"| {index} | {prompt} | {row['route']} | {row['gate']} | "
            f"${row['cost_usd']:.4f} | ${row['baseline_cost_usd']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    conn = connect(":memory:")
    settings = load_settings()
    text = render(quality_note(build_orchestrator(settings, StubGateway(settings), conn)))
    _OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
