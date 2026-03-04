"""Output port interface for answer generation."""

from abc import ABC, abstractmethod

class AnswerGeneratorPort(ABC):
    """Interface for answer generation providers."""
    @abstractmethod
    def generate_answer(self, context: str, question: str) -> str:
        """Generate an answer for a given context and question.

        :param context: Retrieved context for the question.
        :param question: User question.
        :return: Generated answer text.
        """
        pass