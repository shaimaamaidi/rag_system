import os
import json
import fitz

from src.domain.exceptions.page_image_extraction_exception import PageImageExtractionException
from src.domain.exceptions.workflow_conversion_exception import WorkflowConversionException
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.llama_ocr.llama_ocr_processor import LlamaOcrAdapter
from src.infrastructure.adapters.workflow_convertor.azure_workflow_converter import AzureWorkflowConverter

class PageProcessor:
    """Orchestration pour extraire texte, workflows et tables d'une page."""

    def __init__(self, prompt_provider: PromptProviderPort):
        self._llama = LlamaOcrAdapter()
        self._converter = AzureWorkflowConverter(prompt_provider)

    def process_workflow_page(self, page, file_path: str) -> dict:
        tmp_dir = "tmp_images"
        os.makedirs(tmp_dir, exist_ok=True)
        image_path = os.path.join(tmp_dir, f"page_{page.page_number}.png")

        # PDF → image
        try:
            doc = fitz.open(file_path)
            pdf_page = doc.load_page(page.page_number - 1)
            rect = pdf_page.rect
            mat = fitz.Matrix(3840 / rect.width, 2160 / rect.height)
            pix = pdf_page.get_pixmap(matrix=mat)
            pix.save(image_path)
            doc.close()
        except Exception as e:
            raise PageImageExtractionException(
                message=f"Failed to extract image from page {page.page_number}: {str(e)}"
            ) from e
        # OCR Llama
        ocr_result = self._llama.process(image_path)
        workflow = ocr_result.workflow
        pre_graph_content = ocr_result.pre_graph_content
        post_graph_content = ocr_result.post_graph_content
        has_table = ocr_result.has_table

        # Cleanup
        if os.path.exists(image_path):
            os.remove(image_path)

        content_type = "text"
        parts = []

        if pre_graph_content.strip():
            parts.append(pre_graph_content.strip())
        if workflow.strip():
            content_type = "workflow"
            try:
                result = self._converter.convert(workflow)
                parts.append(json.dumps(result.raw_json, ensure_ascii=False, indent=2))
            except Exception as e:
                raise WorkflowConversionException(
                    message=f"Azure GPT-4o workflow conversion failed: {str(e)}",
                    code="WORKFLOW_CONVERSION_ERROR",
                    http_status=502
                ) from e
        if post_graph_content.strip():
            parts.append(post_graph_content.strip())

        return {
            "type": content_type,
            "text": "\n\n".join(parts),
            "has_table": has_table,
        }