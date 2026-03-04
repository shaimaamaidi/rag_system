import logging
import json
import re
from typing import Any, Optional
from src.infrastructure.config.logger import setup_logger
from src.domain.models.page_content_model import PageContent

setup_logger()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TITLE_PAGE_MAX_LINES: int = 4


def count_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def count_sentences(text: str) -> int:
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
    return any(p.search(text) for p in FOOTER_PATTERNS)


def is_title_page(text: str) -> bool:
    n = count_lines(text)
    if not (1 <= n <= TITLE_PAGE_MAX_LINES):
        return False
    if is_footer_page(text):
        return False
    return True


def is_workflow_page(page: PageContent) -> bool:
    result = page.content_type.lower() == "workflow"
    if result:
        logger.info("Page %s: detected as workflow page", page.page_number)
    return result


def is_article_page(page: PageContent) -> bool:
    result = page.content_type.lower() == "article"
    if result:
        logger.info("Page %s: detected as article page", page.page_number)
    return result


def workflow_title(page: PageContent) -> Optional[str]:
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
    return page.tables_metadata or []


def normalize_heading(text: str) -> str:
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
    """Compte le nombre de tables Markdown dans un segment de texte."""
    if not text:
        return 0
    matches = re.findall(r"(?:\|.*\|[ \t]*(?:\n|$))+", text)
    return len(matches)


def filter_metadata_for_segment(text: str, all_metadata: list[Any]) -> list[Any]:
    """
    Retourne les entrées de table_metadata qui correspondent aux tables
    réellement présentes dans ce segment de texte.

    Stratégie :
    - On compte le nombre de tables Markdown dans le segment.
    - On retourne autant d'entrées depuis all_metadata (dans l'ordre).
    - Les entrées déjà consommées sont retirées de all_metadata (mutation in-place).
    """
    n = _count_md_tables(text)
    if n == 0 or not all_metadata:
        return []
    take = min(n, len(all_metadata))
    result = all_metadata[:take]
    del all_metadata[:take]
    return result