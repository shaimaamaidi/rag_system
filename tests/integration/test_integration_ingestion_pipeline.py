import asyncio

from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading
from src.domain.services.document_chunking import SmartChunker
from src.domain.services.document_splitter import DocumentSplitter
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService


def test_ingestion_pipeline_integration():
    class FakeLoader:
        async def load(self, _):
            pages = [
                PageContent(1, "text", "", "Heading A\nL2\nL3\nL4\nL5", False, []),
            ]
            headings = [SectionHeading("Heading A", 1, 0.1, 0.1)]
            return pages, headings

    class DummyEmbedding:
        def generate_embeddings(self, chunks):
            for c in chunks:
                c.embedding = [0.1]
            return chunks

    class DummyStore:
        def __init__(self):
            self.stored = None

        def store_chunks(self, chunks):
            self.stored = list(chunks)

    class RealChunker(SmartChunker):
        pass

    class RealSplitter(DocumentSplitter):
        pass

    store = DummyStore()
    service = DocumentIngestionService(
        loader=FakeLoader(),
        chunker=RealChunker(max_chunk=200, overlap=0),
        embedding=DummyEmbedding(),
        vector_store=store,
    )

    chunks = asyncio.run(service.ingest("doc.pdf"))

    assert chunks
    assert store.stored
    assert store.stored[0].embedding == [0.1]
