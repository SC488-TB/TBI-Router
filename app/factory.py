"""Wires the process. Tests pass their own gateway and database."""

from __future__ import annotations

from app.classifier.service import Classifier
from app.config import Settings, load_settings
from app.cost.logger import CostLogger
from app.db import connect
from app.gateway import Gateway, build_gateway
from app.orchestrator import Orchestrator
from app.router.service import Router
from app.routes.cache import SemanticCache
from app.routes.retrieval import Retriever


def build_orchestrator(
    settings: Settings | None = None,
    gateway: Gateway | None = None,
    conn=None,
) -> Orchestrator:
    settings = settings or load_settings()
    gateway = gateway or build_gateway(settings)
    conn = conn or connect(settings.database_path)
    return Orchestrator(
        settings=settings,
        gateway=gateway,
        classifier=Classifier(settings, gateway),
        router=Router(),
        cache=SemanticCache(conn, settings),
        retriever=Retriever(),
        logger=CostLogger(conn),
    )
