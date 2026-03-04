import os
import types
import pytest

from src.domain.exceptions.azure_agent_config_exception import AzureAgentConfigException
from src.infrastructure.adapters.agent.agent_adapter import AzureAgentAdapter


def test_agent_missing_env(monkeypatch):
    for key in [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_PROJECT_ENDPOINT",
        "AZURE_AI_AGENT_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(AzureAgentConfigException):
        AzureAgentAdapter(search_tool=lambda **_k: {}, prompt_provider=object())


def test_normalize_event():
    class DummyEvent:
        event_type = "evt"
        data = {"a": 1}

    event_type, event_data = AzureAgentAdapter._normalize_event(DummyEvent())
    assert event_type == "evt"
    assert event_data == {"a": 1}

    event_type, event_data = AzureAgentAdapter._normalize_event(("evt2", {"b": 2}))
    assert event_type == "evt2"
    assert event_data == {"b": 2}
