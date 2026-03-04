"""
Module containing the AzureAISearchAdapter class.
Responsible for exposing Azure Search functionality to the domain layer
and providing methods for storing and retrieving document chunks.
"""

from typing import List

from src.domain.ports.output.vector_store_port import VectorStorePort
from src.infrastructure.persistence.azure_search_client import AzureSearchClient
from src.infrastructure.persistence.azure_search_repository import AzureSearchRepository
from src.domain.services.document_chunking import Chunk


class AzureAISearchAdapter(VectorStorePort):
    """
    Adapter for interacting with Azure Cognitive Search.

    This class acts as a bridge between the domain layer and Azure Search,
    providing methods to store document chunks and perform semantic searches.
    """

    def __init__(self, client: AzureSearchClient):
        """
        Initialize the AzureAISearchAdapter.

        Args:
            client (AzureSearchClient): An Azure Search client used to interact with the search services.

        Notes:
            - Initializes an internal repository that handles low-level Azure Search operations.
        """
        self.repository = AzureSearchRepository(client=client)

    def store_chunks(self, chunks: List[Chunk]):
        """
        Upload a list of chunks to Azure Search for later retrieval.

        Args:
            chunks (List[Chunk]): List of Chunk objects to store in the search index.

        Notes:
            - Each chunk should contain embedding vectors and metadata required for semantic search.
            - Logs an info message after successful upload.
        """
        self.repository.upload_chunks(chunks)

    def search(self, query_embedding: List[float], top_k: int = 14) -> List[Chunk]:
        """
        Perform a semantic search for the most relevant chunks.

        Args:
            query_embedding (List[float]): Embedding vector representing the user's query.
            top_k (int, optional): Number of top results to return. Defaults to 7.

        Returns:
            List[Chunk]: A list of the top_k most relevant Chunk objects according to semantic similarity.

        Notes:
            - Relies on the repository to execute the search using Azure Cognitive Search.
            - The returned chunks include their content, metadata, and embeddings if stored.
        """
        result= self.repository.semantic_search(query_embedding, top_k)

        logger.info("Semantic search returned %d chunks (top_k=%d)", len(results), top_k)

        return result