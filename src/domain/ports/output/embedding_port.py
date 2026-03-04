"""Output port interface for embedding generation."""

from abc import ABC, abstractmethod
from typing import List
from src.domain.models.chunk_model import Chunk

class EmbeddingPort(ABC):
    """Interface for embedding generation providers."""
    @abstractmethod
    def generate_embeddings(self, chunks: List[Chunk]):
        """Generate embeddings for a list of chunks.

        :param chunks: Chunk list to embed.
        :return: Updated chunk list with embeddings.
        """
        pass

    @abstractmethod
    def get_embedding_vector(self, text: str):
        """Generate an embedding vector for text.

        :param text: Input text to embed.
        :return: Embedding vector.
        """
        pass