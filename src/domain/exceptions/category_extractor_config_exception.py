# ── Document Category Extractor ───────────────────────────────────────────────
from src.domain.exceptions.app_exception import AppException


class CategoryExtractorConfigException(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="CATEGORY_EXTRACTOR_CONFIG_ERROR", http_status=500)
