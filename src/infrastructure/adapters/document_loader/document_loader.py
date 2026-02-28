from typing import List, Tuple, Set

from src.domain.exceptions.document_loader_exception import DocumentLoaderException
from src.domain.models.page_content_model import PageContent
from src.domain.models.section_heading_model import SectionHeading
from src.domain.ports.input.document_loader_port import DocumentLoaderPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.document_loader.azure_client_adapter import AzureDocumentClient
from src.infrastructure.adapters.document_loader.page_processing import PageProcessor
from src.infrastructure.adapters.document_loader.text_extractor import TextExtractor


class DocumentLoader(DocumentLoaderPort):
    """Orchestration principale pour le chargement et traitement d'un document."""

    def __init__(self, prompt_provider: PromptProviderPort):
        self._client = AzureDocumentClient()
        self._processor = PageProcessor(prompt_provider)
        self._extractor = TextExtractor()

    # ------------------------------------------------------------------ #
    #  Point d'entrée public                                               #
    # ------------------------------------------------------------------ #
    def load(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        if not file_path:
            raise DocumentLoaderException("Le chemin du fichier ne peut pas être vide.")

        az_result = self._client.analyze_file(file_path)

        # Extraction des headings
        headings: List[SectionHeading] = self._extract_section_headings(az_result)

        pages: List[PageContent] = []
        for page in az_result.pages:
            # Classification basique : workflow vs texte
            label = self._has_workflow_keyword(page, az_result)

            if label:
                content = self._processor.process_workflow_page(page, file_path)
            else:
                # Fallback texte brut si pas workflow
                content_text = self._extract_text_page(page, az_result)
                content = {
                    "type": "text",
                    "text": content_text,
                    "has_table": bool(self._extractor.extract_tables_metadata(content_text)),
                    "tables_metadata": self._extractor.extract_tables_metadata(content_text),
                }

            pages.append(
                PageContent(
                    page_number=page.page_number,
                    content_type=content.get("type", "text"),
                    header="",  # Ici, tu peux ajouter header via _build_header_string
                    text=content.get("text", ""),
                    has_table=content.get("has_table", False),
                    tables_metadata=content.get("tables_metadata", []),
                )
            )

        # Classification du document basé sur la densité d'articles
        article_keywords = ["المادة", "مادة"]
        is_article_doc = self.classify_document_by_article_density(
            headings, article_keywords, len(az_result.pages)
        )

        if is_article_doc:
            headings = self.filter_section_headings_by_keywords(headings, article_keywords)
            for page in pages:
                page.content_type = "article"

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
                    first_row_cells = [cell.content for cell in table.cells if cell.row_index == 0]
                    for cell_content in first_row_cells:
                        cell_text = cell_content.replace(" ", "").strip()
                        for kw in workflow_keywords:
                            if kw in cell_text:
                                return True
        return False

    @staticmethod
    def _extract_text_page(page, az_result) -> str:
        """Fallback extraction texte brut par page (sans workflow)."""
        segments = []
        for para in (az_result.paragraphs or []):
            if para.bounding_regions and para.bounding_regions[0].page_number == page.page_number:
                segments.append(para.content.strip())
        return "\n\n".join([s for s in segments if s])

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
            if h.content and any(
                k in h.content for k in keywords
            )
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