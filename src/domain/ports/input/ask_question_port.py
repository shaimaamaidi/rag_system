"""
Module containing the AskQuestionPort abstract base class.
Defines the interface for asking a question and receiving an answer.
"""

from abc import ABC, abstractmethod


class AskQuestionPort(ABC):
    """
    Abstract interface for asking a question and receiving an answer.
    """

    @abstractmethod
    def execute(self, question: str) -> str:
        """
        Return an answer to the provided question.

        Args:
            question (str): The question to be answered.

        Returns:
            str: The answer to the question.
        """
        pass
