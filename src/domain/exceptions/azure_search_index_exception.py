"""
Module: app_exception
Description:
    This module defines the base application exception `AppException` used for
    domain-specific or business logic errors. Other custom exceptions should
    inherit from this class.

    The `AppException` class includes attributes for a message, an error code,
    and an HTTP status code, allowing consistent error handling across the
    application.
"""
from src.domain.exceptions.app_exception import AppException


class AzureSearchIndexException(AppException):
    """
    Base application (business) exception.

    This exception can be used to represent domain-specific or business logic
    errors in the application. All other custom exceptions should inherit from
    this class.

    Attributes:
        message (str): Description of the exception.
        code (str): Error code representing the type of application exception.
                    Defaults to "APP_ERROR".
        http_status (int): HTTP status code associated with this exception.
    """

    def __init__(self, message: str, code: str = "AZURE_SEARCH_INDEX_ERROR", http_status: int = 502):
        """
        Initialize a new AppException instance.

        Args:
            message (str): A human-readable description of the exception.
            code (str, optional): A string representing the error code. Defaults to "APP_ERROR".
            http_status (int, optional): HTTP status code to be returned. Defaults to 400.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)