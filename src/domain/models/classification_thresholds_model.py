"""Threshold configuration for page classification heuristics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationThresholds:
    """Threshold values used by page classification logic.

    :ivar short_line_ratio_min: Minimum ratio of short lines to classify as workflow.
    :ivar avg_words_per_line_max: Maximum average words per line for workflow pages.
    :ivar y_std_gaps_max: Maximum standard deviation for vertical gaps.
    """
    short_line_ratio_min: float = 0.95
    avg_words_per_line_max: float = 3.2
    y_std_gaps_max: float = 0.35