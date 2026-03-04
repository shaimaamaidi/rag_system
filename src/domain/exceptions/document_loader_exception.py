"""Exception raised when document loading fails."""
from src.domain.exceptions.app_exception import AppException


class DocumentLoaderException(AppException):
    """Error raised when a document cannot be loaded or parsed."""

    def __init__(self, message: str, code: str = "DOCUMENT_LOADER_ERROR", http_status: int = 400):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)