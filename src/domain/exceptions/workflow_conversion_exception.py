"""Exception raised when workflow conversion fails."""
from src.domain.exceptions.app_exception import AppException


class WorkflowConversionException(AppException):
    """Error raised when Mermaid workflow conversion fails."""

    def __init__(self, message: str, code: str = "WORKFLOW_CONVERSION_ERROR", http_status: int = 502):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)