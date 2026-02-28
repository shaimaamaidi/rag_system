
"""
Module: create_azure_index

This script is responsible for creating or updating the Azure Cognitive Search index
used by the RAG application. It utilizes the `AzureSearchClient` to configure the index
with vector search and semantic search capabilities.
"""
from src.infrastructure.persistence.azure_search_client import AzureSearchClient


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
        client.index_client.delete_index(client.index_name)
        index = client.create_index()
        print("hi")
    except Exception as e:
        print("Failed to create Azure Search index")
        raise e


if __name__ == "__main__":
    main()
