from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.application.use_cases.ingest_pipeline import IngestDocumentUseCase
from src.domain.service.answer_question_service import AnswerQuestionService
from src.domain.service.document_chunking import SmartChunker
from src.domain.service.ingestion_pipeline_service import DocumentIngestionService
from src.infrastructure.adapters.answer_generation.azure_answer_generator import AzureOpenAIAnswerGenerator
from src.infrastructure.adapters.document_embedding.document_embedding import DocumentEmbedding
from src.infrastructure.adapters.document_loader.document_loader import DocumentLoader
from src.infrastructure.adapters.search_adapter.azure_search_adapter import AzureAISearchAdapter
from src.infrastructure.persistence.azure_search_client import AzureSearchClient
from src.infrastructure.prompts.loader.prompt_loader import PromptyLoader


class Container:
    """
    Dependency injection container for all RAG application components.
    """

    def __init__(self):
        self.prompt_provider = PromptyLoader()
        self._initialize_adapters()
        self._initialize_services()
        self._initialize_use_cases()

    def _initialize_adapters(self) -> None:
        # Prompts
        # déjà initialisé dans __init__

        # Document loading (passe prompt_provider pour AzureWorkflowConverter)
        self.document_loader = DocumentLoader(prompt_provider=self.prompt_provider)

        # Chunking
        self.chunker = SmartChunker()

        # Embedding
        self.embedding_provider = DocumentEmbedding()

        # Azure Search
        self.search_client = AzureSearchClient()
        self.vector_store = AzureAISearchAdapter(client=self.search_client)

        # Answer generation
        self.answer_generator = AzureOpenAIAnswerGenerator(
            azure_adapter=self.vector_store,
            prompt_provider=self.prompt_provider
        )

    def _initialize_services(self) -> None:
        self.ingestion_service = DocumentIngestionService(
            loader=self.document_loader,
            chunker=self.chunker,
            embedding=self.embedding_provider,
            vector_store=self.vector_store
        )

        self.rag_service = AnswerQuestionService(
            embedding_model=self.embedding_provider,
            vector_store=self.vector_store,
            answer_generator=self.answer_generator
        )

    def _initialize_use_cases(self) -> None:
        self.ingest_use_case = IngestDocumentUseCase(self.ingestion_service)
        self.ask_use_case = AskQuestionUseCase(self.rag_service)

    def __repr__(self) -> str:
        return (
            f"<Container(\n"
            f"  adapters=5,\n"
            f"  services=2,\n"
            f"  use_cases=2,\n"
            f"  index='{self.search_client.index_name}'\n"
            f")>"
        )