import pytest

from src.domain.models.paragraph_model import Paragraph
from src.domain.services.document_chunking import _count_md_tables, _metadata_for_chunk, SmartChunker


def test_count_md_tables():
    text = "| a | b |\n| - | - |\n| 1 | 2 |"
    assert _count_md_tables(text) == 1
    assert _count_md_tables("") == 0


def test_metadata_for_chunk():
    text = "| a | b |\n| - | - |\n| 1 | 2 |"
    meta = [{"t": 1}, {"t": 2}]
    assert _metadata_for_chunk(text, meta) == [{"t": 1}]
    assert _metadata_for_chunk("no table", meta) == []


def test_chunker_init_overlap_error():
    with pytest.raises(ValueError):
        SmartChunker(max_chunk=100, overlap=100)


def test_chunk_paragraphs_empty():
    chunker = SmartChunker(max_chunk=50, overlap=0)
    assert chunker.chunk_paragraphs([]) == []


def test_chunk_small_paragraph():
    chunker = SmartChunker(max_chunk=50, overlap=0)
    para = Paragraph(None, None, "doc", "hello world", 0, False)
    chunks = chunker.chunk_paragraphs([para])
    assert len(chunks) == 1
    assert chunks[0].chunk_text == "hello world"


def test_chunk_overlap_applied():
    chunker = SmartChunker(max_chunk=10, overlap=3)
    para = Paragraph(None, None, "doc", "one two three four five six seven eight nine ten eleven twelve.", 0, False)
    chunks = chunker.chunk_paragraphs([para])
    assert len(chunks) >= 2
    assert chunks[1].chunk_text.startswith(chunks[0].chunk_text[-3:])
