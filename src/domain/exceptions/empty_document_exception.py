"""Exception raised when a document contains no usable content."""
from src.domain.exceptions.app_exception import AppException


class EmptyDocumentException(AppException):
    """Error raised when no pages or chunks are extracted."""

    def __init__(self, message: str, code: str = "EMPTY_DOCUMENT_ERROR", http_status: int = 422):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)