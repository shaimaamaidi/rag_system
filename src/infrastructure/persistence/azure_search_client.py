import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    VectorSearch,
    SimpleField,
)

from src.domain.exceptions.azure_search_config_exception import AzureSearchConfigException
from src.domain.exceptions.azure_search_index_exception import AzureSearchIndexException


class AzureSearchClient:
    """
    Wrapper for Azure Cognitive Search client.

    Index schema matches the Chunk dataclass produced by SmartChunker.

    Environment variables required:
        - AZURE_AI_SEARCH_ENDPOINT
        - AZURE_AI_SEARCH_INDEX_NAME
        - AZURE_AI_SEARCH_API_KEY
        - AZURE_EMBEDDING_DIMENSIONS  (optional, default: 3072)
    """

    def __init__(self):
        load_dotenv()
        self.endpoint   = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
        self.api_key    = os.getenv("AZURE_AI_SEARCH_API_KEY")

        self.embedding_dimensions = int(os.getenv("AZURE_EMBEDDING_DIMENSIONS", 3072))

        if not all([self.endpoint, self.index_name, self.api_key]):
            raise AzureSearchConfigException(
                message="Missing Azure AI Search environment variables: "
                        "AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_INDEX_NAME, AZURE_AI_SEARCH_API_KEY"
            )

        self.credential   = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )

    # ──────────────────────────────────────────
    # Index creation
    # ──────────────────────────────────────────

    def create_index(self) -> SearchIndex:
        """
        Create or update the Azure Cognitive Search index.

        Fields (aligned with Chunk dataclass):
            - chunk_id     → Chunk.id            (key, filterable)
            - doc_name     → Chunk.doc_name       (filterable, sortable)
            - paragraph_id → Chunk.paragraph_id   (filterable, sortable)
            - title        → Chunk.title           (searchable, filterable)
            - sub_title    → Chunk.sub_title       (searchable, filterable, semantic keywords)
            - chunk_text   → Chunk.chunk_text      (searchable, semantic content)
            - original_text→ Chunk.original_text   (searchable)
            - has_table    → Chunk.has_table        (filterable)
            - table_metadata→Chunk.table_metadata  (searchable)
            - embedding    → Chunk.embedding        (vector, HNSW)
        """
        try:
            fields = [
                # ── identifiers ──────────────────────────────────────────────
                SimpleField(
                    name="chunk_id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                ),
                SimpleField(
                    name="doc_name",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True,
                ),
                SimpleField(
                    name="paragraph_id",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True,
                ),

                # ── textual content ──────────────────────────────────────────
                SearchField(
                    name="title",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                ),
                SearchField(
                    name="sub_title",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                ),
                SearchField(
                    name="target_group",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                    sortable=True,
                ),
                SearchField(
                    name="chunk_text",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
                SearchField(
                    name="original_text",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=False,
                ),

                # ── metadata ─────────────────────────────────────────────────
                SimpleField(
                    name="has_table",
                    type=SearchFieldDataType.Boolean,
                    filterable=True,
                ),
                SearchField(
                    name="table_metadata",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True,
                    filterable=False,
                ),

                # ── vector embedding ─────────────────────────────────────────
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.embedding_dimensions,
                    vector_search_profile_name="hnsw_profile",
                ),
            ]

            # ── vector search (HNSW) ─────────────────────────────────────────
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="hnsw_algo"),
                ],
                profiles=[
                    VectorSearchProfile(
                        name="hnsw_profile",
                        algorithm_configuration_name="hnsw_algo",
                    ),
                ],
            )

            # ── semantic search ──────────────────────────────────────────────
            # Priority: chunk_text (content) > sub_title > title (keywords)
            semantic_search = SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="semantic_config",
                        prioritized_fields=SemanticPrioritizedFields(
                            content_fields=[
                                SemanticField(field_name="chunk_text"),
                            ],
                            keywords_fields=[
                                SemanticField(field_name="sub_title"),
                                SemanticField(field_name="title"),
                            ],
                        ),
                    )
                ]
            )

            search_index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search,
            )

            result = self.index_client.create_or_update_index(search_index)
            return result
        except Exception as e:
            raise AzureSearchIndexException(
                message=f"Failed to create or update Azure Search index '{self.index_name}': {str(e)}",
            ) from e
    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    def get_search_client(self) -> SearchClient:
        """Return a SearchClient ready to query the index."""
        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

    @staticmethod
    def chunk_to_document(chunk) -> dict:
        """
        Convert a Chunk dataclass instance into an Azure Search document dict.

        Args:
            chunk (Chunk): A Chunk produced by SmartChunker.

        Returns:
            dict: Ready-to-upload document for Azure Search.

        Usage:
            docs = [AzureSearchClient.chunk_to_document(c) for c in chunks]
            search_client.upload_documents(docs)
        """
        return {
            "chunk_id":      chunk.id,
            "doc_name":      chunk.doc_name,
            "paragraph_id":  chunk.paragraph_id,
            "title":         chunk.title or "",
            "sub_title":     chunk.sub_title or "",
            "target_group":  chunk.target_group or "",
            "chunk_text":    chunk.chunk_text,
            "original_text": chunk.original_text,
            "embedding":     chunk.embedding,
            "has_table":     chunk.has_table,
            "table_metadata": [str(x) for x in (chunk.table_metadata or [])],
        }