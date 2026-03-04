import asyncio
import importlib
from dataclasses import dataclass

import pytest

from src.domain.exceptions.document_loader_exception import DocumentLoaderException


def _make_loader_module(monkeypatch):
    module = importlib.import_module("src.infrastructure.adapters.document_loader.document_loader")
    module = importlib.reload(module)

    class DummyClient:
        def analyze_file(self, _):
            return None

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            pass

        async def process_workflow_page(self, *_args, **_kwargs):
            return {"type": "workflow", "text": "", "has_table": False, "tables_metadata": []}

        async def process_pptx_slide(self, *_args, **_kwargs):
            return {"type": "workflow", "text": "", "has_table": False, "tables_metadata": []}

    class DummyExtractor:
        def extract_page_header_contents(self, *_args, **_kwargs):
            return set()

        def extract_text_page(self, page, *_args, **_kwargs):
            return {
                "type": "text",
                "text": f"page-{page.page_number}",
                "has_table": False,
                "tables_metadata": [],
            }

    class DummyClassifier:
        def classify(self, *_args, **_kwargs):
            return "text"

    class DummyFileConverter:
        def convert_to_pdf(self, file_path):
            return file_path

        def clear(self, _):
            return None

        def pptx_to_images(self, _):
            return []

    monkeypatch.setattr(module, "AzureDocumentClient", DummyClient)
    monkeypatch.setattr(module, "PageProcessor", DummyProcessor)
    monkeypatch.setattr(module, "TextExtractor", DummyExtractor)
    monkeypatch.setattr(module, "PageClassifier", DummyClassifier)
    monkeypatch.setattr(module, "FileConverter", DummyFileConverter)

    return module


@dataclass
class FakePoint:
    x: float
    y: float


@dataclass
class FakeRegion:
    page_number: int
    polygon: list


@dataclass
class FakeParagraph:
    content: str
    role: str
    bounding_regions: list


@dataclass
class FakePage:
    page_number: int


@dataclass
class FakeAzResult:
    pages: list
    tables: list
    paragraphs: list


def test_load_empty_path(monkeypatch):
    module = _make_loader_module(monkeypatch)
    loader = module.DocumentLoader(prompt_provider=object())

    with pytest.raises(DocumentLoaderException):
        asyncio.run(loader.load(""))


def test_load_unsupported_extension(monkeypatch, tmp_path):
    module = _make_loader_module(monkeypatch)
    loader = module.DocumentLoader(prompt_provider=object())

    with pytest.raises(DocumentLoaderException):
        asyncio.run(loader.load(str(tmp_path / "file.txt")))


def test_load_missing_file(monkeypatch, tmp_path):
    module = _make_loader_module(monkeypatch)
    loader = module.DocumentLoader(prompt_provider=object())

    with pytest.raises(DocumentLoaderException):
        asyncio.run(loader.load(str(tmp_path / "missing.pdf")))


def test_load_docx_converts_and_clears(monkeypatch, tmp_path):
    module = _make_loader_module(monkeypatch)

    class TrackingConverter:
        def __init__(self):
            self.converted = None
            self.cleared = None

        def convert_to_pdf(self, file_path):
            self.converted = file_path
            return str(tmp_path / "converted.pdf")

        def clear(self, file_path):
            self.cleared = file_path

    class DummyClient:
        def analyze_file(self, _):
            return FakeAzResult(pages=[], tables=[], paragraphs=[])

    converter = TrackingConverter()

    monkeypatch.setattr(module, "FileConverter", lambda: converter)
    monkeypatch.setattr(module, "AzureDocumentClient", DummyClient)
    loader = module.DocumentLoader(prompt_provider=object())

    called = {}

    async def fake_load_pdf(path):
        called["path"] = path
        return [], []

    monkeypatch.setattr(loader, "_load_pdf", fake_load_pdf)

    docx_path = tmp_path / "doc.docx"
    docx_path.write_text("x", encoding="utf-8")

    result = asyncio.run(loader.load(str(docx_path)))

    assert result == ([], [])
    assert converter.converted == str(docx_path)
    assert converter.cleared == str(tmp_path / "converted.pdf")
    assert called["path"] == str(tmp_path / "converted.pdf")


def test_load_pptx_path(monkeypatch, tmp_path):
    module = _make_loader_module(monkeypatch)
    loader = module.DocumentLoader(prompt_provider=object())

    pptx_path = tmp_path / "slides.pptx"
    pptx_path.write_text("x", encoding="utf-8")

    async def fake_load_pptx(path):
        return ["page"], []

    monkeypatch.setattr(loader, "_load_pptx", fake_load_pptx)

    result = asyncio.run(loader.load(str(pptx_path)))
    assert result == (["page"], [])


def test_extract_section_headings_sorted(monkeypatch):
    module = _make_loader_module(monkeypatch)

    paragraphs = [
        FakeParagraph(
            content="H2",
            role="sectionHeading",
            bounding_regions=[FakeRegion(2, [FakePoint(0.0, 0.9), FakePoint(1.0, 1.0)])],
        ),
        FakeParagraph(
            content="H1",
            role="title",
            bounding_regions=[FakeRegion(1, [FakePoint(0.0, 0.2), FakePoint(1.0, 0.3)])],
        ),
        FakeParagraph(
            content="Other",
            role="body",
            bounding_regions=[FakeRegion(1, [FakePoint(0.0, 0.5), FakePoint(1.0, 0.6)])],
        ),
    ]

    az_result = FakeAzResult(pages=[], tables=[], paragraphs=paragraphs)
    headings = module.DocumentLoader._extract_section_headings(az_result)

    assert [h.content for h in headings] == ["H1", "H2"]


def test_load_pdf_builds_pages(monkeypatch, tmp_path):
    module = _make_loader_module(monkeypatch)
    loader = module.DocumentLoader(prompt_provider=object())

    pages = [FakePage(1), FakePage(2)]
    az_result = FakeAzResult(pages=pages, tables=[], paragraphs=[])

    class FakeClient:
        def analyze_file(self, _):
            return az_result

    loader._client = FakeClient()

    result_pages, result_headings = asyncio.run(loader._load_pdf(str(tmp_path / "f.pdf")))

    assert [p.text for p in result_pages] == ["page-1", "page-2"]
    assert result_headings == []


def test_classify_document_by_article_density(monkeypatch):
    module = _make_loader_module(monkeypatch)

    headings = [
        module.SectionHeading(content="Article 1", page_number=1, y_position=0.1, x_position=0.1),
        module.SectionHeading(content="Article 2", page_number=2, y_position=0.1, x_position=0.1),
    ]
    assert module.DocumentLoader.classify_document_by_article_density(headings, ["Article"], 3) is True
    assert module.DocumentLoader.classify_document_by_article_density(headings, ["Article"], 5) is False
