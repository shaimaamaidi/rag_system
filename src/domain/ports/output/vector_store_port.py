"""Output port interface for vector store operations."""

from abc import ABC, abstractmethod
from typing import List
from src.domain.services.document_chunking import Chunk

class VectorStorePort(ABC):
    """Interface for storing and querying chunk embeddings."""

    @abstractmethod
    def store_chunks(self, chunks: List[Chunk]) -> None:
        """Store chunks in the vector store.

        :param chunks: Chunk list to store.
        :return: None.
        """
        pass

    @abstractmethod
    def search(self,query: str, query_embedding: List[float], top_k: int = 6) -> List[Chunk]:
        """Search for similar chunks by embedding.

        :param query:
        :param query_embedding: Query embedding vector.
        :param top_k: Maximum number of results to return.
        :return: Matching chunks.
        """
        pass