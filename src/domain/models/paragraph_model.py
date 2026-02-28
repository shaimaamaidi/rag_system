from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Paragraph:
    title: Optional[str]
    sub_title: Optional[str]
    name_doc: str
    text: str
    len_text: int
    has_table: bool
    is_article: bool = False
    table_metadata: list[Any] = field(default_factory=list)

    def __post_init__(self):
        self.len_text = len(self.text)

    def _recalc(self):
        self.len_text = len(self.text)