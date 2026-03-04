"""Page classification heuristics for workflow detection."""

import logging
import statistics
from azure.ai.documentintelligence.models import DocumentPage

from src.domain.models.classification_thresholds_model import ClassificationThresholds
from src.domain.ports.input.page_classifier_port import PageClassifierPort, PageLabel
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class PageClassifier(PageClassifierPort):
    """Classify pages as workflow or text based on layout heuristics."""

    def __init__(self):
        """Initialize the classifier with default thresholds."""
        self.thresholds = ClassificationThresholds()
        logger.info("PageClassifier initialized with thresholds: %s", self.thresholds)

    def classify(self, page: DocumentPage, has_keyword: bool) -> PageLabel:
        """Classify a page into a label.

        :param page: Azure Document Intelligence page.
        :param has_keyword: Whether workflow keywords were detected.
        :return: Page label ("workflow" or "text").
        """
        metrics = PageClassifier._compute_metrics(page)
        slr = metrics.get("short_line_ratio")
        awpl = metrics.get("avg_words_per_line")
        ystd = metrics.get("y_std_gaps")
        t = self.thresholds

        logger.info(
            "Classifying page %s: metrics=%s, has_keyword=%s",
            getattr(page, "page_number", None), metrics, has_keyword
        )

        if slr is None and awpl is None and ystd is None:
            logger.info("No metrics available, defaulting to 'text'")
            return "text"

        if (
            slr is not None and slr >= t.short_line_ratio_min and
            awpl is not None and awpl <= t.avg_words_per_line_max and
            ystd is not None and ystd <= t.y_std_gaps_max
        ):
            logger.info("Metrics within thresholds, classified as 'workflow'")
            return "workflow"

        if has_keyword:
            logger.info("Keyword detected, classified as 'workflow'")
            return "workflow"

        logger.info("Defaulting to 'text'")
        return "text"

    @staticmethod
    def _compute_metrics(page) -> dict:
        """Compute layout metrics used for classification.

        :param page: Azure Document Intelligence page.
        :return: Metric dictionary with ratios and spacing values.
        """
        lines = page.lines or []

        if not lines:
            return {
                "short_line_ratio": None,
                "avg_words_per_line": None,
                "y_std_gaps": None,
            }

        word_counts = [len(l.content.split()) for l in lines]
        total = len(word_counts)

        short_line_ratio = sum(1 for w in word_counts if w <= 5) / total
        avg_words_per_line = sum(word_counts) / total

        y_centers = sorted([
            sum(l.polygon[i] for i in range(1, len(l.polygon), 2)) / (len(l.polygon) // 2)
            for l in lines if l.polygon
        ])

        gaps = [y_centers[i + 1] - y_centers[i] for i in range(len(y_centers) - 1)]
        y_std_gaps = statistics.stdev(gaps) if len(gaps) > 1 else None

        metrics = {
            "short_line_ratio": round(short_line_ratio, 4),
            "avg_words_per_line": round(avg_words_per_line, 4),
            "y_std_gaps": round(y_std_gaps, 4) if y_std_gaps is not None else None,
        }

        logger.debug("Computed metrics for page %s: %s", getattr(page, "page_number", None), metrics)
        return metrics

    @staticmethod
    def _has_key_word_in_header_table(page, result) -> bool:
        """Return True if a header table cell contains a workflow keyword.

        :param page: Azure Document Intelligence page.
        :param result: Document Intelligence analysis result.
        :return: True if a keyword is found in a table header.
        """
        workflow_keywords = ["رموز"]

        for table in result.tables or []:
            for region in table.bounding_regions:
                if region.page_number == page.page_number:
                    first_row_cells = [
                        cell.content for cell in table.cells
                        if cell.row_index == 0
                    ]
                    for cell_content in first_row_cells:
                        cell_text = cell_content.replace(" ", "").strip()
                        for kw in workflow_keywords:
                            if kw in cell_text:
                                logger.info(
                                    "Keyword '%s' found in table header on page %s",
                                    kw, page.page_number
                                )
                                return True

        logger.debug("No workflow keyword found in table header for page %s", page.page_number)
        return False