"""Embedding model definitions."""

from dataclasses import dataclass
from typing import List


@dataclass
class Embedding:
    """Container for an embedding vector.

    :ivar vector: Numerical vector representing semantic meaning.
    """

    vector: List[float]
