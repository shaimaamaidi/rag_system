
import os
from typing import List
from dotenv import load_dotenv
from openai import AzureOpenAI

class EmbeddingsModel:
    """
    Azure OpenAI-based embedding provider for generating embeddings for text chunks.

    Implements the EmbeddingPort interface for use in RAG pipelines.
    """

    def __init__(self):
        """
        Initialize the Azure OpenAI client for embeddings.

        Raises:
            EnvironmentError: If required Azure environment variables are missing.
            RuntimeError: If initialization of the Azure client fails.
        """
        try:
            load_dotenv()
            AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
            AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
            AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
            self.AZURE_EMBEDDING_MODEL=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
            if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, self.AZURE_EMBEDDING_MODEL]):
                raise EnvironmentError(
                    "Missing one or more Azure OpenAI environment variables "
                    "(AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_EMBEDDING_MODEL)"
                )

            self.client = AzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY
            )
        except Exception as e:
            raise RuntimeError("Failed to initialize EmbeddingsModel") from e

    def generate_embeddings(self, chunks):
        """Génère les embeddings pour tous les chunks."""
        for c in chunks:
            try:
                c.embedding = self.get_embedding_vector(c.chunk_text)
            except Exception as e:
                print(f"❌ Erreur embedding pour chunk {c.id}: {e}")

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
            return embedding
        except Exception as e:
            raise RuntimeError("Failed to generate embedding") from e