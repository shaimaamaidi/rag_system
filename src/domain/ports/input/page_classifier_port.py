"""Input port interface for page classification."""

from typing import Protocol, Literal

from azure.ai.documentintelligence.models import DocumentPage

PageLabel = Literal["workflow", "text"]

class PageClassifierPort(Protocol):
    """Interface for classifying a page as workflow or text."""

    def classify(self, page: DocumentPage, has_keyword: bool) -> PageLabel:
        """Classify a page into a label.

        :param page: Azure Document Intelligence page.
        :param has_keyword: Whether workflow keywords were detected.
        :return: Page label.
        """
        pass