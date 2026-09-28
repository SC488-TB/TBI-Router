"""FastAPI surface. Routing decisions live in the orchestrator, not here."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.cost.savings import summarize
from app.factory import build_orchestrator
from app.gateway import GatewayError
from app.orchestrator import AlreadyEscalated, Orchestrator, UnknownRequest
from app.schemas import CostEvent, PromptScore, RouteRequest, RouteResponse, SavingsReport

_orchestrator: Optional[Orchestrator] = None

_UI = Path(__file__).resolve().parent / "ui"


def create_app(orchestrator: Optional[Orchestrator] = None) -> FastAPI:
    app = FastAPI(title="TBI Router", version="0.1.0")
    # Local IDE command only. Not a public API. See ADR 0011.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8766", "http://localhost:8766"],
        allow_origin_regex=r"vscode-webview://.*",
        allow_methods=["POST", "GET"],
        allow_headers=["content-type"],
    )
    app.state.orchestrator = orchestrator or build_orchestrator()
    if (_UI / "static").exists():
        app.mount("/static", StaticFiles(directory=_UI / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (_UI / "templates" / "index.html").read_text(encoding="utf-8")

    @app.post("/score", response_model=PromptScore)
    def score(body: RouteRequest) -> PromptScore:
        return app.state.orchestrator._classifier.score_prompt(body.prompt)

    @app.post("/route", response_model=RouteResponse)
    def route(body: RouteRequest) -> RouteResponse:
        return app.state.orchestrator.route(body)

    @app.post("/route/{request_id}/escalate", response_model=RouteResponse)
    def escalate(request_id: str) -> RouteResponse:
        try:
            return app.state.orchestrator.escalate(request_id)
        except UnknownRequest:
            raise HTTPException(status_code=404, detail="unknown request")
        except AlreadyEscalated as exc:
            raise HTTPException(status_code=409, detail=exc.response.model_dump())
        except GatewayError as exc:
            raise HTTPException(status_code=502, detail={"request_id": request_id, "error": str(exc)})

    @app.get("/savings", response_model=SavingsReport)
    def savings(source: Optional[str] = None) -> SavingsReport:
        rows = app.state.orchestrator._logger.list(source, limit=10_000)
        return summarize(rows)

    @app.get("/logs", response_model=List[CostEvent])
    def logs(
        source: Optional[str] = None,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> List[CostEvent]:
        return app.state.orchestrator._logger.list(source, limit)

    @app.post("/eval/replay", response_model=SavingsReport)
    def replay() -> SavingsReport:
        from app.eval.replay import replay_set

        return replay_set(app.state.orchestrator)

    return app


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator


app = create_app(get_orchestrator())
