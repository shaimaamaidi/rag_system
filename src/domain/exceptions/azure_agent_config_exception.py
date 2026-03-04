"""Exception raised when Azure agent configuration is invalid."""
from src.domain.exceptions.app_exception import AppException


class AzureAgentConfigException(AppException):
    """Error raised when Azure agent configuration is missing or invalid."""

    def __init__(self, message: str, code: str = "AZURE_AGENT_CONFIG_ERROR", http_status: int = 500):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)