from abc import ABC, abstractmethod
from typing import List
from src.domain.services.document_chunking import Chunk

class VectorStorePort(ABC):

    @abstractmethod
    def store_chunks(self, chunks: List[Chunk]) -> None:
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 14) -> List[Chunk]:
        pass