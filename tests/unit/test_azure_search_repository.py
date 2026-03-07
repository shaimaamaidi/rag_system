import pytest

from src.domain.exceptions.azure_search_query_exception import AzureSearchQueryException
from src.domain.exceptions.chunk_missing_embedding_exception import ChunkMissingEmbeddingException
from src.domain.models.chunk_model import Chunk
from src.infrastructure.persistence.azure_search_repository import AzureSearchRepository


def _make_chunk(embedding):
    return Chunk(
        id="c1",
        doc_name="doc",
        paragraph_id="p1",
        title=None,
        target_group=[],
        chunk_text="text",
        original_text="text",
        has_table=False,
        table_metadata=[],
        embedding=embedding,
    )


def test_upload_chunks_missing_embedding():
    class DummyClient:
        def get_search_client(self):
            return object()

    repo = AzureSearchRepository(DummyClient())
    with pytest.raises(ChunkMissingEmbeddingException):
        repo.upload_chunks([_make_chunk(None)])


def test_upload_chunks_success():
    class DummySearchClient:
        def __init__(self):
            self.uploaded = None

        def upload_documents(self, docs):
            self.uploaded = docs
            return {"value": "ok"}

    class DummyClient:
        def __init__(self):
            self.search_client = DummySearchClient()

        def get_search_client(self):
            return self.search_client

    repo = AzureSearchRepository(DummyClient())
    result = repo.upload_chunks([_make_chunk([0.1, 0.2])])

    assert result == {"value": "ok"}
    assert len(repo.search_client.uploaded) == 1


def test_semantic_search_maps_results():
    class DummySearchClient:
        def search(self, **_kwargs):
            return [
                {
                    "chunk_id": "c1",
                    "doc_name": "doc",
                    "paragraph_id": "p1",
                    "title": "T",
                    "target_group": ["TG"],
                    "chunk_text": "ct",
                    "original_text": "ot",
                    "has_table": True,
                    "table_metadata": ["m1"],
                }
            ]

    class DummyClient:
        def get_search_client(self):
            return DummySearchClient()

    repo = AzureSearchRepository(DummyClient())
    chunks = repo.semantic_search("query", [0.1, 0.2], top_k=1)

    assert len(chunks) == 1
    assert chunks[0].doc_name == "doc"


def test_semantic_search_failure():
    class DummySearchClient:
        def search(self, **_kwargs):
            raise RuntimeError("boom")

    class DummyClient:
        def get_search_client(self):
            return DummySearchClient()

    repo = AzureSearchRepository(DummyClient())
    with pytest.raises(AzureSearchQueryException):
        repo.semantic_search("query", [0.1])
