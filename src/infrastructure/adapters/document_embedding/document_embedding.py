import os
from typing import List
from dotenv import load_dotenv
from openai import AzureOpenAI
from src.infrastructure.adapters.config.logger import setup_logger
import logging

from src.domain.exceptions.azure_config_exception import AzureOpenAIConfigException
from src.domain.exceptions.embedding_generation_exception import EmbeddingGenerationException
from src.domain.exceptions.embedding_init_exception import EmbeddingInitException
from src.domain.ports.output.embedding_port import EmbeddingPort

setup_logger()
logger = logging.getLogger(__name__)


class DocumentEmbedding(EmbeddingPort):
    """
    Azure OpenAI-based embedding provider for generating embeddings for text chunks.
    Implements the EmbeddingPort interface for use in RAG pipelines.
    """

    def __init__(self):
        logger.info("Initializing Azure OpenAI embedding client")
        try:
            load_dotenv()
            AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
            AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
            AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
            self.AZURE_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

            if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, self.AZURE_EMBEDDING_MODEL]):
                logger.error("Missing one or more Azure OpenAI environment variables")
                raise AzureOpenAIConfigException(
                    "Missing one or more Azure OpenAI environment variables "
                    "(AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_EMBEDDING_MODEL)"
                )

            self.client = AzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY
            )
            logger.info("Azure OpenAI embedding client initialized successfully")

        except Exception as e:
            logger.exception("Failed to initialize Azure OpenAI embedding client")
            raise EmbeddingInitException("Failed to initialize EmbeddingsModel") from e

    def generate_embeddings(self, chunks):
        """Génère les embeddings pour tous les chunks."""
        logger.info("Starting embedding generation for chunks")
        for c in chunks:
            try:
                c.embedding = self.get_embedding_vector(c.chunk_text)
            except Exception as e:
                logger.exception(f"Failed to generate embedding for chunk {c.id}")
                raise EmbeddingGenerationException(f"Failed to generate embedding for chunk {c.id}") from e
        logger.info("Embedding generation completed for all chunks")
        return chunks

    def get_embedding_vector(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a given text using Azure OpenAI.

        Args:
            text (str): Text to embed.

        Returns:
            List[float]: Embedding vector.

        Raises:
            RuntimeError: If embedding generation fails.
        """
        try:
            response = self.client.embeddings.create(input=text, model=self.AZURE_EMBEDDING_MODEL)
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of length {len(embedding)}")
            return embedding
        except Exception as e:
            logger.exception("Failed to generate embedding vector")
            raise RuntimeError("Failed to generate embedding") from e