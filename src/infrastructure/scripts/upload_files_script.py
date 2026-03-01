"""
Script: ingest_data.py
Location: src/infrastructure/scripts/ingest_data.py
"""

import sys
from pathlib import Path

from src.domain.exceptions.app_exception import AppException

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.di.container import Container

DATA_DIR = PROJECT_ROOT / "data"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}


def _collect_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)

    all_files = [f for f in sorted(data_dir.iterdir()) if f.is_file()]

    # Séparer fichiers supportés et non supportés
    supported = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    unsupported = [f for f in all_files if f.suffix.lower() not in SUPPORTED_EXTENSIONS]

    # Signaler les fichiers ignorés
    if unsupported:
        print("⚠️  Skipped unsupported files:")
        for f in unsupported:
            print(f"   - {f.name} (extension '{f.suffix}' not supported)")
        print()

    if not supported:
        print(f"⚠️  No supported files found in: {data_dir}")
        print(f"   Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(0)

    return supported


def _ingest_file(ingest_use_case, file_path: Path) -> bool:
    try:
        ingest_use_case.ingest(str(file_path))
        print(f"✅ {file_path.name} — ingested successfully")
        return True
    except AppException as e:
        print(f"❌ {file_path.name} — [{e.code}] {e.message}")
        return False
    except Exception as e:
        print(f"❌ {file_path.name} — Unexpected error: {str(e)}")
        return False


def main() -> None:
    print("=" * 60)
    print("  RAG Ingestion Script")
    print(f"  Data directory : {DATA_DIR}")
    print(f"  Supported      : {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print("=" * 60)

    print("\n🔧 Initializing container...")
    try:
        container = Container()
    except AppException as e:
        print(f"❌ Container initialization failed: [{e.code}] {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Container initialization failed: {str(e)}")
        sys.exit(1)
    print("✅ Container ready\n")

    files = _collect_files(DATA_DIR)
    total = len(files)
    print(f"📂 Found {total} supported file(s) to ingest:\n")
    for f in files:
        print(f"   - {f.name}")
    print()

    success_count = 0
    failed_files = []

    for i, file_path in enumerate(files, start=1):
        print(f"[{i}/{total}] Processing: {file_path.name}")
        ok = _ingest_file(container.ingest_use_case, file_path)
        if ok:
            success_count += 1
        else:
            failed_files.append(file_path.name)

    print("\n" + "=" * 60)
    print(f"  SUMMARY")
    print(f"  Total     : {total}")
    print(f"  Success   : {success_count}")
    print(f"  Failed    : {total - success_count}")
    print(f"  Skipped   : {len([f for f in sorted(DATA_DIR.iterdir()) if f.is_file() and f.suffix.lower() not in SUPPORTED_EXTENSIONS])}")
    print("=" * 60)

    if failed_files:
        print("\n⚠️  Failed files:")
        for name in failed_files:
            print(f"   - {name}")
        sys.exit(1)

    print("\n🎉 All supported files ingested successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()