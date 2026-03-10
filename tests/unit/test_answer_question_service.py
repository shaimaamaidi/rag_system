import pytest

from src.domain.exceptions.answer_generation_exception import AnswerGenerationException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.chunk_model import Chunk
from src.domain.services.answer_question_service import AnswerQuestionService


class _EmbedResult:
    def __init__(self, vector):
        self.vector = vector


def test_execute_empty_question():
    service = AnswerQuestionService(None, None, None)
    with pytest.raises(QuestionEmptyException):
        service.execute("   ", "enh")


def test_execute_embedding_error():
    class DummyEmbedding:
        def get_embedding_vector(self, _):
            raise RuntimeError("fail")

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return []

    service = AnswerQuestionService(DummyEmbedding(), None, DummyClassifier())
    with pytest.raises(AnswerGenerationException):
        service.execute("hello", "enhanced")


def test_execute_search_error():
    class DummyEmbedding:
        def get_embedding_vector(self, _):
            return _EmbedResult([0.1])

    class DummyStore:
        def search(self, *_args, **_kwargs):
            raise RuntimeError("fail")

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return []

    service = AnswerQuestionService(DummyEmbedding(), DummyStore(), DummyClassifier())
    with pytest.raises(AnswerGenerationException):
        service.execute("hello", "enhanced")


def test_execute_no_chunks():
    class DummyEmbedding:
        def get_embedding_vector(self, _):
            return _EmbedResult([0.1])

    class DummyStore:
        def search(self, *_args, **_kwargs):
            return []

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return []

    service = AnswerQuestionService(DummyEmbedding(), DummyStore(), DummyClassifier())
    with pytest.raises(AnswerGenerationException):
        service.execute("hello", "enhanced")


def test_execute_success_with_tables():
    class DummyEmbedding:
        def get_embedding_vector(self, _):
            return _EmbedResult([0.1])

    chunks = [
        Chunk(
            id="c1",
            doc_name="doc",
            paragraph_id="p1",
            title="Title",
            target_group=["TG"],
            chunk_text="chunk",
            original_text="orig",
            has_table=True,
            table_metadata=[{"a": 1}],
            embedding=None,
        )
    ]

    class DummyStore:
        def search(self, *_args, **_kwargs):
            return chunks

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return chunks

    service = AnswerQuestionService(DummyEmbedding(), DummyStore(), DummyClassifier())
    context = service.execute("hello", "enhanced")
    assert "[doc]" in context
    assert "tables" in context


def test_get_context_from_chunks_dedup():
    chunks = [
        Chunk(
            id="c1",
            doc_name="doc",
            paragraph_id="p1",
            title=None,
            target_group=[],
            chunk_text="c1",
            original_text="o1",
            has_table=False,
            table_metadata=[],
            embedding=None,
        ),
        Chunk(
            id="c2",
            doc_name="doc",
            paragraph_id="p1",
            title=None,
            target_group=[],
            chunk_text="c2",
            original_text="o2",
            has_table=False,
            table_metadata=[],
            embedding=None,
        ),
    ]

    context = AnswerQuestionService._get_context_from_chunks(chunks)
    assert context.count("[doc]") == 1
