from src.domain.models.chunk_model import Chunk
from src.infrastructure.adapters.search_adapter.azure_search_adapter import AzureAISearchAdapter


def test_search_adapter_store_and_search():
    class DummyRepository:
        def __init__(self):
            self.uploaded = None

        def upload_chunks(self, chunks):
            self.uploaded = list(chunks)

        def semantic_search(self, vector, top_k):
            return [Chunk(
                id="c1",
                doc_name="doc",
                paragraph_id="p1",
                title=None,
                sub_title=None,
                target_group="",
                chunk_text="ct",
                original_text="ot",
                has_table=False,
                table_metadata=[],
                embedding=None,
            )]

    class DummyAdapter(AzureAISearchAdapter):
        def __init__(self):
            self.repository = DummyRepository()

    adapter = DummyAdapter()

    chunk = Chunk(
        id="c1",
        doc_name="doc",
        paragraph_id="p1",
        title=None,
        sub_title=None,
        target_group="",
        chunk_text="ct",
        original_text="ot",
        has_table=False,
        table_metadata=[],
        embedding=[0.1],
    )

    adapter.store_chunks([chunk])
    result = adapter.search([0.1], top_k=1)

    assert adapter.repository.uploaded[0].id == "c1"
    assert result[0].id == "c1"
