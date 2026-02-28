from abc import ABC, abstractmethod
from typing import List, Tuple
from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading


class DocumentLoaderPort(ABC):
    """Port primaire : contrat que toute implémentation de chargement doit respecter."""

    @abstractmethod
    def load(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        """Charge un document et retourne ses pages et ses headings."""
        ...