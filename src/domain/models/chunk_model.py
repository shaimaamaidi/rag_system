from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class Chunk:
    id: str
    doc_name: str
    paragraph_id: str
    title: Optional[str]
    sub_title: Optional[str]
    target_group: str
    chunk_text: str
    original_text: str
    has_table: bool
    table_metadata: List[Any] = field(default_factory=list)
    embedding: Optional[List[float]] = field(default=None)