import logging
from typing import List, Tuple, Set
from pathlib import Path

from src.domain.exceptions.document_loader_exception import DocumentLoaderException
from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading
from src.domain.ports.input.document_loader_port import DocumentLoaderPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.domain.services.page_classifier import PageClassifier
from src.infrastructure.adapters.config.logger import setup_logger
from src.infrastructure.adapters.document_loader.azure_client_adapter import AzureDocumentClient
from src.infrastructure.adapters.document_loader.file_converter import FileConverter
from src.infrastructure.adapters.document_loader.page_processing import PageProcessor
from src.infrastructure.adapters.document_loader.text_extractor import TextExtractor

setup_logger()
logger = logging.getLogger(__name__)


class DocumentLoader(DocumentLoaderPort):
    """Orchestration principale pour le chargement et traitement d'un document."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}

    def __init__(self, prompt_provider: PromptProviderPort):
        self._client = AzureDocumentClient()
        self._processor = PageProcessor(prompt_provider)
        self._extractor = TextExtractor()
        self._page_classifier = PageClassifier()
        self._file_converter = FileConverter()

    # ------------------------------------------------------------------ #
    #  Point d'entrée public                                               #
    # ------------------------------------------------------------------ #
    async def load(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        logger.info(f"Starting document load: {file_path}")

        if not file_path:
            logger.error("File path is empty")
            raise DocumentLoaderException("Le chemin du fichier ne peut pas être vide.")

        ext = Path(file_path).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file type '{ext}'")
            raise DocumentLoaderException(
                message=f"Unsupported file type '{ext}'. "
                        f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            raise DocumentLoaderException(message=f"File not found: {file_path}")

        if ext == ".pptx":
            return await self._load_pptx(file_path)

        converted_path: str = file_path
        try:
            if ext == ".docx":
                converted_path = self._file_converter.convert_to_pdf(file_path)
                logger.info(f"Converted DOCX to PDF: {converted_path}")
            return await self._load_pdf(converted_path)
        finally:
            if converted_path != file_path:
                self._file_converter.clear(converted_path)
                logger.info(f"Cleared converted files: {converted_path}")

    # ------------------------------------------------------------------ #
    #  PPTX — chaque slide traitée comme image (type forcé workflow)     #
    # ------------------------------------------------------------------ #
    async def _load_pptx(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        logger.info(f"Processing PPTX file: {file_path}")

        image_paths: List[str] = self._file_converter.pptx_to_images(file_path)

        pages: List[PageContent] = []
        slide_number = 0
        try:
            for slide_number, image_path in enumerate(image_paths, start=1):
                content = await self._processor.process_pptx_slide(image_path, slide_number)

                pages.append(
                    PageContent(
                        page_number=slide_number,
                        content_type="workflow",
                        header="",
                        text=content.get("text", ""),
                        has_table=content.get("has_table", False),
                        tables_metadata=content.get("tables_metadata", []),
                    )
                )
            logger.info(f"Processed slide {slide_number}/{len(image_paths)}")

        finally:
            if image_paths:
                self._file_converter.clear(image_paths[0])
                logger.info("Cleared PPTX slides folder")

        return pages, []

    # ------------------------------------------------------------------ #
    #  PDF — pipeline Azure DI complet                                    #
    # ------------------------------------------------------------------ #
    async def _load_pdf(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        logger.info(f"Processing PDF file: {file_path}")

        az_result = self._client.analyze_file(file_path)

        headings: List[SectionHeading] = self._extract_section_headings(az_result)

        pages: List[PageContent] = []
        for page in az_result.pages:
            has_keyword = self._has_workflow_keyword(page, az_result)
            label = self._page_classifier.classify(page, has_keyword)

            if label == "workflow":
                content = await self._processor.process_workflow_page(page, file_path)
            else:
                header_contents = self._extractor.extract_page_header_contents(
                    page.page_number, az_result
                )
                content = self._extractor.extract_text_page(page, az_result, header_contents)

            pages.append(
                PageContent(
                    page_number=page.page_number,
                    content_type=content.get("type", "text"),
                    header="",
                    text=content.get("text", ""),
                    has_table=content.get("has_table", False),
                    tables_metadata=content.get("tables_metadata", []),
                )
            )
            logger.info(f"Processed page {page.page_number}/{len(az_result.pages)} ({label})")

        # Classification du document basé sur la densité d'articles
        article_keywords = ["المادة", "مادة"]
        is_article_doc = self.classify_document_by_article_density(
            headings, article_keywords, len(az_result.pages)
        )

        if is_article_doc:
            headings = self.filter_section_headings_by_keywords(headings, article_keywords)
            for page in pages:
                page.content_type = "article"
            logger.info("Document classified as article type based on headings density")

        return pages, headings

    # ------------------------------------------------------------------ #
    #  Helpers internes                                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_section_headings(az_result) -> List[SectionHeading]:
        headings = []
        for paragraph in (az_result.paragraphs or []):
            if paragraph.role not in ("title", "sectionHeading"):
                continue
            page_number, x_pos, y_pos = 1, 0.0, 0.0
            if paragraph.bounding_regions:
                region = paragraph.bounding_regions[0]
                page_number = region.page_number
                if region.polygon:
                    poly = region.polygon
                    x_pos = poly[0].x if hasattr(poly[0], "x") else poly[0]
                    y_pos = poly[0].y if hasattr(poly[0], "y") else poly[1]
            headings.append(
                SectionHeading(
                    content=paragraph.content,
                    page_number=page_number,
                    y_position=y_pos,
                    x_position=x_pos,
                )
            )
        headings.sort(key=lambda h: (h.page_number, h.y_position))
        return headings

    @staticmethod
    def _has_workflow_keyword(page, az_result) -> bool:
        workflow_keywords = ["رموز"]
        for table in az_result.tables or []:
            for region in table.bounding_regions:
                if region.page_number == page.page_number:
                    first_row_cells = [
                        cell.content for cell in table.cells if cell.row_index == 0
                    ]
                    for cell_content in first_row_cells:
                        cell_text = cell_content.replace(" ", "").strip()
                        for kw in workflow_keywords:
                            if kw in cell_text:
                                return True
        return False

    # ------------------------------------------------------------------ #
    #  Classification document                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def classify_document_by_article_density(
        headings: List[SectionHeading],
        keywords: list,
        total_pages: int,
    ) -> bool:
        if total_pages == 0:
            return False
        article_pages: Set[int] = {
            h.page_number
            for h in headings
            if h.content and any(k in h.content for k in keywords)
        }
        return (len(article_pages) / total_pages) > 0.5

    @staticmethod
    def filter_section_headings_by_keywords(
        headings: List[SectionHeading],
        keywords: list,
    ) -> List[SectionHeading]:
        if not headings:
            return []

        filtered: List[SectionHeading] = []
        started = False

        for heading in headings:
            has_keyword = heading.content and any(k in heading.content for k in keywords)
            if not started:
                filtered.append(heading)
                if has_keyword:
                    started = True
            else:
                if has_keyword:
                    filtered.append(heading)

        return filtered