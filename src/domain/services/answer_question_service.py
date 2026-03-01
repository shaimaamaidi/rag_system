"""
Module containing the RAGService class.
Provides a services to answer questions using a Retrieval-Augmented Generation (RAG) pipeline.
"""
from typing import List

from src.domain.exceptions.answer_generation_exception import AnswerGenerationException
from src.domain.exceptions.app_exception import AppException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.chunk_model import Chunk
from src.domain.ports.input.ask_question_port import AskQuestionPort
from src.domain.ports.output.embedding_port import EmbeddingPort
from src.domain.ports.output.answer_generator_port import AnswerGeneratorPort
from src.domain.ports.output.vector_store_port import VectorStorePort


class AnswerQuestionService(AskQuestionPort):
    """
    Business services to answer questions using a Retrieval-Augmented Generation (RAG) approach.

    This services uses:
    - An embedding model to convert questions into vector representations.
    - A vector store to retrieve relevant chunks of information.
    - An answer generator to produce answers based on the retrieved context.
    """

    def __init__(
        self,
        embedding_model: EmbeddingPort,
        vector_store: VectorStorePort,
        answer_generator: AnswerGeneratorPort,

    ):
        """
        Initialize the RAG services with the required components.

        Args:
            embedding_model (EmbeddingPort): Component to generate embeddings for questions.
            vector_store (VectorStorePort): Component to search for relevant chunks.
            answer_generator (AnswerGeneratorPort): Component to generate answers from retrieved context.
        """
        self.embedding = embedding_model
        self.vector_store = vector_store
        self.answer_generator = answer_generator

    def execute(self, question: str) -> str:
        if not question or not question.strip():
            raise QuestionEmptyException(
                message="Question cannot be empty",
            )

        try:
            question_clean = question.strip()
            question_embedding = self.embedding.get_embedding_vector(question_clean)
        except AppException:
            raise
        except Exception as e:
            raise AnswerGenerationException(
                message=f"Failed to embed question: {str(e)}",
            ) from e

        try:
            chunks = self.vector_store.search(question_embedding.vector, top_k=7)
        except AppException:
            raise
        except Exception as e:
            raise AnswerGenerationException(
                message=f"Failed to retrieve chunks: {str(e)}",
            ) from e

        if not chunks:
            raise AnswerGenerationException(
                message="No relevant chunks found for this question",
            )

        try:
            context = AnswerQuestionService._get_context_from_chunks(chunks)
            return self.answer_generator.generate_answer(context, question_clean)
        except AppException:
            raise
        except Exception as e:
            raise AnswerGenerationException(
                message=f"Failed to generate answer: {str(e)}",
            ) from e

    @staticmethod
    def _get_context_from_chunks(chunks: List[Chunk]) -> str:
        context_list = []
        seen_paragraphs = set()

        for chunk in chunks:
            if chunk.paragraph_id not in seen_paragraphs:
                header_parts = []
                if chunk.title:
                    header_parts.append(chunk.title)
                if chunk.sub_title:
                    header_parts.append(chunk.sub_title)

                header = " | ".join(header_parts) if header_parts else ""

                entry = f"[{chunk.doc_name}]"
                if header:
                    entry += f" {header}"
                entry += f"\ntarget group(s): {chunk.target_group or 'N/A'}"
                entry += f"\n{chunk.original_text}"

                context_list.append(entry)
                seen_paragraphs.add(chunk.paragraph_id)

        return "\n\n".join(context_list)
