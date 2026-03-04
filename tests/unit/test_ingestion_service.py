import asyncio

import pytest

from src.domain.exceptions.app_exception import AppException
from src.domain.exceptions.empty_document_exception import EmptyDocumentException
from src.domain.exceptions.ingestion_exception import IngestionException
from src.domain.models.chunk_model import Chunk
from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService


def _make_service(loader, chunker, embedding, vector_store):
    return DocumentIngestionService(
        loader=loader,
        chunker=chunker,
        embedding=embedding,
        vector_store=vector_store,
    )


def test_ingest_empty_path():
    service = _make_service(None, None, None, None)
    with pytest.raises(IngestionException):
        asyncio.run(service.ingest("  "))


def test_ingest_loader_app_exception_propagates():
    class FakeLoader:
        async def load(self, _):
            raise AppException("boom")

    service = _make_service(FakeLoader(), None, None, None)
    with pytest.raises(AppException):
        asyncio.run(service.ingest("file.pdf"))


def test_ingest_empty_pages_raises():
    class FakeLoader:
        async def load(self, _):
            return [], []

    class DummyChunker:
        def chunk_paragraphs(self, _):
            return []

    service = _make_service(FakeLoader(), DummyChunker(), None, None)
    with pytest.raises(EmptyDocumentException):
        asyncio.run(service.ingest("file.pdf"))


def test_ingest_empty_chunks_raises():
    class FakeLoader:
        async def load(self, _):
            return [PageContent(1, "text", "", "hello", False, [])], []

    class DummyChunker:
        def chunk_paragraphs(self, _):
            return []

    service = _make_service(FakeLoader(), DummyChunker(), None, None)
    with pytest.raises(EmptyDocumentException):
        asyncio.run(service.ingest("file.pdf"))


def test_ingest_embedding_failure_wrapped():
    class FakeLoader:
        async def load(self, _):
            return [PageContent(1, "text", "", "hello", False, [])], []

    class DummyChunker:
        def chunk_paragraphs(self, _):
            return [Chunk(
                id="c1",
                doc_name="doc",
                paragraph_id="p1",
                title=None,
                sub_title=None,
                target_group="",
                chunk_text="hello",
                original_text="hello",
                has_table=False,
                table_metadata=[],
                embedding=None,
            )]

    class DummyEmbedding:
        def generate_embeddings(self, _):
            raise RuntimeError("fail")

    class DummyStore:
        def store_chunks(self, _):
            raise AssertionError("should not be called")

    service = _make_service(FakeLoader(), DummyChunker(), DummyEmbedding(), DummyStore())
    with pytest.raises(IngestionException):
        asyncio.run(service.ingest("file.pdf"))


def test_ingest_success_flow():
    class FakeLoader:
        async def load(self, _):
            return [PageContent(1, "text", "", "hello", False, [])], [
                SectionHeading("H1", 1, 0.1, 0.1)
            ]

    class DummyChunker:
        def chunk_paragraphs(self, _):
            return [Chunk(
                id="c1",
                doc_name="doc",
                paragraph_id="p1",
                title=None,
                sub_title=None,
                target_group="",
                chunk_text="hello",
                original_text="hello",
                has_table=False,
                table_metadata=[],
                embedding=None,
            )]

    class DummyEmbedding:
        def generate_embeddings(self, chunks):
            for c in chunks:
                c.embedding = [0.1, 0.2]
            return chunks

    class DummyStore:
        def __init__(self):
            self.stored = []

        def store_chunks(self, chunks):
            self.stored = list(chunks)

    store = DummyStore()
    service = _make_service(FakeLoader(), DummyChunker(), DummyEmbedding(), store)

    chunks = asyncio.run(service.ingest("file.pdf"))

    assert len(chunks) == 1
    assert store.stored[0].embedding == [0.1, 0.2]
