import asyncio
import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.ask_request_model import AskRequest
from src.presentation.api.routers.ask_router import ask_question
from src.presentation.api.routers.ingest_router import ingest_document
from src.presentation.api.routers.health_router import health


def test_ask_question_stream():
    class DummyAgent:
        def ask_question_stream(self, question):
            assert question == "hello"
            yield "part1"
            yield "part2"

    response = asyncio.run(ask_question(AskRequest(question="hello"), agent=DummyAgent()))

    async def _collect():
        result = []
        async for item in response.body_iterator:
            result.append(item)
        return result

    chunks = asyncio.run(_collect())
    assert chunks == ["part1", "part2"]
    assert response.media_type == "text/event-stream"


def test_ask_question_empty():
    class DummyAgent:
        def ask_question_stream(self, question):
            raise AssertionError("should not be called")

    with pytest.raises(QuestionEmptyException):
        class DummyBody:
            question = "  "

        asyncio.run(ask_question(DummyBody(), agent=DummyAgent()))


def test_ingest_document_success():
    class DummyUseCase:
        def __init__(self):
            self.called = None

        async def ingest(self, file_bytes, filename):
            self.called = (file_bytes, filename)

    use_case = DummyUseCase()
    upload = UploadFile(filename="file.pdf", file=io.BytesIO(b"abc"))

    result = asyncio.run(ingest_document(file=upload, use_case=use_case))

    assert result.status == "success"
    assert use_case.called[1] == "file.pdf"


def test_ingest_document_unsupported():
    upload = UploadFile(filename="file.txt", file=io.BytesIO(b"abc"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(file=upload, use_case=object()))

    assert exc_info.value.status_code == 415


def test_health():
    result = asyncio.run(health())
    assert result == {"status": "ok"}
