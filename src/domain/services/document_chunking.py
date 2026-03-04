import re
import uuid
from typing import List, Any

from pathlib import Path

from src.domain.models.chunk_model import Chunk
from src.domain.models.paragraph_model import Paragraph
from src.domain.services.document_category_extractor import DocumentCategoryExtractor


def _count_md_tables(text: str) -> int:
    """Compte le nombre de tables Markdown dans un segment de texte."""
    if not text:
        return 0
    return len(re.findall(r"(?:\|.*\|[ \t]*(?:\n|$))+", text))


def _metadata_for_chunk(chunk_text: str, all_metadata: List[Any]) -> List[Any]:
    """
    Retourne les entrées de table_metadata qui correspondent aux tables
    réellement présentes dans ce chunk, dans l'ordre.
    On prend min(n_tables_dans_text, len(all_metadata)) entrées depuis le début.
    """
    n = _count_md_tables(chunk_text)
    if n == 0 or not all_metadata:
        return []
    return all_metadata[:min(n, len(all_metadata))]


class SmartChunker:
    """
    Splits Paragraph objects into Chunk objects.

    Splitting strategy (in order of preference):
      1. Split on sentence boundaries  (".")
      2. Split on newlines             ("\\n")
      3. Hard split at max_chunk chars (fallback)

    Special rule:
      If a paragraph is <= (max_chunk + SMALL_PARA_TOLERANCE) characters
      it is treated as a single chunk — no splitting for trivially small text.

    Article rule:
      If a paragraph has is_article=True, it is ALWAYS returned as a single
      chunk regardless of its size — no splitting, no overlap applied.

    Skip rule:
      If a paragraph's text equals its title or sub_title, it is skipped entirely.

    Overlap:
      Each chunk (except the first) receives the last `overlap` characters
      of the ORIGINAL previous chunk as a prefix — ensuring consistent,
      non-cumulative context propagation.
      Final chunk size can reach max_chunk + overlap, which is intentional.
    """

    SMALL_PARA_TOLERANCE: int = 30

    def __init__(self, max_chunk: int = 3000, overlap: int = 200, extractor_category: DocumentCategoryExtractor = None):
        if overlap >= max_chunk:
            raise ValueError("overlap must be strictly less than max_chunk")
        self.max_chunk = max_chunk
        self.overlap = overlap
        self.extractor_category = extractor_category

    # ── public entry point ────────────────────

    def chunk_paragraphs(self, paragraphs: List[Paragraph]) -> List[Chunk]:
        if not paragraphs:
            return []
        chunks: List[Chunk] = []
        for para in paragraphs:
            para_id = str(uuid.uuid4())
            chunks.extend(self._chunk_paragraph(para, para_id))
        return chunks

    # ── per-paragraph logic ───────────────────

    def _chunk_paragraph(self, para: Paragraph, para_id: str) -> List[Chunk]:
        text = para.text.strip()

        # Skip paragraphs where text is just the title or sub_title
        if (para.title and text == para.title.strip()) or \
           (para.sub_title and text == para.sub_title.strip()):
            return []

        # Article rule: always a single chunk, no splitting, no overlap
        if para.is_article:
            return [self._make_chunk(para, para_id, text)]

        limit = self.max_chunk + self.SMALL_PARA_TOLERANCE

        # Rule: small-enough paragraph -> single chunk (no splitting)
        if len(text) <= limit:
            return [self._make_chunk(para, para_id, text)]

        # Choose splitting strategy
        if "." in text:
            pieces = self._split_by_sentences(text)
        elif "\n" in text:
            pieces = self._split_by_newlines(text)
        else:
            pieces = self._hard_split(text)

        # Apply overlap on the RAW pieces (before any mutation)
        pieces = self._apply_overlap(pieces)

        return [self._make_chunk(para, para_id, p) for p in pieces if p.strip()]

    # ── splitting helpers ─────────────────────

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

    # ── overlap ───────────────────────────────

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        if not chunks or self.overlap <= 0:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-self.overlap:]
            overlapped.append(tail + " " + chunks[i])

        return overlapped

    # ── factory ───────────────────────────────

    def _make_chunk(self, para: Paragraph, para_id: str, text: str) -> Chunk:
        category = None
        if self.extractor_category:
            categories = self.extractor_category.extract_categories()
            doc_key = Path(para.name_doc).stem if para.name_doc else ""
            category = categories.get(para.name_doc) or categories.get(doc_key)

        # Ne garder que les métadonnées des tables présentes dans ce chunk
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