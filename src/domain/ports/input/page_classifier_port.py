from typing import Protocol, Literal

from azure.ai.documentintelligence.models import DocumentPage

PageLabel = Literal["workflow", "text"]

class PageClassifierPort(Protocol):
    """Port abstrait pour classifier une page."""

    def classify(self, page: DocumentPage, has_keyword: bool) -> PageLabel:
        pass