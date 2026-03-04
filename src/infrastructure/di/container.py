"""Dependency injection container for wiring application components."""

import logging

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.application.use_cases.ingest_pipeline import IngestDocumentUseCase
from src.domain.services.answer_question_service import AnswerQuestionService
from src.domain.services.document_category_extractor import DocumentCategoryExtractor
from src.domain.services.document_chunking import SmartChunker
from src.domain.services.ingestion_pipeline_service import DocumentIngestionService
from src.infrastructure.adapters.agent.agent_adapter import AzureAgentAdapter
from src.infrastructure.adapters.answer_generation.azure_answer_generator import AzureOpenAIAnswerGenerator
from src.infrastructure.logging.logger import setup_logger
from src.infrastructure.adapters.document_embedding.document_embedding import DocumentEmbedding
from src.infrastructure.adapters.document_loader.document_loader import DocumentLoader
from src.infrastructure.adapters.search_adapter.azure_search_adapter import AzureAISearchAdapter
from src.infrastructure.adapters.tools.search_tool import create_search_tool
from src.infrastructure.persistence.azure_search_client import AzureSearchClient
from src.infrastructure.prompts.loader.prompt_loader import PromptyLoader

setup_logger()
logger = logging.getLogger(__name__)


class Container:
    """Construct and hold configured adapters, services, and use cases."""

    def __init__(self):
        """Initialize and wire all application components."""
        logger.info("Initializing Container...")

        self.prompt_provider = PromptyLoader()
        logger.info("Prompt provider initialized")

        self._initialize_adapters()
        self._initialize_services()
        self._initialize_use_cases()
        self._initialize_tools()
        self.agent_adapter = AzureAgentAdapter(
            search_tool=self.search_tool,
            prompt_provider=self.prompt_provider
        )
        logger.info("Agent adapter initialized")


    def _initialize_adapters(self) -> None:
        """Create and configure infrastructure adapters.

        :return: None.
        """
        self.document_loader = DocumentLoader(prompt_provider=self.prompt_provider)
        logger.info("Document loader initialized")

        self.extractor_category = DocumentCategoryExtractor()
        logger.info("Document category extractor initialized")

        self.chunker = SmartChunker(extractor_category=self.extractor_category)
        logger.info("Chunker initialized")

        self.embedding_provider = DocumentEmbedding()
        logger.info("Document embedding provider initialized")

        self.search_client = AzureSearchClient()
        logger.info("Azure Search client initialized (index: %s)", self.search_client.index_name)

        self.vector_store = AzureAISearchAdapter(client=self.search_client)
        logger.info("Vector store adapter initialized")

        self.answer_generator = AzureOpenAIAnswerGenerator(
            prompt_provider=self.prompt_provider
        )
        logger.info("Answer generator initialized")


    def _initialize_services(self) -> None:
        """Create domain services.

        :return: None.
        """
        self.ingestion_service = DocumentIngestionService(
            loader=self.document_loader,
            chunker=self.chunker,
            embedding=self.embedding_provider,
            vector_store=self.vector_store
        )
        logger.info("Document ingestion service initialized")

        self.answer_service = AnswerQuestionService(
            embedding_model=self.embedding_provider,
            vector_store=self.vector_store,
            answer_generator=self.answer_generator
        )
        logger.info("Answer question service initialized")

    def _initialize_use_cases(self) -> None:
        """Create application use cases.

        :return: None.
        """
        self.ingest_use_case = IngestDocumentUseCase(self.ingestion_service)
        logger.info("Ingest document use case initialized")

        self.ask_use_case = AskQuestionUseCase(self.answer_service)
        logger.info("Ask question use case initialized")

    def _initialize_tools(self) -> None:
        """Create tool adapters used by the agent.

        :return: None.
        """
        self.search_tool = create_search_tool(self.ask_use_case)
        logger.info("Search tool initialized")

    def __repr__(self) -> str:
        """Return a concise summary of the container contents.

        :return: Debug-friendly string representation.
        """
        return (
            f"<Container(\n"
            f"  adapters=5,\n"
            f"  services=2,\n"
            f"  use_cases=2,\n"
            f"  index='{self.search_client.index_name}'\n"
            f")>"
        )