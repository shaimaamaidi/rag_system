import asyncio

from fastapi.exceptions import RequestValidationError
from fastapi import Request
from starlette.datastructures import URL

from src.domain.exceptions.app_exception import AppException
from src.infrastructure.handlers.exception_handler import FastAPIExceptionHandler


def test_handle_app_exception():
    exc = AppException("boom", code="X", http_status=418)
    request = Request({"type": "http", "path": "/", "headers": [], "scheme": "http", "server": ("test", 80)})

    response = asyncio.run(FastAPIExceptionHandler.handle_app_exception(request, exc))

    assert response.status_code == 418
    assert response.body


def test_handle_validation_exception():
    err = RequestValidationError([{"loc": ["body"], "msg": "bad", "type": "value_error"}])
    request = Request({"type": "http", "path": "/", "headers": [], "scheme": "http", "server": ("test", 80)})

    response = asyncio.run(FastAPIExceptionHandler.handle_validation_exception(request, err))

    assert response.status_code == 422
    assert response.body


def test_handle_generic_exception():
    request = Request({"type": "http", "path": "/", "headers": [], "scheme": "http", "server": ("test", 80)})
    response = asyncio.run(FastAPIExceptionHandler.handle_generic_exception(request, RuntimeError("boom")))

    assert response.status_code == 500
    assert response.body
