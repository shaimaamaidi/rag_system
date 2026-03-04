"""Model for normalized page content."""

from dataclasses import dataclass


@dataclass
class PageContent:
    """Container for page-level content and metadata.

    :ivar page_number: Page number in the source document.
    :ivar content_type: Page classification label.
    :ivar header: Header text extracted from the page.
    :ivar text: Main page text content.
    :ivar has_table: Whether the page contains tables.
    :ivar tables_metadata: Table metadata list.
    """
    page_number: int
    content_type: str
    header: str
    text: str
    has_table: bool
    tables_metadata: list