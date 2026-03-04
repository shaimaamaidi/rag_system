"""Exception raised when Azure Document Intelligence analysis fails."""
from src.domain.exceptions.app_exception import AppException


class AzureDocumentAnalysisException(AppException):
    """Error raised when document analysis fails in Azure Document Intelligence."""

    def __init__(self, message: str, code: str = "DOCUMENT_ANALYSIS_ERROR", http_status: int = 422):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)