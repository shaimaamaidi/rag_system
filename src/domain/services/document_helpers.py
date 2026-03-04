"""Helper functions for document parsing and classification."""

import logging
import json
import re
from typing import Any, Optional
from src.domain.models.page_content_model import PageContent
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

TITLE_PAGE_MAX_LINES: int = 4


def count_lines(text: str) -> int:
    """Count non-empty lines in text.

    :param text: Input text.
    :return: Number of non-empty lines.
    """
    return sum(1 for line in text.splitlines() if line.strip())


def count_sentences(text: str) -> int:
    """Count sentences in text using punctuation delimiters.

    :param text: Input text.
    :return: Estimated sentence count.
    """
    parts = re.split(r'[.!?؟]+', text)
    return sum(1 for p in parts if p.strip())


FOOTER_PATTERNS: list[re.Pattern] = [
    re.compile(r'www\.', re.IGNORECASE),
    re.compile(r'https?://', re.IGNORECASE),
    re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', re.IGNORECASE),
    re.compile(r'لمزيد من المعلومات'),
    re.compile(r'للتواصل'),
    re.compile(r'الرجاء التواصل'),
]


def is_footer_page(text: str) -> bool:
    """Determine whether text matches common footer patterns.

    :param text: Page text.
    :return: True if footer patterns are detected.
    """
    return any(p.search(text) for p in FOOTER_PATTERNS)


def is_title_page(text: str) -> bool:
    """Determine whether text looks like a title page.

    :param text: Page text.
    :return: True if the text matches the title page heuristic.
    """
    n = count_lines(text)
    if not (1 <= n <= TITLE_PAGE_MAX_LINES):
        return False
    if is_footer_page(text):
        return False
    return True


def is_workflow_page(page: PageContent) -> bool:
    """Check whether a page is marked as a workflow.

    :param page: Page content model.
    :return: True if the page is a workflow page.
    """
    result = page.content_type.lower() == "workflow"
    if result:
        logger.info("Page %s: detected as workflow page", page.page_number)
    return result


def is_article_page(page: PageContent) -> bool:
    """Check whether a page is marked as an article.

    :param page: Page content model.
    :return: True if the page is an article page.
    """
    result = page.content_type.lower() == "article"
    if result:
        logger.info("Page %s: detected as article page", page.page_number)
    return result


def workflow_title(page: PageContent) -> Optional[str]:
    """Extract a workflow title from a page if present.

    :param page: Page content model.
    :return: Workflow title or None if not found.
    """
    text = page.text or ""
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "workflow_title" in data:
            logger.info("Page %s: workflow_title found via direct JSON", page.page_number)
            return data["workflow_title"]
    except Exception:
        pass
    try:
        inner = text.strip()
        if inner.startswith('"') and inner.endswith('"'):
            inner = inner[1:-1]
        inner = inner.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        data = json.loads(inner)
        if isinstance(data, dict) and "workflow_title" in data:
            logger.info("Page %s: workflow_title found via inner JSON", page.page_number)
            return data["workflow_title"]
    except Exception:
        pass
    match = re.search(r'workflow_title\\?"?\s*:\\?"?\s*\\?"([^"\\]+)', text)
    if match:
        logger.info("Page %s: workflow_title found via regex", page.page_number)
        return match.group(1).strip()

    logger.info("Page %s: no workflow_title found", page.page_number)
    return None


def page_table_metadata(page: PageContent) -> list[Any]:
    """Return table metadata for a page.

    :param page: Page content model.
    :return: Table metadata list.
    """
    return page.tables_metadata or []


def normalize_heading(text: str) -> str:
    """Normalize heading text for matching.

    :param text: Heading text.
    :return: Normalized heading text.
    """
    if not text:
        return ""
    arabic_indic   = "٠١٢٣٤٥٦٧٨٩"
    eastern_arabic = "۰۱۲۳۴۵۶۷۸۹"
    for idx, d in enumerate(arabic_indic):
        text = text.replace(d, str(idx))
    for idx, d in enumerate(eastern_arabic):
        text = text.replace(d, str(idx))
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_preface_heading(text: str, heading_map: dict[str, str]) -> Optional[str]:
    """Extract a preface heading from page text if present.

    :param text: Page text.
    :param heading_map: Mapping of normalized to original headings.
    :return: Extracted heading or None.
    """
    if not text:
        return None
    candidate = ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if line.startswith("{") or line.startswith('"'):
            break
        candidate = line
    if not candidate:
        return None
    cleaned    = candidate.lstrip("# ").strip()
    normalized = normalize_heading(cleaned)
    if normalized in heading_map:
        logger.info(
            "Preface heading extracted: '%s' -> '%s'",
            normalized,
            heading_map[normalized],
        )
        return heading_map[normalized]
    return None


def remove_preface_line(text: str, preface_line: str) -> str:
    """Remove a preface line from text if present.

    :param text: Full page text.
    :param preface_line: Preface line to remove.
    :return: Text with the preface line removed when found.
    """
    if not text or not preface_line:
        return text
    lines  = text.splitlines()
    target = normalize_heading(preface_line.strip())
    for idx, line in enumerate(lines):
        line_clean = line.lstrip("# ").strip()
        if normalize_heading(line_clean) == target:
            logger.info("Removing preface line: '%s'", line_clean)
            return "\n".join(lines[:idx] + lines[idx + 1:]).strip()
    return text

def count_md_tables(text: str) -> int:
    """Count Markdown tables in a text segment.

    :param text: Input text segment.
    :return: Number of Markdown tables detected.
    """
    if not text:
        return 0
    matches = re.findall(r"(?:\|.*\|[ \t]*(?:\n|$))+", text)
    return len(matches)


def filter_metadata_for_segment(text: str, all_metadata: list[Any]) -> list[Any]:
    """Filter table metadata entries for a text segment.

    :param text: Text segment to analyze.
    :param all_metadata: Mutable list of remaining metadata entries.
    :return: Matching metadata entries for the segment.
    """
    n = count_md_tables(text)
    if n == 0 or not all_metadata:
        return []
    take = min(n, len(all_metadata))
    result = all_metadata[:take]
    del all_metadata[:take]
    return result