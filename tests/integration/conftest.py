import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient


class DummyAgent:
    def ask_question_stream(self, question):
        yield "part1"
        yield "part2"


class DummyIngestUseCase:
    def __init__(self):
        self.last = None

    async def ingest(self, file_bytes, filename):
        self.last = (file_bytes, filename)


class DummyAskUseCase:
    def execute(self, question):
        return "answer"


class DummyContainer:
    def __init__(self):
        self.ingest_use_case = DummyIngestUseCase()
        self.ask_use_case = DummyAskUseCase()
        self.agent_adapter = DummyAgent()


@pytest.fixture()
def api_client(monkeypatch):
    dummy_module = types.SimpleNamespace(Container=DummyContainer)
    monkeypatch.setitem(sys.modules, "src.infrastructure.di.container", dummy_module)

    if "src.presentation.api.main" in sys.modules:
        sys.modules.pop("src.presentation.api.main")

    main = importlib.import_module("src.presentation.api.main")
    app = main.create_app()
    return TestClient(app)
