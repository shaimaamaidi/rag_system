"""Exception raised when Azure OpenAI answer generation fails."""
from src.domain.exceptions.app_exception import AppException


class AzureOpenAIAnswerException(AppException):
    """Error raised when Azure OpenAI fails to generate an answer."""

    def __init__(self, message: str, code: str = "ANSWER_GENERATION_ERROR", http_status: int = 502):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)