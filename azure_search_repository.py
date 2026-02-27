"""
Module: AzureSearchRepository

This module contains the `AzureSearchRepository` class, which acts as a repository
for managing CRUD operations and semantic searches in Azure Cognitive Search.

Responsibilities:
    - Upload Chunk objects (from SmartChunker) to the Azure Search index.
    - Perform vector-based semantic search to retrieve relevant chunks.
    - Handle optional filters for search queries.

Chunk schema (aligned with SmartChunker output):
    id              → chunk_id        (key)
    doc_name        → doc_name
    paragraph_id    → paragraph_id
    title           → title
    sub_title       → sub_title
    chunk_text      → chunk_text      (searchable + semantic)
    original_text   → original_text
    embedding       → embedding       (vector HNSW)
    has_table       → has_table       (bool, filterable)
    table_metadata  → table_metadata  (List[str], searchable)
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional

from azure.search.documents._generated.models import VectorizedQuery

from azure_search_client import AzureSearchClient


@dataclass
class Chunk:
    id: str
    doc_name: str
    paragraph_id: str
    title: Optional[str]
    sub_title: Optional[str]
    chunk_text: str
    original_text: str
    has_table: bool = False
    table_metadata: List[Any] = field(default_factory=list)
    embedding: Optional[List[float]] = field(default=None)


# ──────────────────────────────────────────────
# Repository
# ──────────────────────────────────────────────

class AzureSearchRepository:
    """
    Repository for interacting with Azure Cognitive Search.

    Responsibilities:
        - Upload Chunk objects produced by SmartChunker to the search index.
        - Perform vector-based semantic search to find the most relevant chunks.
        - Handle optional OData filters for search queries.
    """

    def __init__(self, client: AzureSearchClient):
        """
        Initialize the repository.

        Args:
            client (AzureSearchClient): Configured AzureSearchClient instance.
        """
        self.client = client
        self.search_client = self.client.get_search_client()

    # ── upload ────────────────────────────────

    def upload_chunks(self, chunks: List[Chunk]):
        """
        Upload a list of Chunk objects to Azure Cognitive Search.

        Args:
            chunks (List[Chunk]): Chunks produced by SmartChunker.
                                  Each chunk must have a non-None `embedding`
                                  before being uploaded.

        Returns:
            list: Result of the upload operation from Azure Search SDK.

        Raises:
            ValueError: If any chunk is missing its embedding vector.
        """
        documents = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(
                    f"Chunk '{chunk.id}' has no embedding. "
                    "Generate embeddings before uploading."
                )
            documents.append(AzureSearchClient.chunk_to_document(chunk))

        result = self.search_client.upload_documents(documents)
        return result

    # ── semantic / vector search ──────────────

    def semantic_search(
        self,
        vector_query: List[float],
        top_k: int = 14,
    ) -> List[Chunk]:
        """
        Perform a vector-based semantic search.

        Args:
            vector_query (List[float]): Embedding of the user query.
            top_k (int): Number of top results to retrieve. Defaults to 7.

        Returns:
            List[Chunk]: Matching chunks with all fields populated.

        Raises:
            RuntimeError: If an error occurs during the search operation.
        """
        try:

            # ── vector query ──────────────────────────────────────────────
            vector_query_obj = VectorizedQuery(
                vector=vector_query,
                k_nearest_neighbors=top_k,
                fields="embedding",
            )

            results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query_obj],
                select=[
                    "chunk_id",
                    "doc_name",
                    "paragraph_id",
                    "title",
                    "sub_title",
                    "chunk_text",
                    "original_text",
                    "has_table",
                    "table_metadata",
                ],
                top=top_k,
                query_type="semantic",
                semantic_configuration_name="semantic_config",
            )

            # ── map results → Chunk objects ───────────────────────────────
            chunks: List[Chunk] = []
            for r in results:
                chunk = Chunk(
                    id=r["chunk_id"],
                    doc_name=r["doc_name"],
                    paragraph_id=r["paragraph_id"],
                    title=r.get("title"),
                    sub_title=r.get("sub_title"),
                    chunk_text=r["chunk_text"],
                    original_text=r["original_text"],
                    has_table=r.get("has_table", False),
                    table_metadata=r.get("table_metadata") or [],
                    embedding=None,
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            raise RuntimeError(
                "Error occurred during vector search in Azure Cognitive Search"
            ) from e

    # ── generate context ─────────────────────────────
    @staticmethod
    def get_context_from_chunks(chunks: List[Chunk]) -> str:
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
                entry += f"\n{chunk.original_text}"

                context_list.append(entry)
                seen_paragraphs.add(chunk.paragraph_id)

        return "\n\n".join(context_list)
