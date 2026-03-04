"""Input port interface for document loading."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading


class DocumentLoaderPort(ABC):
    """Interface contract for document loading implementations."""

    @abstractmethod
    def load(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        """Load a document and return its pages and headings.

        :param file_path: Path to the source document.
        :return: Tuple of page content and section headings.
        """
        ...