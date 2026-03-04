"""Input port for asking a question and receiving an answer."""

from abc import ABC, abstractmethod


class AskQuestionPort(ABC):
    """Abstract interface for question answering."""

    @abstractmethod
    def execute(self, question: str) -> str:
        """Return an answer for the provided question.

        :param question: Question to answer.
        :return: Answer text.
        """
        pass
