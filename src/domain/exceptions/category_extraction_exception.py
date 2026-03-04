"""Exception raised when category extraction fails."""

from src.domain.exceptions.app_exception import AppException


class CategoryExtractionException(AppException):
    """Error raised when categories cannot be extracted from Excel."""

    def __init__(self, message: str):
        """Initialize the exception.

        :param message: Human-readable error message.
        """
        super().__init__(message, code="CATEGORY_EXTRACTION_ERROR", http_status=500)