"""Exception raised when Azure Search index operations fail."""
from src.domain.exceptions.app_exception import AppException


class AzureSearchIndexException(AppException):
    """Error raised when Azure Search index creation or update fails."""

    def __init__(self, message: str, code: str = "AZURE_SEARCH_INDEX_ERROR", http_status: int = 502):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)