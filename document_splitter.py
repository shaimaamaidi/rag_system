"""
DocumentSplitter: Reads a structured JSON document and returns a list of Paragraph objects.

RULES APPLIED:
1. Pages before the first heading → each page becomes its own Paragraph(heading=None)
2. If two successive headings have fewer than 1 non-empty line between them,
   the second heading is merged into the first paragraph's text.
   ⚠ Skipped for pages with content_type == "article"
3. If 3+ successive headings each have < 1 line between them, they all collapse
   into one paragraph under the first heading.
   ⚠ Skipped for pages with content_type == "article"
4. If a heading's associated text has <= 2 sentences AND it is not the first heading,
   it is merged into the preceding paragraph as text instead of starting a new paragraph.
   ⚠ Skipped for pages with content_type == "article"
5. Workflow pages (content_type == "workflow") → new Paragraph with heading = workflow_title
   extracted from the embedded JSON. Any in-progress paragraph is finalized first.
6. A page with 1–4 non-empty lines is considered a "title page". Its content becomes
   the persistent `title` of ALL subsequent paragraphs until a NEW title page is found.
   If two (or more) consecutive title pages appear, only the LAST one becomes the active
   title — the earlier ones are silently discarded (no paragraph is created for them).
   If no title page precedes a paragraph, title is None.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Threshold: pages with at most this many non-empty lines are "title pages"
# ---------------------------------------------------------------------------
TITLE_PAGE_MAX_LINES: int = 4


@dataclass
class Paragraph:
    title: Optional[str]
    sub_title: Optional[str]
    name_doc: str
    text: str
    len_text: int
    has_table: bool
    is_article: bool = False
    table_metadata: list[Any] = field(default_factory=list)

    def __post_init__(self):
        self.len_text = len(self.text)

    def _recalc(self):
        self.len_text = len(self.text)


@dataclass
class PageContent:
    page_number: int
    content_type: str
    header: str
    text: str
    has_table: bool
    tables_metadata: list


@dataclass
class SectionHeading:
    content:     str
    page_number: int
    y_position:  float
    x_position:  float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_lines(text: str) -> int:
    """Count non-empty lines in a text block."""
    return sum(1 for line in text.splitlines() if line.strip())


def _count_sentences(text: str) -> int:
    """Rough sentence count (split on . ! ? ؟)."""
    parts = re.split(r'[.!?؟]+', text)
    return sum(1 for p in parts if p.strip())


_FOOTER_PATTERNS: list[re.Pattern] = [
    re.compile(r'www\.', re.IGNORECASE),                       # URLs
    re.compile(r'https?://', re.IGNORECASE),                   # liens http
    re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', re.IGNORECASE), # emails
    re.compile(r'لمزيد من المعلومات'),                         # "pour plus d'infos"
    re.compile(r'للتواصل'),                                    # "pour contact"
    re.compile(r'الرجاء التواصل'),                             # "veuillez contacter"
]

def _is_footer_page(text: str) -> bool:
    """Return True if the page looks like a contact/footer page (should not be a title)."""
    return any(p.search(text) for p in _FOOTER_PATTERNS)


def _is_title_page(text: str) -> bool:
    """Return True if the page qualifies as a title page (1–4 non-empty lines)."""
    n = _count_lines(text)
    if not (1 <= n <= TITLE_PAGE_MAX_LINES):
        return False
    if _is_footer_page(text):
        return False
    return True


def _page_has_table(page: dict) -> bool:
    return bool(page.get("has_table", False))


def _page_text(page: dict) -> str:
    return (page.get("text") or "").strip()


def _is_workflow_page(page: PageContent) -> bool:
    return page.content_type.lower() == "workflow"


def _is_article_page(page: PageContent) -> bool:
    return page.content_type.lower() == "article"


def _workflow_title(page: PageContent) -> Optional[str]:
    text = page.text or ""

    # Cas 1 : JSON déjà parsé/propre
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "workflow_title" in data:
            return data["workflow_title"]
    except Exception:
        pass

    # Cas 2 : chaîne doublement échappée
    try:
        inner = text.strip()
        if inner.startswith('"') and inner.endswith('"'):
            inner = inner[1:-1]
        inner = inner.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        data = json.loads(inner)
        if isinstance(data, dict) and "workflow_title" in data:
            return data["workflow_title"]
    except Exception:
        pass

    # Cas 3 : fallback regex
    match = re.search(r'workflow_title\\?"?\s*:\\?"?\s*\\?"([^"\\]+)', text)
    if match:
        return match.group(1).strip()

    return None


def _page_table_metadata(page: PageContent) -> list[Any]:
    return page.tables_metadata or []


def _normalize_heading(text: str) -> str:
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


def _extract_preface_heading(text: str, heading_map: dict[str, str]) -> Optional[str]:
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
    normalized = _normalize_heading(cleaned)
    if normalized in heading_map:
        return heading_map[normalized]
    return None


def _remove_preface_line(text: str, preface_line: str) -> str:
    if not text or not preface_line:
        return text

    lines  = text.splitlines()
    target = _normalize_heading(preface_line.strip())
    for idx, line in enumerate(lines):
        line_clean = line.lstrip("# ").strip()
        if _normalize_heading(line_clean) == target:
            return "\n".join(lines[:idx] + lines[idx + 1:]).strip()
    return text


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DocumentSplitter:

    @staticmethod
    def split(name_doc, pages, headings) -> list[Paragraph]:
        return DocumentSplitter._build_paragraphs(pages, headings, name_doc)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    @staticmethod
    def _build_paragraphs(
        pages: list[PageContent],
        headings: list[SectionHeading],
        name_doc: str,
    ) -> list[Paragraph]:

        headings_by_page: dict[int, list[SectionHeading]] = {}
        for h in headings:
            headings_by_page.setdefault(h.page_number, []).append(h)

        paragraphs: list[Paragraph] = []

        current_heading:        Optional[str] = None
        current_text_parts:     list[str]     = []
        current_has_table:      bool          = False
        current_table_metadata: list[Any]     = []
        current_is_article:     bool          = False  # ← AJOUT

        pending_headings:       list[str]     = []
        pending_text_parts:     list[str]     = []
        pending_has_table:      bool          = False
        pending_table_metadata: list[Any]     = []

        # ── Rule 6 : persistent title ─────────────────────────────────────
        active_title:        Optional[str] = None
        pending_title:       Optional[str] = None

        # ── Tracks whether the pending heading came from an article page ──
        pending_is_article: bool = False

        events = DocumentSplitter._build_events(pages, headings_by_page)

        # ----------------------------------------------------------------
        # Inner helpers (closures)
        # ----------------------------------------------------------------

        def _flush_pending_title():
            nonlocal active_title, pending_title
            if pending_title is not None:
                if pending_headings:
                    if has_enough_content_in_pending():
                        commit_pending_as_new()
                    else:
                        flush_pending_into_current()
                finalize_current()
                active_title  = pending_title
                pending_title = None

        def has_enough_content_in_pending(is_article: bool = False) -> bool:
            if is_article or pending_is_article:
                return True
            combined = "\n".join(pending_text_parts)
            return _count_lines(combined) >= 1

        def is_weak_heading(is_article: bool = False) -> bool:
            if is_article or pending_is_article:
                return False
            is_first = (current_heading is None and not current_text_parts)
            if is_first:
                return False
            combined = "\n".join(pending_text_parts)
            return _count_sentences(combined) <= 2

        def flush_pending_into_current():
            nonlocal current_text_parts, current_has_table, current_is_article, pending_is_article
            for ph in pending_headings:
                current_text_parts.append(ph)
            current_text_parts.extend(pending_text_parts)
            current_has_table  = current_has_table or pending_has_table
            current_is_article = current_is_article or pending_is_article  # ← AJOUT
            current_table_metadata.extend(pending_table_metadata)
            pending_headings.clear()
            pending_text_parts.clear()
            pending_table_metadata.clear()
            pending_is_article = False

        def finalize_current():
            nonlocal current_heading, current_text_parts, current_has_table
            nonlocal current_table_metadata, current_is_article

            text = "\n".join(current_text_parts).strip()

            if text:
                paragraphs.append(Paragraph(
                    title          = active_title,
                    sub_title      = current_heading,
                    name_doc       = name_doc,
                    text           = text,
                    len_text       = len(text),
                    has_table      = current_has_table,
                    is_article     = current_is_article,   # ← AJOUT
                    table_metadata = current_table_metadata.copy(),
                ))
                current_heading    = None
                current_has_table  = False
                current_is_article = False                 # ← RESET
                current_table_metadata = []
            else:
                current_has_table  = False
                current_is_article = False                 # ← RESET
                current_table_metadata = []

            current_text_parts = []

        def commit_pending_as_new(is_article: bool = False):
            nonlocal current_heading, current_text_parts, current_has_table
            nonlocal current_table_metadata, current_is_article, pending_is_article

            if is_weak_heading(is_article):
                for ph in pending_headings:
                    current_text_parts.append(ph)
                current_text_parts.extend(pending_text_parts)
                current_has_table  = current_has_table or pending_has_table
                current_is_article = current_is_article or pending_is_article  # ← AJOUT
                current_table_metadata.extend(pending_table_metadata)
            else:
                finalize_current()
                new_heading = pending_headings[0] if pending_headings else None
                extra       = pending_headings[1:] if len(pending_headings) > 1 else []
                current_heading        = new_heading
                current_text_parts     = [h for h in extra] + list(pending_text_parts)
                current_has_table      = pending_has_table
                current_is_article     = pending_is_article                    # ← AJOUT
                current_table_metadata = list(pending_table_metadata)

            pending_headings.clear()
            pending_text_parts.clear()
            pending_table_metadata.clear()
            pending_is_article = False

        # ----------------------------------------------------------------
        # State machine over events
        # ----------------------------------------------------------------

        for event_type, payload in events:

            # ── Rule 6 : title page ───────────────────────────────────────
            if event_type == "title_page":
                pending_title = payload

            elif event_type == "pre_heading_page":
                _flush_pending_title()
                page_header, text_chunk, has_tbl, table_metadata = payload
                text = text_chunk.strip()
                paragraphs.append(Paragraph(
                    title          = active_title,
                    sub_title      = page_header,
                    name_doc       = name_doc,
                    text           = text,
                    len_text       = len(text),
                    has_table      = has_tbl,
                    is_article     = False,   # pre-heading pages are never articles
                    table_metadata = table_metadata,
                ))

            elif event_type == "text":
                _flush_pending_title()
                text_chunk, has_tbl, table_meta = payload
                if pending_headings:
                    pending_text_parts.append(text_chunk)
                    pending_has_table = pending_has_table or has_tbl
                    pending_table_metadata.extend(table_meta)
                else:
                    current_text_parts.append(text_chunk)
                    current_has_table = current_has_table or has_tbl
                    current_table_metadata.extend(table_meta)

            elif event_type == "heading":
                _flush_pending_title()
                heading_content, is_article = payload

                if pending_headings:
                    if has_enough_content_in_pending(is_article):
                        commit_pending_as_new(is_article)
                        pending_headings.append(heading_content)
                        pending_is_article = is_article
                    else:
                        pending_headings.append(heading_content)
                        if is_article:
                            pending_is_article = True
                else:
                    pending_headings.append(heading_content)
                    pending_text_parts.clear()
                    pending_table_metadata.clear()
                    pending_has_table  = False
                    pending_is_article = is_article

            elif event_type == "workflow":
                _flush_pending_title()
                workflow_title, page_text, has_tbl, table_metadata = payload
                if pending_headings:
                    if has_enough_content_in_pending():
                        commit_pending_as_new()
                    else:
                        flush_pending_into_current()
                finalize_current()
                text = page_text.strip()
                paragraphs.append(Paragraph(
                    title          = active_title,
                    sub_title      = workflow_title,
                    name_doc       = name_doc,
                    text           = text,
                    len_text       = len(text),
                    has_table      = has_tbl,
                    is_article     = False,   # workflow pages are never articles
                    table_metadata = table_metadata,
                ))

        # ----------------------------------------------------------------
        # End of events
        # ----------------------------------------------------------------

        if pending_title is not None:
            active_title  = pending_title
            pending_title = None

        if pending_headings:
            if not has_enough_content_in_pending():
                flush_pending_into_current()
            else:
                commit_pending_as_new()

        finalize_current()

        return paragraphs

    # ------------------------------------------------------------------
    # Event builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_events(
        pages: list[PageContent],
        headings_by_page,
    ) -> list[tuple[str, Any]]:
        """
        Convert pages + headings into a flat list of events:
          ("title_page",        page_text_content)                     ← Rule 6
          ("pre_heading_page",  (header, text, has_table, table_meta))
          ("heading",           (heading_content, is_article: bool))
          ("text",              (text, has_table, table_meta))
          ("workflow",          (title, text, has_table, table_meta))
        """
        events: list[tuple[str, Any]] = []

        all_heading_pages = sorted(headings_by_page.keys())
        heading_map = {
            _normalize_heading(h.content.strip()): h.content.strip()
            for hs in headings_by_page.values()
            for h in hs
            if h.content
        }
        first_heading_page = all_heading_pages[0] if all_heading_pages else None
        first_heading_seen = False

        for page in pages:
            page_num   = page.page_number
            page_text  = page.text
            has_tbl    = page.has_table
            is_article = _is_article_page(page)

            # ---- Workflow page ----
            if _is_workflow_page(page):
                wf_title        = _workflow_title(page)
                preface_heading = _extract_preface_heading(page_text, heading_map)
                heading_value   = preface_heading or wf_title
                if preface_heading:
                    page_text = _remove_preface_line(page_text, preface_heading)
                events.append(("workflow", (heading_value, page_text, has_tbl, _page_table_metadata(page))))
                first_heading_seen = True
                continue

            # ---- Rule 6 : title page (1–4 non-empty lines) ----
            if _is_title_page(page_text):
                events.append(("title_page", page_text.strip()))
                first_heading_seen = True
                continue

            # ---- Check headings on this page ----
            page_headings = sorted(
                headings_by_page.get(page_num, []),
                key=lambda h: h.y_position,
            )

            if not page_headings:
                if not first_heading_seen and (first_heading_page is None or page_num < first_heading_page):
                    page_header = page.header
                    events.append(("pre_heading_page", (page_header, page_text, has_tbl, _page_table_metadata(page))))
                else:
                    events.append(("text", (page_text, has_tbl, _page_table_metadata(page))))
                continue

            # ---- Page has headings: interleave text and heading events ----
            first_heading_seen     = True
            remaining_text         = page_text
            page_has_table_emitted = False

            for h in page_headings:
                h_content = h.content.strip()
                idx       = remaining_text.find(h_content)
                if idx != -1:
                    before = remaining_text[:idx].strip()
                    if before:
                        events.append(("text", (before, has_tbl and not page_has_table_emitted, _page_table_metadata(page))))
                        page_has_table_emitted = True
                    events.append(("heading", (h_content, is_article)))
                    remaining_text = remaining_text[idx + len(h_content):].strip()
                else:
                    events.append(("heading", (h_content, is_article)))

            if remaining_text:
                events.append(("text", (remaining_text, has_tbl and not page_has_table_emitted, _page_table_metadata(page))))

        return events


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_paragraphs_to_json(paragraphs: list[Paragraph], output_path: str | Path) -> None:

    data = []
    for p in paragraphs:
        data.append({
            "title":          p.title,
            "heading":        p.sub_title,
            "name_doc":       p.name_doc,
            "text":           p.text,
            "len_text":       p.len_text,
            "has_table":      p.has_table,
            "is_article":     p.is_article,
            "table_metadata": p.table_metadata,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Paragraphs saved to: {output_path}")