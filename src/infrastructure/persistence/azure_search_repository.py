"""Repository for Azure Cognitive Search operations."""
import logging
from typing import List

from azure.search.documents._generated.models import VectorizedQuery

from src.domain.exceptions.azure_search_query_exception import AzureSearchQueryException
from src.domain.exceptions.azure_search_upload_exception import AzureSearchUploadException
from src.domain.exceptions.chunk_missing_embedding_exception import ChunkMissingEmbeddingException
from src.domain.models.chunk_model import Chunk
from src.infrastructure.logging.logger import setup_logger
from src.infrastructure.persistence.azure_search_client import AzureSearchClient

setup_logger()
logger = logging.getLogger(__name__)


class AzureSearchRepository:
    """Repository for Azure Cognitive Search operations.

    :param client: Configured AzureSearchClient instance.
    """

    def __init__(self, client: AzureSearchClient):
        """Initialize the repository.

        :param client: Configured AzureSearchClient instance.
        """
        self.client = client
        self.search_client = self.client.get_search_client()
        logger.info("AzureSearchRepository initialized.")

    def upload_chunks(self, chunks: List[Chunk]):
        """Upload chunks to the Azure Search index.

        :param chunks: Chunk list with embeddings populated.
        :return: Result from Azure Search SDK.
        :raises ChunkMissingEmbeddingException: If a chunk has no embedding.
        :raises AzureSearchUploadException: If upload fails.
        """
        documents = []
        for chunk in chunks:
            if chunk.embedding is None:
                logger.error("Chunk '%s' has no embedding.", chunk.id)
                raise ChunkMissingEmbeddingException(
                    message=f"Chunk '{chunk.id}' has no embedding. Generate embeddings before uploading.",
                )
            documents.append(AzureSearchClient.chunk_to_document(chunk))
        try:
            result = self.search_client.upload_documents(documents)
            logger.info("Uploaded %d chunks to Azure Search index.", len(chunks))
            return result
        except Exception as e:
            logger.exception("Failed to upload chunks to Azure Search.")
            raise AzureSearchUploadException(
                message=f"Failed to upload chunks to Azure Search: {str(e)}",
            ) from e

    def semantic_search(
        self,
        query,
        vector_query: List[float],
        top_k: int = 5,
    ) -> List[Chunk]:
        """Perform a vector-based semantic search.

        :param query:
        :param vector_query: Query embedding vector.
        :param top_k: Maximum number of results to return.
        :return: Matching chunks with populated fields.
        :raises AzureSearchQueryException: If the search operation fails.
        """
        try:

            logger.info("Performing semantic search ...")
            vector_query_obj = VectorizedQuery(
                vector=vector_query,
                k_nearest_neighbors=top_k,
                fields="embedding",
            )

            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query_obj],
                select=[
                    "chunk_id",
                    "doc_name",
                    "paragraph_id",
                    "title",
                    "target_group",
                    "chunk_text",
                    "original_text",
                    "has_table",
                    "table_metadata",
                ],
                top=top_k,
                query_type="semantic",
                semantic_configuration_name="semantic_config",
            )

            chunks: List[Chunk] = []
            for r in results:
                chunk = Chunk(
                    id=r["chunk_id"],
                    doc_name=r["doc_name"],
                    paragraph_id=r["paragraph_id"],
                    title=r.get("title"),
                    target_group=r.get("target_group"),
                    chunk_text=r["chunk_text"],
                    original_text=r["original_text"],
                    has_table=r.get("has_table", False),
                    table_metadata=r.get("table_metadata") or [],
                    embedding=None,
                )
                chunks.append(chunk)
            logger.info("Semantic search returned %d results", len(chunks))
            return chunks

        except Exception as e:
            logger.exception("Vector search failed in Azure Cognitive Search.")
            raise AzureSearchQueryException(
                message=f"Vector search failed in Azure Cognitive Search: {str(e)}",
            ) from e

    def get_distinct_doc_names(self) -> List[str]:
        """Fetch distinct doc_name values using Azure Search facets."""

        results = self.search_client.search(
            search_text="*",
            select=["doc_name"],
        )

        doc_names = set()

        for r in results:
            if r.get("doc_name"):
                doc_names.add(r["doc_name"])

        return list(doc_names)

    from typing import List
    from src.domain.services.document_chunking import Chunk

    def get_chunks_by_doc_name(self) -> List[Chunk]:
        """Return all chunks belonging to a specific document."""

        results = self.search_client.search(
            search_text="*",
        )

        chunks = []

        for r in results:
            if r.get("doc_name") == "نظام_العمل.pdf":
                chunk = Chunk(
                    id=r.get("chunk_id"),
                    doc_name=r.get("doc_name"),
                    paragraph_id=r.get("paragraph_id"),
                    title=r.get("title"),
                    target_group=r.get("target_group"),
                    chunk_text=r.get("chunk_text"),
                    original_text=r.get("original_text"),
                    has_table=r.get("has_table"),
                    table_metadata=r.get("table_metadata", []),
                    embedding=None
                )
                chunks.append(chunk)

        return chunks