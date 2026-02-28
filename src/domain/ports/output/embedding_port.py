from abc import ABC, abstractmethod
from typing import List
from src.domain.models.chunk_model import Chunk

class EmbeddingPort(ABC):
    @abstractmethod
    def generate_embeddings(self, chunks: List[Chunk]):
        pass

    @abstractmethod
    def get_embedding_vector(self, text: str):
        pass