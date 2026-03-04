import importlib
import sys
import types

from fastapi import FastAPI


def test_create_app_uses_container(monkeypatch):
    class DummyContainer:
        pass

    dummy_module = types.SimpleNamespace(Container=DummyContainer)
    monkeypatch.setitem(sys.modules, "src.infrastructure.di.container", dummy_module)

    if "src.presentation.api.main" in sys.modules:
        sys.modules.pop("src.presentation.api.main")

    main = importlib.import_module("src.presentation.api.main")
    app = main.create_app()

    assert isinstance(app, FastAPI)
    assert isinstance(app.state.container, DummyContainer)
