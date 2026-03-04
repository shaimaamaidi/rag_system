"""Paragraph model for structured document text."""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Paragraph:
    """Paragraph data with section metadata and table flags.

    :ivar title: Section title if available.
    :ivar sub_title: Subsection title if available.
    :ivar name_doc: Source document name.
    :ivar text: Full paragraph text.
    :ivar len_text: Length of the paragraph text (computed).
    :ivar has_table: Whether the paragraph includes a table.
    :ivar is_article: Whether the paragraph is treated as an article.
    :ivar table_metadata: Table metadata extracted from the paragraph.
    """
    title: Optional[str]
    sub_title: Optional[str]
    name_doc: str
    text: str
    len_text: int
    has_table: bool
    is_article: bool = False
    table_metadata: list[Any] = field(default_factory=list)

    def __post_init__(self):
        """Compute derived fields after initialization."""
        self.len_text = len(self.text)

    def _recalc(self):
        """Recompute derived fields after text updates."""
        self.len_text = len(self.text)