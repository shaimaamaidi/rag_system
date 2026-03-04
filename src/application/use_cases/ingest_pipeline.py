"""
Module containing the IngestDocumentsUseCase class.
This use case handles the ingestion of documents by delegating
the process to the DocumentIngestionService.
"""

import logging

from src.infrastructure.adapters.config.logger import setup_logger
from src.domain.ports.input.ingest_documents_port import IngestDocumentsPort
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService

setup_logger()
logger = logging.getLogger(__name__)


class IngestDocumentUseCase(IngestDocumentsPort):
    """
    Use case for ingesting documents using the DocumentIngestionService.

    This class implements the IngestDocumentsPort interface and
    delegates the document ingestion logic to a DocumentIngestionService instance.
    """

    def __init__(self, ingestion_service: DocumentIngestionService):
        """
        Initialize the use case with a DocumentIngestionService instance.

        Args:
            ingestion_service (DocumentIngestionService): Service responsible for document ingestion.
        """
        self.ingestion_service = ingestion_service
        logger.info("IngestDocumentUseCase initialized with DocumentIngestionService")

    async def ingest(self, documents_dir: str) -> None:
        """
        Ingest documents from the specified directory.

        Args:
            documents_dir (str): Path to the directory containing documents to ingest.

        Returns:
            None
        """
        logger.info(f"Starting document ingestion from directory: {documents_dir}")
        await self.ingestion_service.ingest(documents_dir)
        logger.info(f"Document ingestion completed for directory: {documents_dir}")