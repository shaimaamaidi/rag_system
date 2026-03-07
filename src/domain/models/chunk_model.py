"""Chunk model definitions for vector store ingestion."""

from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class Chunk:
    """Chunk of text with metadata for retrieval.

    :ivar id: Unique chunk identifier.
    :ivar doc_name: Source document name.
    :ivar paragraph_id: Parent paragraph identifier.
    :ivar title: Section title .
    :ivar target_group: List of target group names.
    :ivar chunk_text: Text content for the chunk.
    :ivar original_text: Original paragraph text.
    :ivar has_table: Whether the chunk includes table data.
    :ivar table_metadata: Table metadata extracted from the chunk.
    :ivar embedding: Optional embedding vector.
    """
    id: str
    doc_name: str
    paragraph_id: str
    title: Optional[str]
    target_group: List[str]
    chunk_text: str
    original_text: str
    has_table: bool
    table_metadata: List[Any] = field(default_factory=list)
    embedding: Optional[List[float]] = field(default=None)