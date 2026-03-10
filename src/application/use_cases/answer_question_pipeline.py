"""Application use case for answering questions via the RAG pipeline."""

import logging

from src.infrastructure.logging.logger import setup_logger
from src.domain.ports.input.ask_question_port import AskQuestionPort
from src.domain.services.answer_question_service import AnswerQuestionService

setup_logger()
logger = logging.getLogger(__name__)


class AskQuestionUseCase(AskQuestionPort):
    """Orchestrate question answering through the domain service.

    :param answer_question_service: Service that executes the RAG pipeline.
    """

    def __init__(self, answer_question_service: AnswerQuestionService):
        """Initialize the use case.

        :param answer_question_service: Service that answers questions.
        """
        self.answer_question_service = answer_question_service
        logger.info("AskQuestionUseCase initialized with AnswerQuestionService")

    def execute(self, question: str, enhancement_question: str) -> str:
        """Execute the question-answering workflow.

        :param enhancement_question:
        :param question: Question text provided by the caller.
        :return: Generated answer text.
        """
        logger.info("Executing question: %s", question)
        answer = self.answer_question_service.execute(question, enhancement_question)
        logger.info("Question executed successfully")
        return answer