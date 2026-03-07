import pytest

from src.domain.exceptions.azure_search_config_exception import AzureSearchConfigException
from src.infrastructure.persistence.azure_search_client import AzureSearchClient


def test_missing_env_raises(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.persistence.azure_search_client.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.delenv("AZURE_AI_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_INDEX_NAME", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_API_KEY", raising=False)

    with pytest.raises(AzureSearchConfigException):
        AzureSearchClient()


def test_chunk_to_document():
    class DummyChunk:
        def __init__(self):
            self.id = "c1"
            self.doc_name = "doc"
            self.paragraph_id = "p1"
            self.title = None
            self.target_group = []
            self.chunk_text = "ct"
            self.original_text = "ot"
            self.embedding = [0.1]
            self.has_table = True
            self.table_metadata = [{"a": 1}]

    doc = AzureSearchClient.chunk_to_document(DummyChunk())

    assert doc["chunk_id"] == "c1"
    assert doc["table_metadata"] == ["{'a': 1}"]
