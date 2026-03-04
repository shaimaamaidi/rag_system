"""Exception raised when a chunk lacks an embedding."""
from src.domain.exceptions.app_exception import AppException


class ChunkMissingEmbeddingException(AppException):
    """Error raised when a chunk is missing its embedding vector."""

    def __init__(self, message: str, code: str = "CHUNK_MISSING_EMBEDDING_ERROR", http_status: int = 422):
        """Initialize the exception.

        :param message: Human-readable error message.
        :param code: Error code identifier.
        :param http_status: HTTP status code to return.
        """
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)