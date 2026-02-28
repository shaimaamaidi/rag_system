"""
Module containing the DocumentIngestionService class.
This service is responsible for ingesting documents by loading, preprocessing,
chunking, generating embeddings, and storing chunks in a vector store.
"""

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
from src.domain.service.document_chunking import SmartChunker
from src.domain.service.document_splitter import DocumentSplitter




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
        """
        Initialize the ingestion service with the required components.

        Args:
            loader (LoaderPort): Component responsible for loading documents.
            chunker (ChunkerPort): Component responsible for splitting documents into chunks.
            embedding (EmbeddingPort): Component responsible for generating embeddings for chunks.
            vector_store (VectorStorePort): Component responsible for storing and retrieving chunks.
        """
        self.loader = loader
        self.chunker = chunker
        self.embedding = embedding
        self.vector_store = vector_store

    def ingest(self, documents_dir: str):
        if not documents_dir or not documents_dir.strip():
            raise IngestionException(
                message="Document path cannot be empty",
            )

        try:
            pages_content, headings = self.loader.load(documents_dir)
        except AppException:
            raise  # propage les exceptions domain déjà typées
        except Exception as e:
            raise IngestionException(
                message=f"Failed to load document: {str(e)}",
            ) from e

        if not pages_content:
            raise EmptyDocumentException(
                message=f"No pages extracted from document: {documents_dir}",
            )

        try:
            paragraphs: list[Paragraph] = DocumentSplitter.split(
                name_doc=Path(documents_dir).name,
                pages=pages_content,
                headings=headings
            )
            chunks: List[Chunk] = self.chunker.chunk_paragraphs(paragraphs)
        except AppException:
            raise
        except Exception as e:
            raise IngestionException(
                message=f"Failed to split/chunk document: {str(e)}",
            ) from e

        if not chunks:
            raise EmptyDocumentException(
                message="No chunks generated from document",
            )

        try:
            chunks = self.embedding.generate_embeddings(chunks)
            self.vector_store.store_chunks(chunks)
        except AppException:
            raise
        except Exception as e:
            raise IngestionException(
                message=f"Failed to embed/store chunks: {str(e)}",
            ) from e