"""Azure OpenAI chunk relevance classification adapter."""

import logging
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from typing import List

from src.domain.exceptions.azure_answer_exception import AzureOpenAIAnswerException
from src.domain.exceptions.azure_config_exception import AzureOpenAIConfigException
from src.domain.models.chunk_classification_model import ChunkClassificationResponse
from src.domain.models.chunk_model import Chunk
from src.domain.ports.output.chunk_relevance_classifier_port import ChunkRelevanceClassifierPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


RELEVANT_LEVELS = {"VERY HIGH", "HIGH"}
MEDIUM_LEVEL = "MEDIUM"

class ChunkRelevanceClassifier(ChunkRelevanceClassifierPort):
    """Classify retrieved chunks by relevance using Azure OpenAI."""

    def __init__(self, prompt_provider: PromptProviderPort):
        """Initialize the classifier from environment configuration.

        :raises AzureOpenAIConfigException: If required env vars are missing.
        """
        load_dotenv()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([self.endpoint, self.api_key, self.api_version, self.embedding_model, self.model]):
            logger.error("Missing Azure OpenAI environment variables")
            raise AzureOpenAIConfigException(
                "One or more Azure OpenAI environment variables are missing"
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        self.prompt_provider = prompt_provider
        logger.info("ChunkRelevanceClassifier initialized successfully")

    def classify(self, question: str, enhanced_question: str, chunks: List[Chunk]) -> List[Chunk]:
        """Classify chunks and return only VERY HIGH and HIGH relevance ones.

        :param question: Original user question string.
        :param enhanced_question: Reformulated question optimized for search.
        :param chunks: List of Chunk objects returned by search_tool.
        :return: Filtered list of Chunk objects rated VERY HIGH or HIGH.
        :raises AzureOpenAIAnswerException: If the classification call fails.
        """
        logger.info("Classifying %d chunks for relevance", len(chunks))

        # Build a lightweight representation for the LLM (no embeddings)
        chunks_payload = [
            {
                "chunk_index": i + 1,
                "doc_name": chunk.doc_name,
                "title": chunk.title,
                "target_group": chunk.target_group if chunk.target_group else [],
                "original_text": chunk.original_text,
            }
            for i, chunk in enumerate(chunks)
        ]


        try:
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=self.prompt_provider.get_system_prompt("classifier")),
                ChatCompletionUserMessageParam(role="user", content=self.prompt_provider.get_user_classifier_prompt(question, enhanced_question, chunks_payload)),
            ]

            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=ChunkClassificationResponse,
                temperature=0,
            )

            parsed: ChunkClassificationResponse = response.choices[0].message.parsed
            logger.info("Classification received for %d chunks", len(parsed.results))

            # Build a lookup: chunk_index (1-based) → classification
            classification_map: dict[int, str] = {
                result.chunk_index: result.classification
                for result in parsed.results
            }

            # Filter and return only VERY HIGH and HIGH chunks
            relevant_chunks: List[Chunk] = [
                chunk
                for i, chunk in enumerate(chunks)
                if classification_map.get(i + 1) in RELEVANT_LEVELS
            ]

            if not relevant_chunks:
                logger.info("No VERY HIGH/HIGH chunks found — falling back to MEDIUM")
                relevant_chunks = [
                    chunk
                    for i, chunk in enumerate(chunks)
                    if classification_map.get(i + 1) == MEDIUM_LEVEL
                ]

                if not relevant_chunks:
                    logger.info("No MEDIUM chunks found — returning all %d chunks as fallback", len(chunks))
                    relevant_chunks = chunks

            logger.info(
                "%d / %d chunks kept after classification (VERY HIGH + HIGH)",
                len(relevant_chunks),
                len(chunks),
            )
            return relevant_chunks

        except Exception as e:
            logger.exception("Failed to classify chunks with Azure OpenAI")
            raise AzureOpenAIAnswerException(
                f"Failed to classify chunks with Azure OpenAI: {str(e)}"
            )