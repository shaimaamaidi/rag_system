"""Input port interface for document ingestion."""

from abc import ABC, abstractmethod


class IngestDocumentsPort(ABC):
    """Abstract input port for document ingestion."""

    @abstractmethod
    def ingest(self, documents_dir: str) -> None:
        """Ingest documents from the specified directory.

        :param documents_dir: Directory path containing documents.
        :return: None.
        """
        pass
