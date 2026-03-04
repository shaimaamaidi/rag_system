import logging
from typing import Any, Optional

from src.domain.services.document_helpers import (
    count_lines, count_sentences, normalize_heading,
    is_article_page, is_workflow_page, remove_preface_line,
    workflow_title, extract_preface_heading, page_table_metadata,
    is_title_page, count_md_tables, filter_metadata_for_segment
)
from src.domain.factories.paragraph_factory import ParagraphFactory
from src.domain.models.page_content_model import PageContent
from src.domain.models.paragraph_model import Paragraph
from src.domain.models.section_heading_model import SectionHeading
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class DocumentSplitter:

    @staticmethod
    def split(name_doc, pages, headings) -> list[Paragraph]:
        logger.info(f"Starting DocumentSplitter for '{name_doc}' with {len(pages)} pages and {len(headings)} headings")
        paragraphs = DocumentSplitter._build_paragraphs(pages, headings, name_doc)
        logger.info(f"DocumentSplitter finished: {len(paragraphs)} paragraphs created")
        return paragraphs

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
        current_is_article:     bool          = False

        pending_headings:       list[str]     = []
        pending_text_parts:     list[str]     = []
        pending_has_table:      bool          = False
        pending_table_metadata: list[Any]     = []

        active_title:    Optional[str] = None
        pending_title:   Optional[str] = None
        pending_is_article: bool       = False

        try:
            events = DocumentSplitter._build_events(pages, headings_by_page)
        except Exception as e:
            logger.error(f"Failed to build events for document '{name_doc}': {e}")
            return paragraphs

        # ── closures ──────────────────────────────────────────────────────

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
            return count_lines(combined) >= 1

        def is_weak_heading(is_article: bool = False) -> bool:
            if is_article or pending_is_article:
                return False
            is_first = (current_heading is None and not current_text_parts)
            if is_first:
                return False
            combined = "\n".join(pending_text_parts)
            return count_sentences(combined) <= 2

        def flush_pending_into_current():
            nonlocal current_text_parts, current_has_table, current_is_article, pending_is_article
            for ph in pending_headings:
                current_text_parts.append(ph)
            current_text_parts.extend(pending_text_parts)
            current_has_table  = current_has_table or pending_has_table
            current_is_article = current_is_article or pending_is_article
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
                paragraphs.append(ParagraphFactory.create(
                    title          = active_title,
                    sub_title      = current_heading,
                    name_doc       = name_doc,
                    text           = text,
                    has_table      = current_has_table,
                    is_article     = current_is_article,
                    table_metadata = current_table_metadata.copy(),
                ))
                logger.info(f"Paragraph created: title='{active_title}', sub_title='{current_heading}', "
                            f"text_length={len(text)} chars, tables={current_has_table}")
                current_heading    = None
                current_has_table  = False
                current_is_article = False
                current_table_metadata.clear()
            else:
                current_has_table  = False
                current_is_article = False
                current_table_metadata.clear()

            current_text_parts.clear()

        def commit_pending_as_new(is_article: bool = False):
            nonlocal current_heading, current_text_parts, current_has_table
            nonlocal current_table_metadata, current_is_article, pending_is_article

            if is_weak_heading(is_article):
                for ph in pending_headings:
                    current_text_parts.append(ph)
                current_text_parts.extend(pending_text_parts)
                current_has_table  = current_has_table or pending_has_table
                current_is_article = current_is_article or pending_is_article
                current_table_metadata.extend(pending_table_metadata)
            else:
                finalize_current()
                new_heading = pending_headings[0] if pending_headings else None
                extra       = pending_headings[1:] if len(pending_headings) > 1 else []
                current_heading        = new_heading
                current_text_parts     = [h for h in extra] + list(pending_text_parts)
                current_has_table      = pending_has_table
                current_is_article     = pending_is_article
                current_table_metadata = list(pending_table_metadata)

            pending_headings.clear()
            pending_text_parts.clear()
            pending_table_metadata.clear()
            pending_is_article = False

        # ── state machine ─────────────────────────────────────────────────

        for event_type, payload in events:

            if event_type == "title_page":
                pending_title = payload

            elif event_type == "pre_heading_page":
                _flush_pending_title()
                page_header, text_chunk, has_tbl, table_metadata = payload
                text = text_chunk.strip()
                paragraphs.append(ParagraphFactory.create_pre_heading(
                    active_title   = active_title,
                    page_header    = page_header,
                    name_doc       = name_doc,
                    text           = text,
                    has_table      = has_tbl,
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
                workflow_title_val, page_text, has_tbl, table_metadata = payload
                if not workflow_title_val:
                    logger.warning(f"Workflow page detected but no title found: page_text='{page_text[:50]}...'")
                    workflow_title_val = "Unknown workflow"
                if pending_headings:
                    if has_enough_content_in_pending():
                        commit_pending_as_new()
                    else:
                        flush_pending_into_current()
                finalize_current()
                text = page_text.strip()
                paragraphs.append(ParagraphFactory.create_workflow(
                    active_title   = active_title,
                    workflow_title = workflow_title_val,
                    name_doc       = name_doc,
                    text           = text,
                    has_table      = has_tbl,
                    table_metadata = table_metadata,
                ))

        # ── end of events ─────────────────────────────────────────────────

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

    @staticmethod
    def _build_events(
        pages: list[PageContent],
        headings_by_page,
    ) -> list[tuple[str, Any]]:
        events: list[tuple[str, Any]] = []

        all_heading_pages = sorted(headings_by_page.keys())
        heading_map = {
            normalize_heading(h.content.strip()): h.content.strip()
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
            is_article = is_article_page(page)

            if is_workflow_page(page):
                try:
                    wf_title_val = workflow_title(page)
                except Exception as e:
                    logger.error(f"Failed to extract workflow title on page {page_num}: {e}")
                    wf_title_val = "Unknown workflow"
                preface_heading = extract_preface_heading(page_text, heading_map)
                heading_value   = preface_heading or wf_title_val
                if preface_heading:
                    page_text = remove_preface_line(page_text, preface_heading)
                events.append(("workflow", (heading_value, page_text, has_tbl, page_table_metadata(page))))
                first_heading_seen = True
                continue

            if is_title_page(page_text):
                events.append(("title_page", page_text.strip()))
                first_heading_seen = True
                continue

            page_headings = sorted(
                headings_by_page.get(page_num, []),
                key=lambda h: h.y_position,
            )

            if not page_headings:
                if not first_heading_seen and (first_heading_page is None or page_num < first_heading_page):
                    page_header = page.header
                    events.append(("pre_heading_page", (page_header, page_text, has_tbl, page_table_metadata(page))))
                else:
                    events.append(("text", (page_text, has_tbl, page_table_metadata(page))))
                continue

            first_heading_seen = True
            remaining_text     = page_text
            meta_pool = list(page_table_metadata(page))

            for h in page_headings:
                h_content = h.content.strip()
                idx       = remaining_text.find(h_content)
                if idx != -1:
                    before = remaining_text[:idx].strip()
                    if before:
                        seg_meta = filter_metadata_for_segment(before, meta_pool)
                        seg_tbl  = bool(seg_meta) or (has_tbl and count_md_tables(before) > 0)
                        events.append(("text", (before, seg_tbl, seg_meta)))
                    events.append(("heading", (h_content, is_article)))
                    remaining_text = remaining_text[idx + len(h_content):].strip()
                else:
                    events.append(("heading", (h_content, is_article)))

            if remaining_text:
                seg_meta = filter_metadata_for_segment(remaining_text, meta_pool)
                seg_tbl  = bool(seg_meta) or (has_tbl and count_md_tables(remaining_text) > 0)
                events.append(("text", (remaining_text, seg_tbl, seg_meta)))

        return events