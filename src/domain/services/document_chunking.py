import re
import uuid
import logging
from typing import List, Any
from pathlib import Path

from src.domain.models.chunk_model import Chunk
from src.domain.models.paragraph_model import Paragraph
from src.domain.services.document_category_extractor import DocumentCategoryExtractor
from src.infrastructure.adapters.config.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def _count_md_tables(text: str) -> int:
    """Compte le nombre de tables Markdown dans un segment de texte."""
    if not text:
        return 0
    return len(re.findall(r"(?:\|.*\|[ \t]*(?:\n|$))+", text))


def _metadata_for_chunk(chunk_text: str, all_metadata: List[Any]) -> List[Any]:
    """
    Retourne les entrées de table_metadata qui correspondent aux tables
    réellement présentes dans ce chunk, dans l'ordre.
    """
    n = _count_md_tables(chunk_text)
    if n == 0 or not all_metadata:
        return []
    return all_metadata[:min(n, len(all_metadata))]


class SmartChunker:
    """
    Splits Paragraph objects into Chunk objects.
    """

    SMALL_PARA_TOLERANCE: int = 30

    def __init__(self, max_chunk: int = 3000, overlap: int = 200, extractor_category: DocumentCategoryExtractor = None):
        if overlap >= max_chunk:
            raise ValueError("overlap must be strictly less than max_chunk")
        self.max_chunk = max_chunk
        self.overlap = overlap
        self.extractor_category = extractor_category
        logger.info(
            f"SmartChunker initialized: max_chunk={self.max_chunk}, overlap={self.overlap}, extractor_category={'provided' if extractor_category else 'None'}")

    def chunk_paragraphs(self, paragraphs: List[Paragraph]) -> List[Chunk]:
        logger.info(f"Starting chunking of {len(paragraphs)} paragraphs")
        if not paragraphs:
            logger.warning("No paragraphs provided to chunk")
            return []

        chunks: List[Chunk] = []
        for para in paragraphs:
            para_id = str(uuid.uuid4())
            para_chunks = self._chunk_paragraph(para, para_id)
            chunks.extend(para_chunks)

        logger.info(f"Chunking completed: {len(chunks)} total chunks created")
        return chunks

    def _chunk_paragraph(self, para: Paragraph, para_id: str) -> List[Chunk]:
        text = para.text.strip()

        # Skip paragraphs where text is just the title or sub_title
        if (para.title and text == para.title.strip()) or \
                (para.sub_title and text == para.sub_title.strip()):
            return []

        # Article rule: always a single chunk
        if para.is_article:
            return [self._make_chunk(para, para_id, text)]

        limit = self.max_chunk + self.SMALL_PARA_TOLERANCE

        if len(text) <= limit:
            return [self._make_chunk(para, para_id, text)]

        # Choose splitting strategy
        if "." in text:
            pieces = self._split_by_sentences(text)
        elif "\n" in text:
            pieces = self._split_by_newlines(text)
        else:
            pieces = self._hard_split(text)

        # Apply overlap
        pieces = self._apply_overlap(pieces)

        return [self._make_chunk(para, para_id, p) for p in pieces if p.strip()]

    # ── splitting helpers ─────────────────────
    # (les méthodes _split_by_sentences, _split_by_newlines, _hard_split, _pack, _apply_overlap restent inchangées)

    def _make_chunk(self, para: Paragraph, para_id: str, text: str) -> Chunk:
        category = None
        if self.extractor_category:
            categories = self.extractor_category.extract_categories()
            doc_key = Path(para.name_doc).stem if para.name_doc else ""
            category = categories.get(para.name_doc) or categories.get(doc_key)

        chunk_table_metadata = _metadata_for_chunk(text, para.table_metadata or [])
        chunk_has_table = bool(chunk_table_metadata)

        chunk = Chunk(
            id=str(uuid.uuid4()),
            doc_name=para.name_doc,
            paragraph_id=para_id,
            title=para.title,
            sub_title=para.sub_title,
            chunk_text=text,
            original_text=para.text,
            embedding=None,
            has_table=chunk_has_table,
            table_metadata=chunk_table_metadata,
            target_group=category,
        )
        return chunk