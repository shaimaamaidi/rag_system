"""Domain service for answering questions using a RAG pipeline."""

import logging
from typing import List

from src.domain.exceptions.answer_generation_exception import AnswerGenerationException
from src.domain.exceptions.app_exception import AppException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.chunk_model import Chunk
from src.domain.ports.input.ask_question_port import AskQuestionPort
from src.domain.ports.output.chunk_relevance_classifier_port import ChunkRelevanceClassifierPort
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
        chunk_classifier: ChunkRelevanceClassifierPort
    ):
        """Initialize the service.

        :param embedding_model: Component to generate embeddings for questions.
        :param vector_store: Component to search for relevant chunks.
        :param chunk_classifier: Component to classify chunk relevance.
        """
        self.embedding = embedding_model
        self.vector_store = vector_store
        self.chunk_classifier = chunk_classifier
        logger.info("AnswerQuestionService initialized with embedding, vector store, and answer generator")

    def execute(self, question: str, enhancement_question: str) -> str:
        """Execute the question-answering flow.

        :param enhancement_question:
        :param question: Question text provided by the user.
        :return: Generated answer.
        :raises QuestionEmptyException: If the question is empty or whitespace.
        :raises AnswerGenerationException: If embedding, retrieval, or generation fails.
        """
        if not question or not question.strip():
            logger.warning("Empty question received")
            raise QuestionEmptyException(message="Question cannot be empty")

        enhancement_question_clean = enhancement_question.strip()
        question_clean = question.strip()

        try:
            logger.info("Generating embedding for question: %s", enhancement_question_clean)
            question_embedding = self.embedding.get_embedding_vector(enhancement_question_clean)
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
            chunks = self.vector_store.search(enhancement_question_clean, question_embedding, top_k=5)
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
            logger.info("Classifying chunks by relevance")
            logger.info(self._get_context_from_chunks(chunks))
            chunks_retrieved = self.chunk_classifier.classify(question_clean, enhancement_question_clean, chunks)
            logger.info("Classification done: %d relevant chunks kept", len(chunks_retrieved))
        except AppException:
            raise
        except Exception as e:
            logger.exception("Failed to classify chunks")
            raise AnswerGenerationException(message=f"Failed to classify chunks: {str(e)}") from e

        if not chunks_retrieved:
            logger.warning("No chunks rated VERY HIGH or HIGH after classification")
            raise AnswerGenerationException(message="No relevant chunks found for this question")

        try:
            context = AnswerQuestionService._get_context_from_chunks(chunks_retrieved)
            logger.info("Generating answer from retrieved context")
            logger.info("Answer generated successfully")
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
        chunk_number = 0

        for chunk in chunks:
            if chunk.paragraph_id not in seen_paragraphs:
                chunk_number += 1
                header_parts = []
                if chunk.title:
                    header_parts.append(chunk.title)

                header = " | ".join(header_parts) if header_parts else ""

                entry = f"### CHUNK {chunk_number}\n"
                entry += f"[{chunk.doc_name}]"
                if header:
                    entry += f" {header}"
                entry += f"\ntarget group(s): {', '.join(chunk.target_group) if chunk.target_group else 'N/A'}"
                entry += f"\n{chunk.original_text}"

                if chunk.has_table and chunk.table_metadata:
                    import json
                    entry += f"\ntables:\n{json.dumps(chunk.table_metadata, ensure_ascii=False, indent=2)}"

                context_list.append(entry)
                seen_paragraphs.add(chunk.paragraph_id)

        total = len(context_list)
        header_line = f"TOTAL CHUNKS: {total}\n\n"
        logger.info("Context assembled from %d chunks", total)
        return header_line + "\n\n".join(context_list)