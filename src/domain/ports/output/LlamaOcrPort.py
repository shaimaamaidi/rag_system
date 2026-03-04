"""Output port interface for OCR processing."""

from abc import ABC, abstractmethod
from src.domain.models.ocr_result_model import OcrResult


class LlamaOcrPort(ABC):
    """Interface contract for OCR processors."""

    @abstractmethod
    def process(self, image_path: str) -> OcrResult:
        """Process an image and return OCR results.

        :param image_path: Path to the image file.
        :return: OCR result payload.
        """
        pass