import asyncio

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.application.use_cases.ingest_pipeline import IngestDocumentUseCase


def test_ingest_use_case_calls_service():
    class DummyService:
        def __init__(self):
            self.called = None

        async def ingest(self, documents_dir):
            self.called = documents_dir

    svc = DummyService()
    use_case = IngestDocumentUseCase(svc)

    asyncio.run(use_case.ingest("/tmp/docs"))

    assert svc.called == "/tmp/docs"


def test_ask_use_case_calls_service():
    class DummyService:
        def __init__(self):
            self.called = None

        def execute(self, question, enhancement_question):
            self.called = (question, enhancement_question)
            return "ok"

    svc = DummyService()
    use_case = AskQuestionUseCase(svc)

    result = use_case.execute("hi", "enhanced")

    assert result == "ok"
    assert svc.called == ("hi", "enhanced")
