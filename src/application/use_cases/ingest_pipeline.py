"""Application use case for ingesting documents into the RAG pipeline."""

import logging

from src.infrastructure.logging.logger import setup_logger
from src.domain.ports.input.ingest_documents_port import IngestDocumentsPort
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService

setup_logger()
logger = logging.getLogger(__name__)


class IngestDocumentUseCase(IngestDocumentsPort):
    """Orchestrate document ingestion through the domain service.

    :param ingestion_service: Service that performs ingestion steps.
    """

    def __init__(self, ingestion_service: DocumentIngestionService):
        """Initialize the use case.

        :param ingestion_service: Service responsible for document ingestion.
        """
        self.ingestion_service = ingestion_service
        logger.info("IngestDocumentUseCase initialized with DocumentIngestionService")

    async def ingest(self, documents_dir: str) -> None:
        """Ingest documents from a directory.

        :param documents_dir: Path to the directory containing documents.
        :return: None.
        """
        logger.info("Starting document ingestion from directory: %s", documents_dir)
        await self.ingestion_service.ingest(documents_dir)
        logger.info("Document ingestion completed for directory: %s", documents_dir)