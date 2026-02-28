from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationThresholds:
    short_line_ratio_min: float = 0.95
    avg_words_per_line_max: float = 3.2
    y_std_gaps_max: float = 0.35