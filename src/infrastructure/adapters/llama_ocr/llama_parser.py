"""Parser utilities for OCR markdown and workflow extraction."""

import logging
import re

from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class LlamaOcrParser:
    """Parse OCR output and extract workflow content."""

    @staticmethod
    def extract_text_from_response(data: dict):
        """Extract markdown or text content from an OCR response.

        :param data: OCR response payload.
        :return: Extracted markdown or text.
        """
        raw_md = LlamaOcrParser._extract_raw_markdown(data)
        return raw_md

    @staticmethod
    def _extract_raw_markdown(data: dict) -> str:
        """Return the raw markdown or text from response payload.

        :param data: OCR response payload.
        :return: Raw markdown or plain text.
        """
        for key in ("markdown_full", "markdown"):
            obj = data.get(key)
            if isinstance(obj, dict):
                parts = [(p.get("markdown") or p.get("md") or "").strip() for p in obj.get("pages", [])]
                parts = [p for p in parts if p]
                if parts:
                    return "\n\n".join(parts)
            elif isinstance(obj, str) and obj.strip():
                return obj.strip()

        for key in ("text_full", "text"):
            obj = data.get(key)
            if isinstance(obj, dict):
                parts = [
                    p.get("text", "").strip()
                    for p in obj.get("pages", [])
                    if isinstance(p.get("text"), str) and p.get("text").strip()
                ]
                if parts:
                    return "\n\n".join(parts)
            elif isinstance(obj, str) and obj.strip():
                return obj.strip()

        logger.warning("No markdown or text content found in Llama response")
        return ""

    @staticmethod
    def split_mermaid_blocks(raw_md: str):
        """Split raw markdown into Mermaid workflow and surrounding text.

        :param raw_md: Raw markdown string.
        :return: Tuple of (workflow, pre_graph, post_graph).
        """
        pattern = re.compile(r"```(?:mermaid)?\s*\n(.*?)```", re.DOTALL)
        matches = list(pattern.finditer(raw_md))

        if not matches:
            logger.info("No mermaid blocks found in raw markdown")
            return "", raw_md.strip(), ""

        workflow = "\n\n".join([m.group(1).strip() for m in matches])
        pre_graph = raw_md[: matches[0].start()].strip()
        post_graph = raw_md[matches[-1].end() :].strip()

        logger.info(
            "Mermaid blocks extracted: %d blocks, workflow length=%d",
            len(matches), len(workflow)
        )
        return workflow, pre_graph, post_graph

    @staticmethod
    def convert_html_tables_to_markdown(text: str) -> str:
        """Convert HTML tables in text to Markdown format.

        :param text: Input text containing HTML tables.
        :return: Text with HTML tables converted to Markdown.
        """
        table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE)

        def convert_single_table(table_html: str) -> str:
            """Convert a single HTML table block to Markdown.

            :param table_html: HTML table markup.
            :return: Markdown table string.
            """
            rows = re.findall(r"<tr.*?>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
            md_rows = []
            for row in rows:
                cells = re.findall(r"<t[dh].*?>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                clean_cells = [re.sub(r"<.*?>", "", c).strip() for c in cells]
                if clean_cells:
                    md_rows.append(clean_cells)
            if not md_rows:
                return ""
            header = "| " + " | ".join(md_rows[0]) + " |"
            separator = "| " + " | ".join(["---"] * len(md_rows[0])) + " |"
            body = ["| " + " | ".join(r) + " |" for r in md_rows[1:]]
            return "\n".join([header, separator] + body)

        return table_pattern.sub(lambda m: convert_single_table(m.group(0)), text)