import logging
import os
import json
import fitz

from src.domain.exceptions.page_image_extraction_exception import PageImageExtractionException
from src.domain.exceptions.workflow_conversion_exception import WorkflowConversionException
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.config.logger import setup_logger
from src.infrastructure.adapters.document_loader.text_extractor import TextExtractor
from src.infrastructure.adapters.llama_ocr.llama_ocr_processor import LlamaOcrAdapter
from src.infrastructure.adapters.workflow_convertor.azure_workflow_converter import AzureWorkflowConverter

setup_logger()
logger = logging.getLogger(__name__)


class PageProcessor:
    """Orchestration pour extraire texte, workflows et tables d'une page."""

    def __init__(self, prompt_provider: PromptProviderPort):
        self._llama = LlamaOcrAdapter()
        self._converter = AzureWorkflowConverter(prompt_provider)

    # ------------------------------------------------------------------ #
    #  PDF workflow page (existing)                                       #
    # ------------------------------------------------------------------ #
    async def process_workflow_page(self, page, file_path: str) -> dict:
        tmp_dir = "tmp_images"
        os.makedirs(tmp_dir, exist_ok=True)
        image_path = os.path.join(tmp_dir, f"page_{page.page_number}.png")
        logger.info(f"Processing PDF page {page.page_number}: {file_path} → {image_path}")

        # PDF → image
        try:
            doc = fitz.open(file_path)
            if page.page_number - 1 >= len(doc):
                raise PageImageExtractionException(
                    message=f"Page {page.page_number} out of range — PDF has {len(doc)} pages."
                )
            pdf_page = doc.load_page(page.page_number - 1)
            rect = pdf_page.rect
            mat = fitz.Matrix(3840 / rect.width, 2160 / rect.height)
            pix = pdf_page.get_pixmap(matrix=mat)
            pix.save(image_path)
            doc.close()
            logger.info(f"Extracted image for page {page.page_number}")

        except Exception as e:
            logger.error(f"Failed to extract image from page {page.page_number}: {e}")
            raise PageImageExtractionException(
                message=f"Failed to extract image from page {page.page_number}: {str(e)}"
            ) from e

        return await self._run_llama_pipeline(image_path, cleanup=True)

    # ------------------------------------------------------------------ #
    #  PPTX slide (new) — image already on disk, no PDF extraction       #
    # ------------------------------------------------------------------ #
    async def process_pptx_slide(self, image_path: str, slide_number: int) -> dict:
        """Traite une slide PPTX déjà exportée en image.

        Args:
            image_path: Chemin vers le PNG de la slide (persistent).
            slide_number: Numéro de la slide (1-indexed), utilisé pour les messages d'erreur.

        Returns:
            dict avec les clés : type, text, has_table, tables_metadata.
        """
        logger.info(f"Processing PPTX slide {slide_number}: {image_path}")

        if not os.path.exists(image_path):
            logger.error(f"Slide image not found for slide {slide_number}: {image_path}")
            raise PageImageExtractionException(
                message=f"Slide image not found for slide {slide_number}: {image_path}"
            )

        # Images are persistent — no cleanup
        return await self._run_llama_pipeline(image_path, cleanup=False)

    # ------------------------------------------------------------------ #
    #  Shared Llama OCR + workflow conversion pipeline                   #
    # ------------------------------------------------------------------ #
    async def _run_llama_pipeline(self, image_path: str, cleanup: bool) -> dict:
        """Appelle Llama OCR sur une image et convertit le workflow si présent.

        Args:
            image_path: Chemin de l'image à traiter.
            cleanup: Si True, supprime l'image après traitement.
        """
        logger.info(f"Running Llama OCR pipeline on {image_path}")

        try:
            ocr_result = await self._llama.process(image_path)
        finally:
            if cleanup and os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Removed temporary image {image_path}")

        workflow = ocr_result.workflow
        pre_graph_content = ocr_result.pre_graph_content
        post_graph_content = ocr_result.post_graph_content
        has_table = ocr_result.has_table

        content_type = "text"
        parts = []

        if pre_graph_content.strip():
            parts.append(pre_graph_content.strip())

        if workflow.strip():
            content_type = "workflow"
            logger.info(f"Found workflow content in image {image_path}, converting with Azure Workflow")

            try:
                result = self._converter.convert(workflow)
                parts.append(json.dumps(result.raw_json, ensure_ascii=False, indent=2))
                logger.info(f"Workflow conversion succeeded for {image_path}")
            except Exception as e:
                logger.error(f"Workflow conversion failed for {image_path}: {e}")
                raise WorkflowConversionException(
                    message=f"Azure GPT-4o workflow conversion failed: {str(e)}",
                    code="WORKFLOW_CONVERSION_ERROR",
                    http_status=502,
                ) from e

        if post_graph_content.strip():
            parts.append(post_graph_content.strip())

        full_text = "\n\n".join(parts)

        tables_metadata = TextExtractor.extract_tables_metadata_from_text(full_text)
        logger.info(f"Finished processing image {image_path}, content_type={content_type}, tables={len(tables_metadata)}")

        return {
            "type":            content_type,
            "text":            full_text,
            "has_table":       has_table,
            "tables_metadata": tables_metadata,
        }