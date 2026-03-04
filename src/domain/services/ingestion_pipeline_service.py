"""
Module containing the DocumentIngestionService class.
This service is responsible for ingesting documents by loading, preprocessing,
chunking, generating embeddings, and storing chunks in a vector store.
"""
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
    """
    Service responsible for ingesting documents through the full pipeline:
    1. Load documents from a source.
    2. Preprocess/clean documents.
    3. Split documents into semantic chunks.
    4. Generate embeddings for each chunk.
    5. Store chunks in a vector store for retrieval.
    """

    def __init__(
        self,
        loader: DocumentLoaderPort,
        chunker: SmartChunker,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort
    ):
        self.loader = loader
        self.chunker = chunker
        self.embedding = embedding
        self.vector_store = vector_store
        logger.info("DocumentIngestionService initialized with loader, chunker, embedding, vector_store")

    async def ingest(self, documents_dir: str):
        if not documents_dir or not documents_dir.strip():
            logger.error("Document path cannot be empty")
            raise IngestionException(message="Document path cannot be empty")

        logger.info(f"Starting ingestion for document path: {documents_dir}")

        try:
            pages_content, headings = await self.loader.load(documents_dir)
            logger.info(f"Loaded document: {len(pages_content)} pages, {len(headings)} headings")

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to load document: {e}")
            raise IngestionException(message=f"Failed to load document: {str(e)}") from e

        if not pages_content:
            logger.warning(f"No pages extracted from document: {documents_dir}")
            raise EmptyDocumentException(message=f"No pages extracted from document: {documents_dir}")

        try:
            paragraphs: List[Paragraph] = DocumentSplitter.split(
                name_doc=Path(documents_dir).name,
                pages=pages_content,
                headings=headings
            )
            logger.info(f"Document split into {len(paragraphs)} paragraphs")

            chunks: List[Chunk] = self.chunker.chunk_paragraphs(paragraphs)
            logger.info(f"Paragraphs chunked into {len(chunks)} chunks")

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to split/chunk document: {e}")
            raise IngestionException(message=f"Failed to split/chunk document: {str(e)}") from e

        if not chunks:
            logger.warning("No chunks generated from document")
            raise EmptyDocumentException(message="No chunks generated from document")

        try:
            chunks = self.embedding.generate_embeddings(chunks)
            logger.info("Embeddings generated for chunks")

            self.vector_store.store_chunks(chunks)
            logger.info(f"Chunks stored in vector store: {len(chunks)} chunks")

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to embed/store chunks: {e}")
            raise IngestionException(message=f"Failed to embed/store chunks: {str(e)}") from e

        logger.info(f"Ingestion completed successfully for document: {documents_dir}")
        return chunks