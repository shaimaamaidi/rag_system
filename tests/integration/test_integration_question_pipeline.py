from src.domain.models.chunk_model import Chunk
from src.domain.services.answer_question_service import AnswerQuestionService


def test_question_pipeline_integration():
    class DummyEmbedding:
        def get_embedding_vector(self, _):
            class _Res:
                vector = [0.1]
            return _Res()

    class DummyStore:
        def search(self, *_args, **_kwargs):
            return [
                Chunk(
                    id="c1",
                    doc_name="doc",
                    paragraph_id="p1",
                    title="T",
                    target_group=["TG"],
                    chunk_text="ct",
                    original_text="ot",
                    has_table=False,
                    table_metadata=[],
                    embedding=None,
                )
            ]

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return DummyStore().search()

    service = AnswerQuestionService(DummyEmbedding(), DummyStore(), DummyClassifier())
    context = service.execute("hello", "enhanced")
    assert "[doc]" in context
