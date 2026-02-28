from abc import ABC, abstractmethod
from src.domain.models.ocr_result_model import OcrResult


class LlamaOcrPort(ABC):
    """Port primaire : contrat que tout processor OCR doit respecter"""

    @abstractmethod
    def process(self, image_path: str) -> OcrResult:
        """Upload, attend, extrait et retourne un OcrResult"""
        pass