"""Exception raised when page image extraction fails."""
from src.domain.exceptions.app_exception import AppException


class PageImageExtractionException(AppException):
    """Error raised when a page image cannot be extracted."""

    def __init__(self, message: str, code: str = "PAGE_IMAGE_EXTRACTION_ERROR", http_status: int = 422):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)