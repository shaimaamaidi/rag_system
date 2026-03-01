import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from src.domain.exceptions.azure_document_analysis_exception import AzureDocumentAnalysisException
from src.domain.exceptions.azure_document_config_exception import AzureDocumentConfigException


class AzureDocumentClient:
    """Wrapper Azure Document Intelligence."""

    def __init__(self):
        load_dotenv()
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not all([key, endpoint]):
            raise AzureDocumentConfigException(
                "Missing one or more Azure Document Intelligence environment variables "
                "(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY)"
            )
        self._client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def analyze_file(self, file_path: str, pdf_style: bool = True):
        try:
            with open(file_path, "rb") as f:
                features = [DocumentAnalysisFeature.STYLE_FONT] if pdf_style else []
                poller = self._client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=f,
                    features=features,
                )
            return poller.result()
        except Exception as e:
            raise AzureDocumentAnalysisException(
                message=f"Azure Document Intelligence analysis failed: {str(e)}"
            ) from e