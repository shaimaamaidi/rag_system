"""Base application exception for domain-specific errors."""


class AppException(Exception):
    """Base exception for domain and business logic errors.

    :ivar message: Human-readable error message.
    :ivar code: Error code identifier.
    :ivar http_status: HTTP status code for API responses.
    """

    def __init__(self, message: str, code: str = "APP_ERROR", http_status: int = 400):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)