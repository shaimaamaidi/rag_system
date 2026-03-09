"""Domain service for answering questions using a RAG pipeline."""

import logging
from typing import List

from src.domain.exceptions.answer_generation_exception import AnswerGenerationException
from src.domain.exceptions.app_exception import AppException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.chunk_model import Chunk
from src.domain.ports.input.ask_question_port import AskQuestionPort
from src.domain.ports.output.embedding_port import EmbeddingPort
from src.domain.ports.output.vector_store_port import VectorStorePort
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class AnswerQuestionService(AskQuestionPort):
    """Answer questions by orchestrating embedding, retrieval, and generation.

    :param embedding_model: Provider for embedding vectors.
    :param vector_store: Vector store for similarity search.
    """

    def __init__(
        self,
        embedding_model: EmbeddingPort,
        vector_store: VectorStorePort,
    ):
        """Initialize the service.

        :param embedding_model: Component to generate embeddings for questions.
        :param vector_store: Component to search for relevant chunks.
        """
        self.embedding = embedding_model
        self.vector_store = vector_store
        logger.info("AnswerQuestionService initialized with embedding, vector store, and answer generator")

    def execute(self, question: str) -> str:
        """Execute the question-answering flow.

        :param question: Question text provided by the user.
        :return: Generated answer.
        :raises QuestionEmptyException: If the question is empty or whitespace.
        :raises AnswerGenerationException: If embedding, retrieval, or generation fails.
        """
        if not question or not question.strip():
            logger.warning("Empty question received")
            raise QuestionEmptyException(message="Question cannot be empty")

        try:
            question_clean = question.strip()
            logger.info("Generating embedding for question: %s", question_clean)
            question_embedding = self.embedding.get_embedding_vector(question_clean)
            logger.info("Question embedding generated successfully")
        except AppException:
            raise
        except Exception as e:
            logger.exception("Failed to embed question")
            raise AnswerGenerationException(
                message=f"Failed to embed question: {str(e)}",
            ) from e

        try:
            logger.info("Searching for relevant chunks in vector store")
            chunks = self.vector_store.search(question_clean, question_embedding, top_k=6)
            logger.info("Retrieved %d chunks from vector store", len(chunks))
        except AppException:
            raise
        except Exception as e:
            logger.exception("Failed to retrieve chunks")
            raise AnswerGenerationException(
                message=f"Failed to retrieve chunks: {str(e)}",
            ) from e

        if not chunks:
            logger.warning("No relevant chunks found for this question")
            raise AnswerGenerationException(message="No relevant chunks found for this question")

        try:
            context = AnswerQuestionService._get_context_from_chunks(chunks)
            logger.info("Generating answer from retrieved context")
            return context
        except AppException:
            raise
        except Exception as e:
            logger.exception("Failed to generate answer")
            raise AnswerGenerationException(
                message=f"Failed to generate answer: {str(e)}",
            ) from e

    @staticmethod
    def _get_context_from_chunks(chunks: List[Chunk]) -> str:
        """Assemble a context string from retrieved chunks.

        :param chunks: Retrieved chunks with metadata.
        :return: Concatenated context string for answer generation.
        """
        context_list = []
        seen_paragraphs = set()

        for chunk in chunks:
            if chunk.paragraph_id not in seen_paragraphs:
                header_parts = []
                if chunk.title:
                    header_parts.append(chunk.title)

                header = " | ".join(header_parts) if header_parts else ""

                entry = f"[{chunk.doc_name}]"
                if header:
                    entry += f" {header}"
                entry += f"\ntarget group(s): {', '.join(chunk.target_group) if chunk.target_group else 'N/A'}"
                entry += f"\n{chunk.original_text}"

                if chunk.has_table and chunk.table_metadata:
                    import json
                    entry += f"\ntables:\n{json.dumps(chunk.table_metadata, ensure_ascii=False, indent=2)}"

                context_list.append(entry)
                seen_paragraphs.add(chunk.paragraph_id)

        logger.info("Context assembled from %d chunks", len(context_list))
        return "\n\n".join(context_list)