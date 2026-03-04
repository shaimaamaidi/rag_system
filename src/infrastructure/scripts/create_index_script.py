
"""
Module: create_azure_index

This script is responsible for creating or updating the Azure Cognitive Search index
used by the RAG application. It utilizes the `AzureSearchClient` to configure the index
with vector search and semantic search capabilities.
"""
import logging

from azure.core.exceptions import ResourceNotFoundError

from src.infrastructure.adapters.config.logger import setup_logger
from src.infrastructure.persistence.azure_search_client import AzureSearchClient

setup_logger()
logger = logging.getLogger(__name__)


def main():
    """
    Main function to initialize the Azure Search client and create or update the index.

    Responsibilities:
        - Initialize the AzureSearchClient using environment variables.
        - Create or update the search index with vector and semantic search enabled.

    Raises:
        Exception: Propagates any exception raised during index creation or client initialization.
    """
    try:
        client = AzureSearchClient()
        logger.info("AzureSearchClient initialized.")

        try:
            client.index_client.delete_index(client.index_name)
            logger.info("Existing index '%s' deleted.", client.index_name)
        except ResourceNotFoundError:
            logger.info("Index '%s' does not exist, nothing to delete.", client.index_name)

        logger.info("Azure Search index '%s' created or updated successfully.", client.index_name)
        index = client.create_index()
    except Exception as e:
        logger.exception("Failed to create or update Azure Search index: %s", str(e))
        raise e


if __name__ == "__main__":
    main()
