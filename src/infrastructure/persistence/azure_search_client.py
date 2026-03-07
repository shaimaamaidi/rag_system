"""Azure Cognitive Search client wrapper and index management."""

import logging
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
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class AzureSearchClient:
    """Wrapper for Azure Cognitive Search clients and index creation.

    :ivar endpoint: Azure Search endpoint URL.
    :ivar index_name: Search index name.
    :ivar api_key: Azure Search API key.
    :ivar embedding_dimensions: Expected embedding vector dimensions.
    """

    def __init__(self):
        """Initialize the search client from environment variables.

        :raises AzureSearchConfigException: If required env vars are missing.
        """
        load_dotenv()
        self.endpoint   = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
        self.api_key    = os.getenv("AZURE_AI_SEARCH_API_KEY")

        self.embedding_dimensions = int(os.getenv("AZURE_EMBEDDING_DIMENSIONS", 3072))

        if not all([self.endpoint, self.index_name, self.api_key]):
            logger.error("Missing Azure Search environment variables.")
            raise AzureSearchConfigException(
                message="Missing Azure AI Search environment variables: "
                        "AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_INDEX_NAME, AZURE_AI_SEARCH_API_KEY"
            )

        self.credential   = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
        logger.info("AzureSearchClient initialized.")

    def create_index(self) -> SearchIndex:
        """Create or update the Azure Cognitive Search index.

        :return: Created or updated search index.
        :raises AzureSearchIndexException: If index creation fails.
        """
        try:
            logger.info("Creating/updating Azure Search index.")
            fields = [
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
                    facetable=True,
                ),
                SimpleField(
                    name="paragraph_id",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True,
                ),

                SearchField(
                    name="title",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                ),
                SearchField(
                    name="target_group",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=False,
                    filterable=True,
                    sortable=False,
                ),
                SearchField(
                    name="chunk_text",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
                SearchField(
                    name="original_text",
                    type=SearchFieldDataType.String,
                    filterable=False,
                ),

                SimpleField(
                    name="has_table",
                    type=SearchFieldDataType.Boolean,
                    filterable=True,
                ),
                SearchField(
                    name="table_metadata",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=False,
                    filterable=False,
                ),

                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.embedding_dimensions,
                    vector_search_profile_name="hnsw_profile",
                ),
            ]

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

            semantic_search = SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="semantic_config",
                        prioritized_fields=SemanticPrioritizedFields(
                            content_fields=[
                                SemanticField(field_name="chunk_text"),
                            ],
                            keywords_fields=[
                                SemanticField(field_name="doc_name"),
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
            logger.info("Azure Search index created/updated successfully")

            return result
        except Exception as e:
            logger.exception("Failed to create/update Azure Search index '%s'", self.index_name)
            raise AzureSearchIndexException(
                message=f"Failed to create or update Azure Search index '{self.index_name}': {str(e)}",
            ) from e
    def get_search_client(self) -> SearchClient:
        """Return a search client bound to the configured index.

        :return: Search client instance.
        """
        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

    @staticmethod
    def chunk_to_document(chunk) -> dict:
        """Convert a chunk object into an Azure Search document dict.

        :param chunk: Chunk produced by the chunker.
        :return: Document ready for upload.
        """
        return {
            "chunk_id":      chunk.id,
            "doc_name":      chunk.doc_name,
            "paragraph_id":  chunk.paragraph_id,
            "title":         chunk.title or "",
            "target_group":  chunk.target_group or [],
            "chunk_text":    chunk.chunk_text,
            "original_text": chunk.original_text,
            "embedding":     chunk.embedding,
            "has_table":     chunk.has_table,
            "table_metadata": [str(x) for x in (chunk.table_metadata or [])],
        }