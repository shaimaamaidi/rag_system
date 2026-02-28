"""
Module containing the Embedding dataclass.
Represents a vector embedding for a piece of text or a document.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Embedding:
    """
    Represents an embedding vector for a piece of text or a document.

    Attributes:
        vector (List[float]): Numerical vector representing the semantic embedding.
    """

    vector: List[float]
