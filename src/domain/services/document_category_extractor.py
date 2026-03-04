import os
import logging
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from src.domain.exceptions.category_extraction_exception import CategoryExtractionException
from src.domain.exceptions.category_extractor_config_exception import CategoryExtractorConfigException
from src.infrastructure.adapters.config.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class DocumentCategoryExtractor:
    """
    Service pour extraire les catégories de documents depuis un fichier Excel.
    """

    def __init__(self, excel_path_env: str = "EXCEL_PATH"):
        """
        Initialise le service en chargeant le chemin du fichier Excel depuis le .env.
        :param excel_path_env: Nom de la variable d'environnement contenant le chemin Excel
        """
        load_dotenv()
        excel_relative_path = os.getenv(excel_path_env)

        if not excel_relative_path:
            logger.error(f"Environment variable '{excel_path_env}' is not defined in .env")
            raise CategoryExtractorConfigException(
                message=f"Environment variable '{excel_path_env}' is not defined in .env"
            )

        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # remonte jusqu'à src
        self.excel_path = project_root / excel_relative_path
        logger.info(f"DocumentCategoryExtractor initialized with Excel path: {self.excel_path}")

    def extract_categories(self) -> dict:
        """
        Lit le fichier Excel et renvoie un dictionnaire {nom_document: catégorie}.
        :return: dict
        """
        logger.info(f"Starting category extraction from Excel: {self.excel_path}")
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

            logger.info(f"Category extraction completed successfully, {len(result)} categories found")
            return result

        except Exception as e:
            logger.exception("Failed to parse Excel content")
            raise CategoryExtractionException(
                message=f"Failed to parse Excel content: {str(e)}"
            ) from e