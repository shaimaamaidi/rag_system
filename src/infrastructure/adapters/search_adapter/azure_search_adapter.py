"""Azure Search adapter exposing vector store operations."""
import logging
from typing import List

from src.domain.ports.output.vector_store_port import VectorStorePort
from src.infrastructure.logging.logger import setup_logger
from src.infrastructure.persistence.azure_search_client import AzureSearchClient
from src.infrastructure.persistence.azure_search_repository import AzureSearchRepository
from src.domain.services.document_chunking import Chunk

setup_logger()
logger = logging.getLogger(__name__)


class AzureAISearchAdapter(VectorStorePort):
    """Adapter for Azure Cognitive Search operations.

    :param client: Azure Search client wrapper.
    """

    def __init__(self, client: AzureSearchClient):
        """Initialize the adapter.

        :param client: Azure Search client wrapper.
        """
        self.repository = AzureSearchRepository(client=client)

    def store_chunks(self, chunks: List[Chunk]):
        """Store chunks in Azure Search.

        :param chunks: List of chunks to upload.
        :return: None.
        """
        self.repository.upload_chunks(chunks)

    def search(self,query: str,  query_embedding: List[float], top_k: int = 7) -> List[Chunk]:
        """Search for the most relevant chunks.

        :param query:
        :param query_embedding: Query embedding vector.
        :param top_k: Number of results to return.
        :return: List of relevant chunks.
        """
        result= self.repository.semantic_search(query, query_embedding, top_k)

        logger.info("Semantic search returned %d chunks (top_k=%d)", len(result), top_k)

        return result