from src.domain.exceptions.app_exception import AppException


class CategoryExtractionException(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="CATEGORY_EXTRACTION_ERROR", http_status=500)