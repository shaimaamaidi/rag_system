"""
Module containing the factory for creating the RAG tool.
Provides a tool that uses an AskQuestionUseCase to answer CV-related questions
using Retrieval-Augmented Generation (RAG).
"""
from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase


def create_search_tool(use_case: AskQuestionUseCase):
    """
    Factory function to create a RAG tool with an injected use case.

    This tool wraps the AskQuestionUseCase and exposes a callable
    that returns answers for CV-related questions using RAG.

    Args:
        use_case (AskQuestionUseCase): The use case responsible for answering questions.

    Returns:
        Callable[[str], str]: A function that takes a question string and
                              returns an answer based on CV documents.
    """

    def search_tool(question: str) -> str:
        """
        Answer a CV-related question using RAG (Retrieval-Augmented Generation).

        The tool delegates the answer generation to the provided
        AskQuestionUseCase.

        Args:
            question (str): The CV-related question to answer.

        Returns:
            str: The answer generated based on CV documents.
        """
        return use_case.execute(question)

    return search_tool
