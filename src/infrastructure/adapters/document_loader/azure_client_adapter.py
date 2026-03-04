import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from src.infrastructure.adapters.config.logger import setup_logger
import logging

from src.domain.exceptions.azure_document_analysis_exception import AzureDocumentAnalysisException
from src.domain.exceptions.azure_document_config_exception import AzureDocumentConfigException

setup_logger()
logger = logging.getLogger(__name__)


class AzureDocumentClient:
    """Wrapper Azure Document Intelligence."""

    def __init__(self):
        load_dotenv()
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not all([key, endpoint]):
            logger.error("Missing Azure Document Intelligence environment variables")
            raise AzureDocumentConfigException(
                "Missing one or more Azure Document Intelligence environment variables "
                "(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY)"
            )

        try:
            self._client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
            logger.info("Azure Document Intelligence client initialized successfully")
        except Exception as e:
            logger.exception("Failed to initialize Azure Document Intelligence client")
            raise AzureDocumentConfigException(
                "Failed to initialize Azure Document Intelligence client"
            ) from e

    def analyze_file(self, file_path: str, pdf_style: bool = True):
        logger.info(f"Analyzing file with Azure Document Intelligence: {file_path}")
        try:
            with open(file_path, "rb") as f:
                features = [DocumentAnalysisFeature.STYLE_FONT] if pdf_style else []
                poller = self._client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=f,
                    features=features,
                )
            result = poller.result()
            logger.info(f"Analysis completed for file: {file_path}")
            return result
        except Exception as e:
            logger.exception(f"Analysis failed for file: {file_path}")
            raise AzureDocumentAnalysisException(
                message=f"Azure Document Intelligence analysis failed: {str(e)}"
            ) from e