import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Any


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


@dataclass
class Chunk:
    id: str
    doc_name: str
    paragraph_id: str
    title: Optional[str]
    sub_title: Optional[str]
    chunk_text: str
    original_text: str
    has_table: bool
    table_metadata: List[Any] = field(default_factory=list)
    embedding: Optional[List[float]] = field(default=None)


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

    def __init__(self, max_chunk: int = 3000, overlap: int = 200):
        if overlap >= max_chunk:
            raise ValueError("overlap must be strictly less than max_chunk")
        self.max_chunk = max_chunk
        self.overlap = overlap

    # ── public entry point ────────────────────

    def chunk_paragraphs(self, paragraphs: List[Paragraph]) -> List[Chunk]:
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
        """
        Prepend the last `overlap` chars of chunk[i-1] (ORIGINAL, not already
        overlapped) to chunk[i].  This avoids cumulative duplication.

        chunk[0]  -> unchanged
        chunk[i]  -> chunks[i-1][-overlap:] + " " + chunks[i]   (i > 0)

        The source is always the original `chunks` list, never the mutated one.
        """
        if not chunks or self.overlap <= 0:
            return chunks

        overlapped = [chunks[0]]  # first chunk untouched

        for i in range(1, len(chunks)):
            # Always read from the ORIGINAL list to avoid snowball effect
            tail = chunks[i - 1][-self.overlap:]
            overlapped.append(tail + " " + chunks[i])

        return overlapped

    # ── factory ───────────────────────────────

    @staticmethod
    def _make_chunk(para: Paragraph, para_id: str, text: str) -> Chunk:
        return Chunk(
            id=str(uuid.uuid4()),
            doc_name=para.name_doc,
            paragraph_id=para_id,
            title=para.title,
            sub_title=para.sub_title,
            chunk_text=text,
            original_text=para.text,
            embedding=None,
            has_table=para.has_table,
            table_metadata=para.table_metadata.copy()
        )