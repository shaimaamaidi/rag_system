from pydantic import BaseModel
from typing import List, Literal


class ChunkClassification(BaseModel):
    """Classification result for a single chunk."""
    chunk_index: int
    classification: Literal["VERY HIGH", "HIGH", "MEDIUM", "LOW"]


class ChunkClassificationResponse(BaseModel):
    """Response returned by the LLM for chunk relevance classification."""
    results: List[ChunkClassification]