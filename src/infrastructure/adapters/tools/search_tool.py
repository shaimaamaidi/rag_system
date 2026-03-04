"""Factory for creating a RAG search tool callable."""
import logging

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def create_search_tool(use_case: AskQuestionUseCase):
    """Create a search tool callable backed by the ask use case.

    :param use_case: Use case responsible for answering questions.
    :return: Callable that accepts a question and returns an answer.
    """

    def search_tool(question: str) -> str:
        """Answer a question using the RAG pipeline.

        :param question: Question to answer.
        :return: Answer generated from retrieved documents.
        """
        logger.info("RAG tool received question: %s", question)

        answer = use_case.execute(question)

        logger.info("RAG tool generated answer (length=%d)", len(answer))

        return answer
    return search_tool
