"""
Module: fastapi_exception_handler
Description:
    Centralized exception handling for FastAPI.
    Handles AppException, validation errors, and generic unhandled exceptions.
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions.app_exception import AppException

# HTTP status codes that indicate config/infra errors (always 5xx)
_CONFIG_CODES = {
    "AZURE_CONFIG_ERROR",
    "AZURE_DOC_CONFIG_ERROR",
    "AZURE_SEARCH_CONFIG_ERROR",
    "LLAMA_CONFIG_ERROR",
    "EMBEDDING_INIT_ERROR",
    "WORKFLOW_CONVERTER_CONFIG_ERROR",
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
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc)
                }
            }
        )