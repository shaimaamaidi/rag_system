import pytest

from src.domain.exceptions.embedding_init_exception import EmbeddingInitException
from src.infrastructure.adapters.document_embedding.document_embedding import DocumentEmbedding


def test_embedding_missing_env(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.adapters.document_embedding.document_embedding.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", raising=False)

    with pytest.raises(EmbeddingInitException):
        DocumentEmbedding()


def test_get_embedding_vector_success(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.adapters.document_embedding.document_embedding.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "http://test")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-01-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "embed")

    class DummyEmbeddings:
        def create(self, *_args, **_kwargs):
            class _Data:
                embedding = [0.1, 0.2]
            class _Resp:
                data = [_Data()]
            return _Resp()

    class DummyClient:
        def __init__(self, **_kwargs):
            self.embeddings = DummyEmbeddings()

    monkeypatch.setattr(
        "src.infrastructure.adapters.document_embedding.document_embedding.AzureOpenAI",
        DummyClient,
    )

    emb = DocumentEmbedding()
    assert emb.get_embedding_vector("hello") == [0.1, 0.2]
