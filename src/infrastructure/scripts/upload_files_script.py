"""
Script: ingest_data.py
Location: src/infrastructure/scripts/ingest_data.py
"""
import logging
import sys
import os
from dotenv import load_dotenv
from pathlib import Path

from src.domain.exceptions.app_exception import AppException
from src.infrastructure.logging.logger import setup_logger
from src.infrastructure.di.container import Container

setup_logger()
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
data_dir_env = os.getenv("DATA_DIR")

if not data_dir_env:
    logger.error("DATA_DIR not defined in .env")
    sys.exit(1)

DATA_DIR = Path(data_dir_env)

# Si chemin relatif → on le rattache au project root
if not DATA_DIR.is_absolute():
    DATA_DIR = PROJECT_ROOT / DATA_DIR

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


def _collect_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        sys.exit(1)

    all_files = [f for f in sorted(data_dir.iterdir()) if f.is_file()]

    # Séparer fichiers supportés et non supportés
    supported = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    unsupported = [f for f in all_files if f.suffix.lower() not in SUPPORTED_EXTENSIONS]

    # Signaler les fichiers ignorés
    if unsupported:
        logger.warning("Skipped unsupported files:")
        for f in unsupported:
            logger.warning("   - %s (extension '%s' not supported)", f.name, f.suffix)

    if not supported:
        logger.warning("No supported files found in: %s", data_dir)
        sys.exit(0)

    return supported


async def _ingest_file(ingest_use_case, file_path: Path) -> bool:
    try:
        await ingest_use_case.ingest(str(file_path))
        logger.info("%s - ingested successfully", file_path.name)
        return True
    except AppException as e:
        logger.error("%s - [%s] %s", file_path.name, e.code, e.message)
        return False
    except Exception as e:
        logger.error("%s - Unexpected error: %s", file_path.name, str(e))
        return False


async def main() -> None:
    logger.info("  RAG Ingestion Script")
    logger.info("  Data directory : %s", DATA_DIR)
    logger.info("  Supported      : %s", ", ".join(sorted(SUPPORTED_EXTENSIONS)))

    logger.info("Initializing container...")

    try:
        container = Container()
    except AppException as e:
        logger.error("Container initialization failed: [%s] %s", e.code, e.message)
        sys.exit(1)
    except Exception as e:
        logger.error("Container initialization failed: %s", str(e))
        sys.exit(1)
    logger.info("Container ready")

    files = _collect_files(DATA_DIR)
    total = len(files)
    logger.info("Found %d supported file(s) to ingest:\n   - %s", total, "\n   - ".join(f.name for f in files))

    success_count = 0
    failed_files = []

    for i, file_path in enumerate(files, start=1):
        logger.info("[%d/%d] Processing: %s", i, total, file_path.name)
        ok = await _ingest_file(container.ingest_use_case, file_path)
        if ok:
            success_count += 1
        else:
            failed_files.append(file_path.name)

    if failed_files:
        failed_list = "\n   - ".join(failed_files)
        logger.warning("Failed files:\n   - %s", failed_list)
        sys.exit(1)

    logger.info("All supported files ingested successfully.")
    sys.exit(0)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())