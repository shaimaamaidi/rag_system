"""
Module: fastapi_exception_handler
Description:
    Centralized exception handling for FastAPI.
    Handles AppException, validation errors, and generic unhandled exceptions.
"""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions.app_exception import AppException
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


# HTTP status codes that indicate config/infra errors (always 5xx)
_CONFIG_CODES = {
    "AZURE_CONFIG_ERROR",
    "AZURE_DOC_CONFIG_ERROR",
    "AZURE_SEARCH_CONFIG_ERROR",
    "LLAMA_CONFIG_ERROR",
    "EMBEDDING_INIT_ERROR",
    "WORKFLOW_CONVERTER_CONFIG_ERROR",
    "AZURE_AGENT_CONFIG_ERROR",
    "CATEGORY_EXTRACTOR_CONFIG_ERROR",
}


class FastAPIExceptionHandler:
    """
    Centralized exception handler for FastAPI.

    Provides static methods to handle:
        - AppException (all custom domain/infra exceptions)
        - RequestValidationError (FastAPI input validation)
        - Exception (unhandled generic errors)
    """

    @staticmethod
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """
        Handles all AppException subclasses.
        Uses exc.http_status directly — set per exception class.
        """
        if exc.code in _CONFIG_CODES:
            logger.error("Configuration/Infrastructure Error [%s]: %s", exc.code, exc.message, exc_info=exc)
        else:
            logger.warning("Application Error [%s]: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )

    @staticmethod
    async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        Handles FastAPI request validation errors (422).
        """
        logger.info("Validation Error on request %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors()
                }
            }
        )

    @staticmethod
    async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        """
        Handles all unhandled exceptions (500).
        """
        logger.error("Unhandled exception on request %s: %s", request.url.path, str(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc)
                }
            }
        )