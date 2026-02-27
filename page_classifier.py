import statistics
from dataclasses import dataclass
from typing import Literal

PageLabel = Literal["workflow", "text"]


@dataclass(frozen=True)
class ClassificationThresholds:
    short_line_ratio_min: float = 0.95
    avg_words_per_line_max: float = 3.2
    y_std_gaps_max: float = 0.35


class PageClassifier:

    def __init__(self):
        self.thresholds = ClassificationThresholds()

    def classify(self, page, hasKeyWord) -> PageLabel:
        metrics = PageClassifier._compute_metrics(page)
        slr = metrics.get("short_line_ratio")
        awpl = metrics.get("avg_words_per_line")
        ystd = metrics.get("y_std_gaps")
        t = self.thresholds

        if slr is None and awpl is None and ystd is None:
            return "text"

        if (
            slr is not None and slr >= t.short_line_ratio_min and
            awpl is not None and awpl <= t.avg_words_per_line_max and
            ystd is not None and ystd <= t.y_std_gaps_max
        ):
            return "workflow"

        if hasKeyWord:
            return "workflow"

        return "text"

    @staticmethod
    def _compute_metrics(page) -> dict:
        lines = page.lines or []

        if not lines:
            return {
                "short_line_ratio": None,
                "avg_words_per_line": None,
                "y_std_gaps": None
            }

        word_counts = [len(l.content.split()) for l in lines]
        total = len(word_counts)

        short_line_ratio = sum(1 for w in word_counts if w <= 5) / total
        avg_words_per_line = sum(word_counts) / total

        y_centers = sorted(
            [
                sum(l.polygon[i] for i in range(1, len(l.polygon), 2)) / (len(l.polygon) // 2)
                for l in lines if l.polygon
            ]
        )

        gaps = [y_centers[i + 1] - y_centers[i] for i in range(len(y_centers) - 1)]
        y_std_gaps = statistics.stdev(gaps) if len(gaps) > 1 else None

        return {
            "short_line_ratio": round(short_line_ratio, 4),
            "avg_words_per_line": round(avg_words_per_line, 4),
            "y_std_gaps": round(y_std_gaps, 4) if y_std_gaps is not None else None,
        }