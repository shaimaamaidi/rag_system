"""
Module containing the AskQuestionUseCase class.
This use case handles the process of answering a question by delegating
to the RAG services.
"""

import logging

from src.infrastructure.logging.logger import setup_logger
from src.domain.ports.input.ask_question_port import AskQuestionPort
from src.domain.services.answer_question_service import AnswerQuestionService

setup_logger()
logger = logging.getLogger(__name__)


class AskQuestionUseCase(AskQuestionPort):
    """
    Use case for answering a question using the RAG services.

    This class implements the AskQuestionPort interface and delegates
    the question-answering logic to a RAGService instance.
    """

    def __init__(self, answer_question_service: AnswerQuestionService):
        """
        Initialize the use case with a RAGService instance.

        Args:
        """
        self.answer_question_service = answer_question_service
        logger.info("AskQuestionUseCase initialized with AnswerQuestionService")

    def execute(self, question: str) -> str:
        """
        Ask a question and get an answer using the RAG services.

        Args:
            question (str): The question to be answered.

        Returns:
            str: The answer returned by the RAG services.
        """
        logger.info(f"Executing question: {question}")
        answer = self.answer_question_service.execute(question)
        logger.info("Question executed successfully")
        return answer