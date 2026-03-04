"""
Module containing the IngestDocumentsUseCase class.
This use case handles the ingestion of documents by delegating
the process to the DocumentIngestionService.
"""

from src.domain.ports.input.ingest_documents_port import IngestDocumentsPort
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService


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

    async def ingest(self, documents_dir: str) -> None:
        """
        Ingest documents from the specified directory.

        Args:
            documents_dir (str): Path to the directory containing documents to ingest.

        Returns:
            None
        """
        await self.ingestion_service.ingest(documents_dir)
