"""Domain service for ingesting documents into the vector store."""
import logging
from typing import List
from pathlib import Path

from src.domain.exceptions.app_exception import AppException
from src.domain.exceptions.empty_document_exception import EmptyDocumentException
from src.domain.exceptions.ingestion_exception import IngestionException
from src.domain.models.chunk_model import Chunk
from src.domain.models.paragraph_model import Paragraph
from src.domain.ports.input.document_loader_port import DocumentLoaderPort
from src.domain.ports.input.ingest_documents_port import IngestDocumentsPort
from src.domain.ports.output.embedding_port import EmbeddingPort
from src.domain.ports.output.vector_store_port import VectorStorePort
from src.domain.services.document_chunking import SmartChunker
from src.domain.services.document_splitter import DocumentSplitter
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class DocumentIngestionService(IngestDocumentsPort):
    """Ingest documents through loading, splitting, embedding, and storing.

    :param loader: Document loader implementation.
    :param chunker: Chunking strategy implementation.
    :param embedding: Embedding provider.
    :param vector_store: Vector store implementation.
    """

    def __init__(
        self,
        loader: DocumentLoaderPort,
        chunker: SmartChunker,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort
    ):
        """Initialize the ingestion service.

        :param loader: Document loader implementation.
        :param chunker: Chunking strategy implementation.
        :param embedding: Embedding provider.
        :param vector_store: Vector store implementation.
        """
        self.loader = loader
        self.chunker = chunker
        self.embedding = embedding
        self.vector_store = vector_store
        logger.info("DocumentIngestionService initialized with loader, chunker, embedding, vector_store")

    async def ingest(self, documents_dir: str):
        """Run the ingestion pipeline for a document path.

        :param documents_dir: Path to the document or directory.
        :return: List of chunks stored in the vector store.
        :raises IngestionException: If any ingestion step fails.
        :raises EmptyDocumentException: If no content is extracted.
        """
        if not documents_dir or not documents_dir.strip():
            logger.error("Document path cannot be empty")
            raise IngestionException(message="Document path cannot be empty")

        logger.info("Starting ingestion for document path: %s", documents_dir)

        try:
            pages_content, headings = await self.loader.load(documents_dir)
            logger.info(
                "Loaded document: %d pages, %d headings",
                len(pages_content),
                len(headings),
            )

        except AppException:
            raise
        except Exception as e:
            logger.error("Failed to load document: %s", e)
            raise IngestionException(message=f"Failed to load document: {str(e)}") from e

        if not pages_content:
            logger.warning("No pages extracted from document: %s", documents_dir)
            raise EmptyDocumentException(message=f"No pages extracted from document: {documents_dir}")

        try:
            paragraphs: List[Paragraph] = DocumentSplitter.split(
                name_doc=Path(documents_dir).name,
                pages=pages_content,
                headings=headings
            )
            logger.info("Document split into %d paragraphs", len(paragraphs))

            chunks: List[Chunk] = self.chunker.chunk_paragraphs(paragraphs)
            logger.info("Paragraphs chunked into %d chunks", len(chunks))

        except AppException:
            raise
        except Exception as e:
            logger.error("Failed to split/chunk document: %s", e)
            raise IngestionException(message=f"Failed to split/chunk document: {str(e)}") from e

        if not chunks:
            logger.warning("No chunks generated from document")
            raise EmptyDocumentException(message="No chunks generated from document")

        try:
            chunks = self.embedding.generate_embeddings(chunks)
            logger.info("Embeddings generated for chunks")

            self.vector_store.store_chunks(chunks)
            logger.info("Chunks stored in vector store: %d chunks", len(chunks))

        except AppException:
            raise
        except Exception as e:
            logger.error("Failed to embed/store chunks: %s", e)
            raise IngestionException(message=f"Failed to embed/store chunks: {str(e)}") from e

        logger.info("Ingestion completed successfully for document: %s", documents_dir)
        return chunks