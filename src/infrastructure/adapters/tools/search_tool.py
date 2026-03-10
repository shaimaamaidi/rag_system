"""RAG search tool implementation."""
import logging

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.domain.ports.output.search_tool_port import SearchToolPort
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class RAGSearchTool(SearchToolPort):
    """Search tool backed by the RAG ask use case."""

    def __init__(self, use_case: AskQuestionUseCase) -> None:
        """Initialize with the ask use case.

        :param use_case: Use case responsible for answering questions.
        """
        self.use_case = use_case

    def __call__(self, question: str, enhancement_question: str) -> str:
        """Execute the search tool.

        :param question: Question to answer.
        :param enhancement_question: Enhanced question used for retrieval.
        :return: Answer generated from retrieved documents.
        """
        logger.info("RAG tool received question: %s", question)
        context = self.use_case.execute(question, enhancement_question)
        logger.info("RAG tool generated context (length=%d)", len(context))
        return context