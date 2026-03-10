"""Output port for chunk relevance classification."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.models.chunk_model import Chunk


class ChunkRelevanceClassifierPort(ABC):
    """Port for classifying chunk relevance."""

    @abstractmethod
    def classify(
        self,
        question: str,
        enhanced_question: str,
        chunks: List[Chunk]
    ) -> List[Chunk]:
        """
        Classify retrieved chunks and return only relevant ones.

        :param question: Original user question
        :param enhanced_question: Reformulated search question
        :param chunks: Retrieved chunks
        :return: Filtered chunks
        """
        pass