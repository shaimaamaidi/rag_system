
"""Create or update the Azure Cognitive Search index used by the RAG app."""
import logging

from azure.core.exceptions import ResourceNotFoundError

from src.infrastructure.logging.logger import setup_logger
from src.infrastructure.persistence.azure_search_client import AzureSearchClient

setup_logger()
logger = logging.getLogger(__name__)


def main():
    """Create or update the Azure Search index.

    :raises Exception: Propagates errors raised during index creation.
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
