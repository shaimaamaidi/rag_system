"""Service for extracting document categories from an Excel mapping file."""

import os
import logging
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from src.domain.exceptions.category_extraction_exception import CategoryExtractionException
from src.domain.exceptions.category_extractor_config_exception import CategoryExtractorConfigException
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class DocumentCategoryExtractor:
    """Extract document categories from an Excel file.

    :param excel_path_env: Environment variable name containing the Excel path.
    """

    def __init__(self, excel_path_env: str = "EXCEL_PATH"):
        """Initialize the extractor.

        :param excel_path_env: Environment variable name containing the Excel path.
        """
        load_dotenv()
        excel_relative_path = os.getenv(excel_path_env)

        if not excel_relative_path:
            logger.error("Environment variable '%s' is not defined in .env", excel_path_env)
            raise CategoryExtractorConfigException(
                message=f"Environment variable '{excel_path_env}' is not defined in .env"
            )

        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # remonte jusqu'à src
        self.excel_path = project_root / excel_relative_path
        logger.info("DocumentCategoryExtractor initialized with Excel path: %s", self.excel_path)

    def extract_categories(self) -> dict:
        """Read the Excel file and build a document-to-category mapping.

        :return: Mapping of document name to category.
        :raises CategoryExtractionException: If the Excel content cannot be parsed.
        """
        logger.info("Starting category extraction from Excel: %s", self.excel_path)
        try:
            df = pd.read_excel(self.excel_path, engine="openpyxl", header=None)
            result = {}

            for _, row in df.iterrows():
                document_name = row.iloc[2]
                category = row.iloc[3]

                if (
                    pd.notna(document_name)
                    and pd.notna(category)
                    and str(document_name).strip() != "اسم الوثيقة"
                ):
                    result[str(document_name).strip()] = str(category).strip()

            logger.info("Category extraction completed successfully, %d categories found", len(result))
            return result

        except Exception as e:
            logger.exception("Failed to parse Excel content")
            raise CategoryExtractionException(
                message=f"Failed to parse Excel content: {str(e)}"
            ) from e