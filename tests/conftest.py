import pytest
from fastapi.testclient import TestClient

from app.classifier.service import Classifier
from app.config import Settings, load_settings
from app.cost.logger import CostLogger
from app.db import connect
from app.factory import build_orchestrator
from app.gateway import StubGateway
from app.main import create_app
from app.router.service import Router
from app.routes.cache import SemanticCache
from app.routes.retrieval import Retriever


@pytest.fixture
def settings() -> Settings:
    base = load_settings()
    return Settings(
        cheap_model="cheap-test",
        premium_model="premium-test",
        mid_model=None,
        embed_model=None,
        prices=base.prices,
        database_path=":memory:",
    )


@pytest.fixture
def gateway(settings):
    return StubGateway(settings)


@pytest.fixture
def conn():
    return connect(":memory:")


@pytest.fixture
def orchestrator(settings, gateway, conn):
    return build_orchestrator(settings=settings, gateway=gateway, conn=conn)


@pytest.fixture
def client(orchestrator):
    return TestClient(create_app(orchestrator))
