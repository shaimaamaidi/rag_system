"""Chunking utilities to split paragraphs into retrievable chunks."""

import re
import uuid
import logging
from typing import List, Any
from pathlib import Path

from src.domain.models.chunk_model import Chunk
from src.domain.models.paragraph_model import Paragraph
from src.domain.services.document_category_extractor import DocumentCategoryExtractor
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def _count_md_tables(text: str) -> int:
    """Count Markdown tables in a text segment.

    :param text: Input text segment.
    :return: Number of Markdown tables detected.
    """
    if not text:
        return 0
    return len(re.findall(r"(?:\|.*\|[ \t]*(?:\n|$))+", text))


def _metadata_for_chunk(chunk_text: str, all_metadata: List[Any]) -> List[Any]:
    """Filter table metadata to match tables present in a chunk.

    :param chunk_text: Chunk text to analyze.
    :param all_metadata: Full list of table metadata.
    :return: Metadata entries corresponding to tables in the chunk.
    """
    n = _count_md_tables(chunk_text)
    if n == 0 or not all_metadata:
        return []
    return all_metadata[:min(n, len(all_metadata))]


class SmartChunker:
    """Split :class:`Paragraph` objects into :class:`Chunk` objects."""

    SMALL_PARA_TOLERANCE: int = 30

    def __init__(self, max_chunk: int = 3000, overlap: int = 200, extractor_category: DocumentCategoryExtractor = None):
        """Initialize the chunker.

        :param max_chunk: Maximum chunk size in characters.
        :param overlap: Overlap size between adjacent chunks.
        :param extractor_category: Optional category extractor.
        :raises ValueError: If overlap is greater than or equal to max_chunk.
        """
        if overlap >= max_chunk:
            raise ValueError("overlap must be strictly less than max_chunk")
        self.max_chunk = max_chunk
        self.overlap = overlap
        self.extractor_category = extractor_category
        logger.info(
            "SmartChunker initialized: max_chunk=%d, overlap=%d, extractor_category=%s",
            self.max_chunk,
            self.overlap,
            "provided" if extractor_category else "None",
        )

    def chunk_paragraphs(self, paragraphs: List[Paragraph]) -> List[Chunk]:
        """Split paragraphs into chunks.

        :param paragraphs: Paragraphs to chunk.
        :return: List of generated chunks.
        """
        logger.info("Starting chunking of %d paragraphs", len(paragraphs))
        if not paragraphs:
            logger.warning("No paragraphs provided to chunk")
            return []

        chunks: List[Chunk] = []
        for para in paragraphs:
            para_id = str(uuid.uuid4())
            para_chunks = self._chunk_paragraph(para, para_id)
            chunks.extend(para_chunks)

        logger.info("Chunking completed: %d total chunks created", len(chunks))
        return chunks

    def _chunk_paragraph(self, para: Paragraph, para_id: str) -> List[Chunk]:
        """Chunk a single paragraph with the configured strategy.

        :param para: Paragraph to split.
        :param para_id: Stable paragraph identifier.
        :return: List of chunks derived from the paragraph.
        """
        text = para.text.strip()

        if (para.title and text == para.title.strip()) or \
                (para.sub_title and text == para.sub_title.strip()):
            return []

        if para.is_article:
            return [self._make_chunk(para, para_id, text)]

        limit = self.max_chunk + self.SMALL_PARA_TOLERANCE

        if len(text) <= limit:
            return [self._make_chunk(para, para_id, text)]

        if "." in text:
            pieces = self._split_by_sentences(text)
        elif "\n" in text:
            pieces = self._split_by_newlines(text)
        else:
            pieces = self._hard_split(text)

        pieces = self._apply_overlap(pieces)

        return [self._make_chunk(para, para_id, p) for p in pieces if p.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """Pack sentences (split on '.') into chunks <= max_chunk."""
        raw_sentences = text.split(".")
        sentences = [s.strip() + "." for s in raw_sentences if s.strip()]
        return self._pack(sentences)

    def _split_by_newlines(self, text: str) -> List[str]:
        """Pack lines into chunks <= max_chunk."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return self._pack(lines)

    def _hard_split(self, text: str) -> List[str]:
        """Brute-force: cut every max_chunk characters."""
        return [text[i: i + self.max_chunk] for i in range(0, len(text), self.max_chunk)]

    def _pack(self, units: List[str]) -> List[str]:
        """
        Greedily pack text units into chunks that respect max_chunk.
        If a single unit exceeds max_chunk it is hard-split.
        """
        chunks: List[str] = []
        current = ""

        for unit in units:
            if len(unit) > self.max_chunk:
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(self._hard_split(unit))
                continue

            sep = " " if current else ""
            if len(current) + len(sep) + len(unit) <= self.max_chunk:
                current += sep + unit
            else:
                if current:
                    chunks.append(current.strip())
                current = unit

        if current:
            chunks.append(current.strip())

        return chunks

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """Apply overlap between adjacent chunks.

        :param chunks: Sequential chunk list before overlap.
        :return: New chunk list with overlap applied.
        """
        if not chunks or self.overlap <= 0:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-self.overlap:]
            overlapped.append(tail + " " + chunks[i])

        return overlapped

    def _make_chunk(self, para: Paragraph, para_id: str, text: str) -> Chunk:
        """Create a chunk object from paragraph data.

        :param para: Source paragraph.
        :param para_id: Paragraph identifier.
        :param text: Chunk text.
        :return: Constructed chunk.
        """
        category = None
        if self.extractor_category:
            categories = self.extractor_category.extract_categories()
            doc_key = Path(para.name_doc).stem if para.name_doc else ""
            category = categories.get(para.name_doc) or categories.get(doc_key) or []

        chunk_table_metadata = _metadata_for_chunk(text, para.table_metadata or [])
        chunk_has_table = bool(chunk_table_metadata)
        title = ""
        if para.title:
            title += para.title + " - "
        if para.sub_title:
            title += para.sub_title

        chunk = Chunk(
            id=str(uuid.uuid4()),
            doc_name=para.name_doc,
            paragraph_id=para_id,
            title=title,
            chunk_text=text,
            original_text=para.text,
            embedding=None,
            has_table=chunk_has_table,
            table_metadata=chunk_table_metadata,
            target_group=category,
        )
        return chunk