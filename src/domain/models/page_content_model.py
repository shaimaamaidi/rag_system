from dataclasses import dataclass


@dataclass
class PageContent:
    page_number: int
    content_type: str
    header: str
    text: str
    has_table: bool
    tables_metadata: list