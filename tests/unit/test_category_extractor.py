import pandas as pd
import pytest

from src.domain.exceptions.category_extraction_exception import CategoryExtractionException
from src.domain.exceptions.category_extractor_config_exception import CategoryExtractorConfigException
from src.domain.services.document_category_extractor import DocumentCategoryExtractor


def test_missing_env_raises(monkeypatch):
    monkeypatch.setattr(
        "src.domain.services.document_category_extractor.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.delenv("EXCEL_PATH", raising=False)
    with pytest.raises(CategoryExtractorConfigException):
        DocumentCategoryExtractor()


def test_extract_categories_success(monkeypatch, tmp_path):
    monkeypatch.setenv("EXCEL_PATH", "data.xlsx")

    df = pd.DataFrame([
        [None, None, "اسم الوثيقة", "تصنيف"],
        [None, None, "Doc1", "Cat1"],
        [None, None, "Doc2", "Cat2"],
    ])

    def fake_read_excel(*_args, **_kwargs):
        return df

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    extractor = DocumentCategoryExtractor()
    result = extractor.extract_categories()

    assert result == {"Doc1": "Cat1", "Doc2": "Cat2"}


def test_extract_categories_failure(monkeypatch):
    monkeypatch.setenv("EXCEL_PATH", "data.xlsx")

    def fake_read_excel(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    extractor = DocumentCategoryExtractor()
    with pytest.raises(CategoryExtractionException):
        extractor.extract_categories()
