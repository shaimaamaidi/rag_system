from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading
from src.domain.services.document_splitter import DocumentSplitter


def test_split_title_and_heading():
    pages = [
        PageContent(1, "text", "", "My Title", False, []),
        PageContent(2, "text", "", "Section A\nLine2\nLine3\nLine4\nLine5", False, []),
    ]
    headings = [SectionHeading("Section A", 2, 0.1, 0.1)]

    paragraphs = DocumentSplitter.split("doc1", pages, headings)

    assert len(paragraphs) == 1
    assert paragraphs[0].title == "My Title"
    assert paragraphs[0].sub_title == "Section A"
    assert paragraphs[0].text == "Line2\nLine3\nLine4\nLine5"


def test_split_pre_heading_page():
    pages = [
        PageContent(1, "text", "Header1", "Intro1\nIntro2\nIntro3\nIntro4\nIntro5", False, []),
        PageContent(2, "text", "", "Section A\nLine2\nLine3\nLine4\nLine5", False, []),
    ]
    headings = [SectionHeading("Section A", 2, 0.1, 0.1)]

    paragraphs = DocumentSplitter.split("doc1", pages, headings)

    assert len(paragraphs) == 2
    assert paragraphs[0].sub_title == "Header1"
    assert paragraphs[0].text == "Intro1\nIntro2\nIntro3\nIntro4\nIntro5"
    assert paragraphs[1].sub_title == "Section A"
    assert paragraphs[1].text == "Line2\nLine3\nLine4\nLine5"


def test_split_workflow_page():
    pages = [
        PageContent(1, "workflow", "", '{"workflow_title": "WF1"}\nStep 1', True, [{"table_index": 0}]),
    ]

    paragraphs = DocumentSplitter.split("doc1", pages, [])

    assert len(paragraphs) == 1
    assert paragraphs[0].sub_title == "WF1"
    assert paragraphs[0].text == '{"workflow_title": "WF1"}\nStep 1'
    assert paragraphs[0].has_table is True
