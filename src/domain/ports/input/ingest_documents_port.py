"""
Module containing the IngestDocumentsPort abstract base class.
Defines the interface (input port) for ingesting documents into the system.
"""

from abc import ABC, abstractmethod


class IngestDocumentsPort(ABC):
    """
    Abstract input port for document ingestion.
    """

    @abstractmethod
    def ingest(self, documents_dir: str) -> None:
        """
        Ingest a list of documents from the specified directory into the system.

        Args:
            documents_dir (str): Directory path containing the documents to ingest.
        """
        pass
