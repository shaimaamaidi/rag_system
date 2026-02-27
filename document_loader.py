import os
import re
import fitz
import json
from dotenv import load_dotenv
from datetime import datetime
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature, ParagraphRole
from azure.core.credentials import AzureKeyCredential
from pathlib import Path

from AzureWorkflowConverter import AzureWorkflowConverter
from LlamaOCRProcessor import LlamaOCRProcessor
from page_classifier import PageClassifier


@dataclass
class PageContent:
    page_number: int
    content_type: str
    header: str
    text: str
    has_table: bool
    tables_metadata: list

@dataclass
class SectionHeading:
    content:     str
    page_number: int
    y_position:  float
    x_position:  float

class DocumentLoader:
    def __init__(self):
        load_dotenv()
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        self.classifier = PageClassifier()

        self.llama_processor = LlamaOCRProcessor()
        self.azure_converter = AzureWorkflowConverter()

    def load(self, file_path: str) -> Tuple[List[PageContent], List[SectionHeading]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        print(f"\n{'=' * 60}")
        print(f"🔍  Analyse : {file_path}")
        print(f"{'=' * 60}")

        with open(file_path, "rb") as f:

            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=f,
                features=[DocumentAnalysisFeature.STYLE_FONT]
            )


        az_result = poller.result()

        print(f"✅  {len(az_result.pages)} page(s) reçues — {datetime.now().strftime('%H:%M:%S')}\n")

        headings: List[SectionHeading] = DocumentLoader._extract_section_headings(az_result)
        pages: List[PageContent] = []
        for page in az_result.pages:
            pages.append(self._process_page(page, az_result, file_path))

        article_keywords = ["المادة", "مادة"]

        type_doc = DocumentLoader.classify_document_by_article_density(headings, article_keywords, len(az_result.pages) )

        if type_doc:
            print("chacha")
            headings=DocumentLoader.filter_section_headings_by_keywords(headings, article_keywords)
            for page in pages:
                page.content_type = "article"

        return pages, headings

    @staticmethod
    def _extract_header(page_number: int, result) -> str:

        header_parts = []

        for p in (result.paragraphs or []):
            if not p.bounding_regions:
                continue

            if p.bounding_regions[0].page_number != page_number:
                continue

            if str(p.role).endswith("pageHeader"):
                header_parts.append(p.content.strip())

        return " | ".join(header_parts)

    @staticmethod
    def _remove_header_from_text(text: str, header: str) -> str:
        if not header or not text:
            return text

        if header in text:
            text = text.replace(header, "", 1)

        return text.strip()

    @staticmethod
    def _has_key_word_in_header_table(page, result) -> bool:
        """
        Retourne True si :
        - Une cellule de la première ligne d'une table contient un mot-clé
        """
        workflow_keywords = ["رموز"]

        for table in result.tables or []:
            for region in table.bounding_regions:
                if region.page_number == page.page_number:
                    # Vérifier seulement la première ligne
                    first_row_cells = [
                        cell.content for cell in table.cells
                        if cell.row_index == 0
                    ]
                    for cell_content in first_row_cells:
                        cell_text = cell_content.replace(" ", "").strip()
                        for kw in workflow_keywords:
                            if kw in cell_text:
                                return True

        return False

    @staticmethod
    def _extract_text(page, result) -> dict:

        segments = []
        has_table = False
        tables_metadata = []

        for line in (page.lines or []):
            segments.append(line.content)

        for idx, table in enumerate(result.tables or []):
            for region in table.bounding_regions:
                if region.page_number == page.page_number:
                    has_table = True
                    tables_metadata.append({
                        "table_index": idx,
                        "rows": table.row_count,
                        "cols": table.column_count
                    })

        text = "\n".join(segments)

        return {
            "text": text,
            "has_table": has_table,
            "tables_metadata": tables_metadata
        }

    @staticmethod
    def _extract_text_page(page, az_result, header_contents: Set[str]) -> dict:
        page_num = page.page_number

        page_tables = []
        for table_idx, table in enumerate(az_result.tables):
            for region in table.bounding_regions:
                if region.page_number == page_num and region.polygon:
                    y_top = min(region.polygon[i] for i in range(1, len(region.polygon), 2))
                    y_bot = max(region.polygon[i] for i in range(1, len(region.polygon), 2))
                    x_min = min(region.polygon[i] for i in range(0, len(region.polygon), 2))
                    x_max = max(region.polygon[i] for i in range(0, len(region.polygon), 2))
                    page_tables.append({
                        "table_idx": table_idx,
                        "table":     table,
                        "y_top":     y_top,
                        "bbox":      (x_min, x_max, y_top, y_bot),
                    })

        has_table = bool(page_tables)
        table_boxes = [t["bbox"] for t in page_tables]

        tables_metadata = [
            {
                "table_index": t["table_idx"],
                "row_count": t["table"].row_count,
                "col_count": t["table"].column_count,
                "y_position": round(t["y_top"], 4),
            }
            for t in page_tables
        ]

        header_y_max = DocumentLoader._get_header_y_max(page.page_number, az_result)
        if header_y_max is not None:
            header_y_max += 0.10

        header_tokens: Set[str] = set()
        for hc in header_contents:
            for tok in hc.replace("/", " ").replace("|", " ").split():
                tok = tok.strip()
                if len(tok) >= 4:
                    header_tokens.add(tok)

        page_number_contents: Set[str] = set()
        for para in (az_result.paragraphs or []):
            role_str = str(getattr(para, "role", "")).upper()
            if "PAGE_NUMBER" in role_str or "PAGENUMBER" in role_str:
                for region in (para.bounding_regions or []):
                    if region.page_number == page.page_number:
                        page_number_contents.add(para.content.strip())

        def _is_header_fragment(line_content: str) -> bool:
            if not line_content:
                return False
            line_tokens = [
                t.strip()
                for t in line_content.replace("/", " ").replace("|", " ").split()
                if len(t.strip()) >= 4
            ]
            if not line_tokens:
                return False
            return all(tok in header_tokens for tok in line_tokens)

        segments = []
        for line in (page.lines or []):
            line_content = line.content.strip()
            line_y = DocumentLoader._line_y_center(line)

            if line_content in page_number_contents:
                continue
            if header_y_max is not None and line_y <= header_y_max:
                continue
            if line_content in header_contents:
                continue
            if any(line_content in hc or hc in line_content for hc in header_contents):
                continue
            if header_contents and _is_header_fragment(line_content):
                continue
            if DocumentLoader._line_in_table(line, table_boxes):
                continue

            segments.append((line_y, line.content))

        for t in page_tables:
            table_str = DocumentLoader._table_to_markdown(t["table"])
            segments.append((t["y_top"], table_str))

        segments.sort(key=lambda s: s[0])
        text = "\n\n".join(c for _, c in segments if c.strip())

        return {"type": "text", "text": text, "has_table": has_table, "tables_metadata": tables_metadata}

    @staticmethod
    def _line_in_table(line, boxes: list) -> bool:
        if not line.polygon or not boxes:
            return False
        x_coords = [line.polygon[i] for i in range(0, len(line.polygon), 2)]
        y_coords = [line.polygon[i] for i in range(1, len(line.polygon), 2)]
        lx = sum(x_coords) / len(x_coords)
        ly = sum(y_coords) / len(y_coords)
        return any(xn <= lx <= xx and yn <= ly <= yx for xn, xx, yn, yx in boxes)

    @staticmethod
    def _line_y_center(line) -> float:
        if not line.polygon:
            return 0.0
        y_coords = [line.polygon[i] for i in range(1, len(line.polygon), 2)]
        return sum(y_coords) / len(y_coords)

    @staticmethod
    def _table_to_markdown(table) -> str:
        grid = [[""] * table.column_count for _ in range(table.row_count)]
        for cell in table.cells:
            content = cell.content.replace("\n", " ").strip()
            grid[cell.row_index][cell.column_index] = content

        def _md_row(cells: list) -> str:
            return "| " + " | ".join(cells) + " |"

        header_row = _md_row(grid[0]) if grid else ""
        separator = "| " + " | ".join(["---"] * table.column_count) + " |"
        data_rows = [_md_row(row) for row in grid[1:]]

        lines = [header_row, separator] + data_rows
        return "\n".join(lines)

    @staticmethod
    def _extract_section_headings(az_result) -> List[SectionHeading]:
        headings = []
        for paragraph in (az_result.paragraphs or []):
            if paragraph.role not in ("title", "sectionHeading"):
                continue

            page_number = 1
            x_pos = 0.0
            y_pos = 0.0

            if paragraph.bounding_regions:
                region = paragraph.bounding_regions[0]
                page_number = region.page_number
                if region.polygon:
                    poly = region.polygon
                    if hasattr(poly[0], 'x'):
                        x_pos = poly[0].x
                        y_pos = poly[0].y
                    else:
                        x_pos = poly[0]
                        y_pos = poly[1]

            headings.append(SectionHeading(
                content=paragraph.content,
                page_number=page_number,
                y_position=y_pos,
                x_position=x_pos,
            ))

        headings.sort(key=lambda h: (h.page_number, h.y_position))
        return headings

    def _process_page(self, page, az_result, file_path) -> PageContent:
        label   = self.classifier.classify(page, DocumentLoader._has_key_word_in_header_table(page, az_result))

        header_contents = DocumentLoader._extract_page_header_contents(page.page_number, az_result)
        header_str = DocumentLoader._build_header_string(page.page_number, az_result)

        if label == "text":
            content = DocumentLoader._extract_text_page(page, az_result, header_contents)
        else:
            content = self._handle_workflow_page(page, az_result, file_path)

        # ── Extraire le page header ───────────────────────────────────────────

        # ── Supprimer le header du texte principal ────────────────────────────
        clean_text = self._remove_header_from_text(content.get("text", ""), header_str)

        return PageContent(
            page_number    = page.page_number,
            content_type   = content.get("type","text"),
            header         = header_str,
            text           = clean_text,
            has_table      = content.get("has_table", False),
            tables_metadata= content.get("tables_metadata", []),
        )

    @staticmethod
    def _extract_page_header_contents(page_number: int, az_result) -> Set[str]:
        page_paragraphs = []
        for para in (az_result.paragraphs or []):
            if not para.bounding_regions:
                continue
            region = para.bounding_regions[0]
            if region.page_number != page_number:
                continue
            poly = region.polygon or []
            if not poly:
                continue
            y = poly[1] if not hasattr(poly[0], 'y') else poly[0].y
            page_paragraphs.append((y, para))

        page_paragraphs.sort(key=lambda t: t[0])

        last_header_idx = -1
        for idx, (y, para) in enumerate(page_paragraphs):
            if para.role == ParagraphRole.PAGE_HEADER:
                last_header_idx = idx

        if last_header_idx == -1:
            return set()

        header_contents: Set[str] = set()
        for idx in range(last_header_idx + 1):
            _, para = page_paragraphs[idx]
            header_contents.add(para.content.strip())
        return header_contents

    @staticmethod
    def _build_header_string(page_number: int, az_result) -> str:
        page_paragraphs = []
        for para in (az_result.paragraphs or []):
            if not para.bounding_regions:
                continue
            region = para.bounding_regions[0]
            if region.page_number != page_number:
                continue
            poly = region.polygon or []
            if not poly:
                continue
            y = poly[1] if not hasattr(poly[0], 'y') else poly[0].y
            page_paragraphs.append((y, para))

        page_paragraphs.sort(key=lambda t: t[0])

        last_header_idx = -1
        for idx, (y, para) in enumerate(page_paragraphs):
            if para.role == ParagraphRole.PAGE_HEADER:
                last_header_idx = idx

        if last_header_idx == -1:
            return ""

        parts = [para.content.strip() for _, para in page_paragraphs[:last_header_idx + 1]]
        return " | ".join(p for p in parts if p)

    @staticmethod
    def _get_header_y_max(page_number: int, az_result) -> Optional[float]:
        page_paragraphs = []
        for para in (az_result.paragraphs or []):
            if not para.bounding_regions:
                continue
            region = para.bounding_regions[0]
            if region.page_number != page_number:
                continue
            poly = region.polygon or []
            if not poly:
                continue
            if hasattr(poly[0], 'y'):
                y_top = poly[0].y
                y_bot = max(p.y for p in poly)
            else:
                y_top = poly[1]
                y_bot = max(poly[i] for i in range(1, len(poly), 2))
            page_paragraphs.append((y_top, y_bot, para))

        page_paragraphs.sort(key=lambda t: t[0])

        last_header_y_bot = None
        for y_top, y_bot, para in page_paragraphs:
            if para.role == ParagraphRole.PAGE_HEADER:
                last_header_y_bot = y_bot

        return last_header_y_bot

    def _handle_workflow_page(self, page, az_result, file_path) -> dict:
        tmp_dir = "tmp_images"
        os.makedirs(tmp_dir, exist_ok=True)
        image_path = os.path.join(tmp_dir, f"page_{page.page_number}.png")

        # ── 1. Convertir la page en image ────────────────────────────────
        try:
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError("PDF source introuvable pour convertir en image")

            doc = fitz.open(file_path)
            pdf_page = doc.load_page(page.page_number - 1)

            rect = pdf_page.rect
            scale_x = 3840 / rect.width
            scale_y = 2160 / rect.height
            mat = fitz.Matrix(scale_x, scale_y)
            pix = pdf_page.get_pixmap(matrix=mat)
            pix.save(image_path)
            doc.close()

        except Exception as e:
            print(f"⚠️ Conversion page → image échouée : {e}")
            return DocumentLoader._extract_text_page(page, az_result, set())
        try:
            job_id = self.llama_processor.upload_image(image_path)
            workflow, pre_graph_content, post_graph_content, has_table = self.llama_processor.wait_for_completion(job_id)
        except Exception as e:
            print(f"❌ Llama OCR failed: {e}")
            return DocumentLoader._extract_text_page(page, az_result, set())

        # ── 3. Supprimer l'image temporaire ─────────────────────────────
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"⚠️ Impossible de supprimer l'image temporaire: {e}")

        # ── 4. Vérifier si Llama a renvoyé quelque chose ───────────────
        if not workflow.strip() and not pre_graph_content.strip() and not post_graph_content.strip():
            print("⚠️ Aucun texte extrait par Llama, fallback texte brut")
            return DocumentLoader._extract_text_page(page, az_result, set())

        # ── 5. Préparer le texte final pour le workflow ────────────────
        type="text"
        parts = []

        # 1️⃣ Contenu avant graph
        if pre_graph_content.strip():
            parts.append(pre_graph_content.strip())

        # 2️⃣ Workflow converti
        if workflow.strip():
            type="workflow"
            try:
                workflow_json = self.azure_converter.convert_to_json_workflow(workflow)
                workflow_text_str = json.dumps(workflow_json, ensure_ascii=False, indent=2)
                parts.append(workflow_text_str)
            except Exception as e:
                print(f"❌ Azure GPT-4o conversion failed: {e}")

        # 3️⃣ Contenu après graph
        if post_graph_content.strip():
            parts.append(post_graph_content.strip())

        final_text = "\n\n".join(parts)

        tables_metadata=[]
        if has_table:
            tables_metadata = DocumentLoader.extract_tables_metadata_from_text(pre_graph_content+"\n\n"+post_graph_content)
        return {
            "type": type,
            "text": final_text,
            "has_table": has_table,
            "tables_metadata": tables_metadata,
        }

    @staticmethod
    def extract_tables_metadata_from_text(post_graph_content: str) -> list:
        """
        Analyse post_graph_content pour trouver des tables Markdown ou HTML
        et renvoie une liste de metadata pour tables_metadata.

        Retour:
            [
                {
                    "table_index": 0,
                    "row_count": 3,
                    "col_count": 4
                },
                ...
            ]
        """
        tables_metadata = []

        # ── 1. Détecter les tableaux Markdown ────────────────────────────
        # Markdown simple : | col1 | col2 |
        markdown_table_pattern = re.compile(
            r"((?:\|.*\|\s*\n)+)",  # capture lines starting and ending with |
            re.MULTILINE
        )

        md_tables = markdown_table_pattern.findall(post_graph_content)
        for idx, table_text in enumerate(md_tables):
            lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
            if len(lines) < 2:
                continue  # pas de separator, probablement pas un tableau

            header = lines[0]
            separator = lines[1]  # ligne --- | --- | ---
            data_rows = lines[2:] if len(lines) > 2 else []

            col_count = header.count("|") - 1  # nombre de colonnes
            row_count = len(data_rows) + 1  # +1 pour l'en-tête

            tables_metadata.append({
                "table_index": idx,
                "row_count": row_count,
                "col_count": col_count
            })

        # ── 2. Détecter éventuellement les tableaux HTML simples ─────────
        html_table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE)
        html_tables = html_table_pattern.findall(post_graph_content)
        for idx, table_html in enumerate(html_tables, start=len(tables_metadata)):
            # compter les lignes <tr>
            rows = re.findall(r"<tr.*?>", table_html, re.IGNORECASE)
            # compter les colonnes via le premier <tr>
            cols = re.findall(r"<t[dh].*?>", table_html, re.IGNORECASE)
            row_count = len(rows)
            col_count = len(cols) if cols else 0
            tables_metadata.append({
                "table_index": idx,
                "row_count": row_count,
                "col_count": col_count
            })

        return tables_metadata

    @staticmethod
    def classify_document_by_article_density(
            headings: List[SectionHeading],
            keywords: List[str],
            total_pages: int
    ) -> bool:
        """
        Classifie le document selon la densité des articles.

        - Compte le nombre de pages contenant au moins un heading
          avec un mot-clé.
        - Calcule le ratio pages_article / total_pages.
        - Si ratio > 0.7 -> 'doc_article'
          sinon -> 'doc_normale'
        """

        if total_pages == 0:
            return False

        # Set des pages contenant au moins un article
        article_pages: Set[int] = {
            h.page_number
            for h in headings
            if h.content and any(
                k in re.sub(r'[^\u0600-\u06FF0-9\s]', '', h.content)
                for k in keywords
            )
        }

        ratio = len(article_pages) / total_pages

        if ratio > 0.5:
            return True
        else:
            return False

    @staticmethod
    def filter_section_headings_by_keywords(
            headings: List[SectionHeading],
            keywords: List[str]
    ) -> List[SectionHeading]:

        if not headings:
            return []

        # Trier par page puis position

        filtered: List[SectionHeading] = []
        started = False

        for heading in headings:
            content_clean = re.sub(r'[^\u0600-\u06FF0-9\s]', '', heading.content)
            has_keyword = (
                    heading.content
                    and any(k in content_clean for k in keywords)
            )

            if not started:
                # Avant premier article → on garde tout
                filtered.append(heading)

                if has_keyword:
                    started = True
            else:
                # Après premier article → on garde uniquement les articles
                if has_keyword:
                    filtered.append(heading)

        return filtered