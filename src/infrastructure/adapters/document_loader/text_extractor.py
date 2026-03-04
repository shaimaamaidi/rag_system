"""Extract text and table metadata from Document Intelligence results."""

import logging
from typing import Set, Optional
from azure.ai.documentintelligence.models import ParagraphRole

from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class TextExtractor:
    """Utilities for extracting page text and table metadata."""

    @staticmethod
    def extract_text_page(page, az_result, header_contents: Set[str]) -> dict:
        """Extract full text and table metadata for a page.

        :param page: Document Intelligence page object.
        :param az_result: Analysis result containing tables and paragraphs.
        :param header_contents: Header text to exclude.
        :return: Parsed content with text and table metadata.
        """
        logger.info("Started extracting page %s", page.page_number)

        page_num = page.page_number

        page_tables = []
        for table_idx, table in enumerate(az_result.tables):
            for region in table.bounding_regions:
                if region.page_number == page_num and region.polygon:
                    poly = region.polygon
                    # Support both object format (.x/.y) and flat float list (x0,y0,x1,y1,...)
                    if hasattr(poly[0], 'x'):
                        xs = [p.x for p in poly]
                        ys = [p.y for p in poly]
                    else:
                        xs = [poly[i] for i in range(0, len(poly), 2)]
                        ys = [poly[i] for i in range(1, len(poly), 2)]

                    y_top = min(ys)
                    y_bot = max(ys)
                    x_min = min(xs)
                    x_max = max(xs)

                    page_tables.append({
                        "table_idx": table_idx,
                        "table": table,
                        "y_top": y_top,
                        "bbox": (x_min, x_max, y_top, y_bot),
                    })
                    break

        has_table = bool(page_tables)
        logger.info("Page %s: %d table(s) detected", page_num, len(page_tables))
        table_boxes = [t["bbox"] for t in page_tables]

        tables_metadata = [
            {
                "table_index": t["table_idx"],
                "row_count": t["table"].row_count,
                "col_count": t["table"].column_count,
                "y_position": round(t["y_top"], 4),
            }
            for t in page_tables
        ]

        header_y_max = TextExtractor._get_header_y_max(page.page_number, az_result)
        if header_y_max is not None:
            header_y_max += 0.10

        header_tokens: Set[str] = set()
        for hc in header_contents:
            for tok in hc.replace("/", " ").replace("|", " ").split():
                tok = tok.strip()
                if len(tok) >= 4:
                    header_tokens.add(tok)

        page_number_contents: Set[str] = set()
        for para in (az_result.paragraphs or []):
            role_str = str(getattr(para, "role", "")).upper()
            if "PAGE_NUMBER" in role_str or "PAGENUMBER" in role_str:
                for region in (para.bounding_regions or []):
                    if region.page_number == page.page_number:
                        page_number_contents.add(para.content.strip())

        def _is_header_fragment(line_content: str) -> bool:
            """Check whether a line is part of the header fragment.

            :param line_content: Line text to evaluate.
            :return: True if the line matches header tokens.
            """
            if not line_content:
                return False
            line_tokens = [
                t.strip()
                for t in line_content.replace("/", " ").replace("|", " ").split()
                if len(t.strip()) >= 4
            ]
            if not line_tokens:
                return False
            return all(tok in header_tokens for tok in line_tokens)

        segments = []
        for line in (page.lines or []):
            line_content = line.content.strip()
            line_y = TextExtractor._line_y_center(line)

            if line_content in page_number_contents:
                continue
            if header_y_max is not None and line_y <= header_y_max:
                continue
            if line_content in header_contents:
                continue
            if any(line_content in hc or hc in line_content for hc in header_contents):
                continue
            if header_contents and _is_header_fragment(line_content):
                continue
            if TextExtractor._line_in_table(line, table_boxes):
                continue

            segments.append((line_y, line.content))

        for t in page_tables:
            table_str = TextExtractor._table_to_markdown(t["table"])
            segments.append((t["y_top"], table_str))

        segments.sort(key=lambda s: s[0])
        text = "\n\n".join(c for _, c in segments if c.strip())
        logger.info("Page %s: extraction completed with %d segments", page_num, len(segments))

        return {
            "type": "text",
            "text": text,
            "has_table": has_table,
            "tables_metadata": tables_metadata,
        }

    @staticmethod
    def _get_header_y_max(page_number: int, az_result) -> Optional[float]:
        """Find the maximum Y coordinate for header content.

        :param page_number: Page number to inspect.
        :param az_result: Analysis result containing paragraphs.
        :return: Maximum header Y coordinate, if any.
        """
        page_paragraphs = []
        for para in (az_result.paragraphs or []):
            if not para.bounding_regions:
                continue
            region = para.bounding_regions[0]
            if region.page_number != page_number:
                continue
            poly = region.polygon or []
            if not poly:
                continue
            if hasattr(poly[0], 'y'):
                y_top = poly[0].y
                y_bot = max(p.y for p in poly)
            else:
                y_top = poly[1]
                y_bot = max(poly[i] for i in range(1, len(poly), 2))
            page_paragraphs.append((y_top, y_bot, para))

        page_paragraphs.sort(key=lambda t: t[0])
        last_header_y_bot = None
        for _, y_bot, para in page_paragraphs:
            if para.role == ParagraphRole.PAGE_HEADER:
                last_header_y_bot = y_bot
        return last_header_y_bot

    @staticmethod
    def _line_y_center(line) -> float:
        """Compute the vertical center of a line polygon.

        :param line: Line object with polygon coordinates.
        :return: Center Y coordinate.
        """
        if not line.polygon:
            return 0.0
        y_coords = [line.polygon[i] for i in range(1, len(line.polygon), 2)]
        return sum(y_coords) / len(y_coords)

    @staticmethod
    def _line_in_table(line, boxes: list) -> bool:
        """Check whether a line intersects any table bounding boxes.

        :param line: Line object with polygon coordinates.
        :param boxes: Table bounding boxes.
        :return: True if the line is inside any table box.
        """
        if not line.polygon or not boxes:
            return False
        x_coords = [line.polygon[i] for i in range(0, len(line.polygon), 2)]
        y_coords = [line.polygon[i] for i in range(1, len(line.polygon), 2)]
        lx = sum(x_coords) / len(x_coords)
        ly = sum(y_coords) / len(y_coords)
        return any(xn <= lx <= xx and yn <= ly <= yx for xn, xx, yn, yx in boxes)

    @staticmethod
    def _table_to_markdown(table) -> str:
        """Convert a table object to Markdown.

        :param table: Table object with cell content.
        :return: Markdown table string.
        """
        grid = [[""] * table.column_count for _ in range(table.row_count)]
        for cell in table.cells:
            content = cell.content.replace("\n", " ").strip()
            grid[cell.row_index][cell.column_index] = content

        def _md_row(cells):
            """Render a list of cells as a Markdown table row.

            :param cells: Table row cell values.
            :return: Markdown row string.
            """
            return "| " + " | ".join(cells) + " |"

        header_row = _md_row(grid[0]) if grid else ""
        separator = "| " + " | ".join(["---"] * table.column_count) + " |"
        data_rows = [_md_row(row) for row in grid[1:]]
        return "\n".join([header_row, separator] + data_rows)

    @staticmethod
    def remove_header(text: str, header: str) -> str:
        """Remove a header string from text when present.

        :param text: Input text.
        :param header: Header to remove.
        :return: Text with header removed if found.
        """
        if not header or not text:
            return text
        if header in text:
            text = text.replace(header, "", 1)
        return text.strip()

    @staticmethod
    def extract_page_header_contents(page_number: int, az_result) -> Set[str]:
        """Extract header contents for a page.

        :param page_number: Page number to inspect.
        :param az_result: Analysis result containing paragraphs.
        :return: Set of header content strings.
        """
        page_paragraphs = []
        for para in (az_result.paragraphs or []):
            if not para.bounding_regions:
                continue
            region = para.bounding_regions[0]
            if region.page_number != page_number:
                continue
            poly = region.polygon or []
            if not poly:
                continue
            y = poly[1] if not hasattr(poly[0], 'y') else poly[0].y
            page_paragraphs.append((y, para))

        page_paragraphs.sort(key=lambda t: t[0])

        last_header_idx = -1
        for idx, (y, para) in enumerate(page_paragraphs):
            if para.role == ParagraphRole.PAGE_HEADER:
                last_header_idx = idx

        if last_header_idx == -1:
            return set()

        header_contents: Set[str] = set()
        for idx in range(last_header_idx + 1):
            _, para = page_paragraphs[idx]
            header_contents.add(para.content.strip())
        return header_contents

    @staticmethod
    def extract_tables_metadata_from_text(content: str) -> list:
        """Detect Markdown/HTML tables in raw text and return metadata.

        :param content: Raw text content.
        :return: Table metadata list with counts and placeholders.
        """
        import re
        tables_metadata = []
        md_tables = re.compile(r"((?:\|.*\|\s*\n)+)", re.MULTILINE).findall(content)
        for idx, table_text in enumerate(md_tables):
            lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
            if len(lines) < 2:
                continue
            col_count = lines[0].count("|") - 1
            row_count = len(lines[2:]) + 1  # lignes de données + ligne header
            tables_metadata.append({
                "table_index": idx,
                "row_count": row_count,
                "col_count": col_count,
                "y_position": None,
            })
        html_tables = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE).findall(content)
        for idx, table_html in enumerate(html_tables, start=len(tables_metadata)):
            rows = re.findall(r"<tr.*?>", table_html, re.IGNORECASE)
            cols = re.findall(r"<t[dh].*?>", table_html, re.IGNORECASE)
            tables_metadata.append({
                "table_index": idx,
                "row_count": len(rows),
                "col_count": len(cols),
                "y_position": None,
            })
        return tables_metadata