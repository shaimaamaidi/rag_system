"""Exception raised when a question is empty or invalid."""
from src.domain.exceptions.app_exception import AppException


class QuestionEmptyException(AppException):
    """Error raised when the input question is empty."""

    def __init__(self, message: str, code: str = "QUESTION_EMPTY_ERROR", http_status: int = 400):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)