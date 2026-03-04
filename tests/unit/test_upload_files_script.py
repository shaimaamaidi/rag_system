import asyncio
import importlib
from pathlib import Path

import pytest

from src.domain.exceptions.app_exception import AppException


def load_module(monkeypatch, data_dir: Path):
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    module = importlib.import_module("src.infrastructure.scripts.upload_files_script")
    return importlib.reload(module)


def test_collect_files_missing_directory(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    missing_dir = tmp_path / "missing"
    with pytest.raises(SystemExit) as exc_info:
        module._collect_files(missing_dir)
    assert exc_info.value.code == 1


def test_collect_files_filters_supported(monkeypatch, tmp_path, caplog):
    module = load_module(monkeypatch, tmp_path)
    (tmp_path / "a.pdf").write_bytes(b"dummy")
    (tmp_path / "b.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "c.pptx").write_bytes(b"dummy")

    with caplog.at_level("WARNING"):
        result = module._collect_files(tmp_path)

    assert [p.name for p in result] == ["a.pdf", "c.pptx"]
    assert "Skipped unsupported files" in caplog.text


def test_collect_files_no_supported(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)
    (tmp_path / "a.txt").write_text("skip", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        module._collect_files(tmp_path)
    assert exc_info.value.code == 0


def test_ingest_file_success(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FakeUseCase:
        async def ingest(self, _):
            return None

    result = asyncio.run(module._ingest_file(FakeUseCase(), tmp_path / "a.pdf"))
    assert result is True


def test_ingest_file_app_exception(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FakeUseCase:
        async def ingest(self, _):
            raise AppException("E001", "failure")

    result = asyncio.run(module._ingest_file(FakeUseCase(), tmp_path / "a.pdf"))
    assert result is False


def test_ingest_file_generic_exception(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FakeUseCase:
        async def ingest(self, _):
            raise RuntimeError("boom")

    result = asyncio.run(module._ingest_file(FakeUseCase(), tmp_path / "a.pdf"))
    assert result is False


def test_main_success(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FakeContainer:
        def __init__(self):
            self.ingest_use_case = object()

    monkeypatch.setattr(module, "Container", FakeContainer)
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "_collect_files", lambda _: [tmp_path / "a.pdf"])  # noqa: E731

    async def fake_ingest_file(_, __):
        return True

    monkeypatch.setattr(module, "_ingest_file", fake_ingest_file)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(module.main())
    assert exc_info.value.code == 0


def test_main_failure(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FakeContainer:
        def __init__(self):
            self.ingest_use_case = object()

    monkeypatch.setattr(module, "Container", FakeContainer)
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "_collect_files", lambda _: [tmp_path / "a.pdf"])  # noqa: E731

    async def fake_ingest_file(_, __):
        return False

    monkeypatch.setattr(module, "_ingest_file", fake_ingest_file)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(module.main())
    assert exc_info.value.code == 1


def test_main_container_app_exception(monkeypatch, tmp_path):
    module = load_module(monkeypatch, tmp_path)

    class FailContainer:
        def __init__(self):
            raise AppException("E999", "bad container")

    monkeypatch.setattr(module, "Container", FailContainer)
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(module.main())
    assert exc_info.value.code == 1
