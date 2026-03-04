"""FastAPI application factory for the RAG API."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.domain.exceptions.app_exception import AppException
from src.infrastructure.di.container import Container
from src.infrastructure.handlers.exception_handler import FastAPIExceptionHandler
from src.presentation.api.routers import ask_router, ingest_router, health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :return: Configured FastAPI application instance.
    """
    app = FastAPI(
        title="RAG API",
        description="Retrieval-Augmented Generation API — ingest documents and answer questions.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.container = Container()

    app.add_exception_handler(AppException, FastAPIExceptionHandler.handle_app_exception)
    app.add_exception_handler(RequestValidationError, FastAPIExceptionHandler.handle_validation_exception)
    app.add_exception_handler(Exception, FastAPIExceptionHandler.handle_generic_exception)

    app.include_router(ingest_router.router, prefix="/api/v1")
    app.include_router(ask_router.router, prefix="/api/v1")
    app.include_router(health_router.router)

    return app


app = create_app()