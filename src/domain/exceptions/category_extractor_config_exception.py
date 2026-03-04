"""Exception raised when category extractor configuration is invalid."""

from src.domain.exceptions.app_exception import AppException


class CategoryExtractorConfigException(AppException):
    """Error raised when category extractor configuration is missing or invalid."""

    def __init__(self, message: str):
        """Initialize the exception.

        :param message: Human-readable error message.
        """
        super().__init__(message, code="CATEGORY_EXTRACTOR_CONFIG_ERROR", http_status=500)
