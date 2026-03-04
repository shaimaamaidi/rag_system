"""
Module containing the factory for creating the RAG tool.
Provides a tool that uses an AskQuestionUseCase to answer related questions
using Retrieval-Augmented Generation (RAG).
"""
import logging

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def create_search_tool(use_case: AskQuestionUseCase):
    """
    Factory function to create a RAG tool with an injected use case.

    This tool wraps the AskQuestionUseCase and exposes a callable
    that returns answers for related questions using RAG.

    Args:
        use_case (AskQuestionUseCase): The use case responsible for answering questions.

    Returns:
        Callable[[str], str]: A function that takes a question string and
                              returns an answer based on documents.
    """

    def search_tool(question: str) -> str:
        """
        Answer a related question using RAG (Retrieval-Augmented Generation).

        The tool delegates the answer generation to the provided
        AskQuestionUseCase.

        Args:
            question (str): The related question to answer.

        Returns:
            str: The answer generated based on documents.
        """
        logger.info("RAG tool received question: %s", question)

        answer = use_case.execute(question)

        logger.info("RAG tool generated answer (length=%d)", len(answer))

        return answer
    return search_tool
