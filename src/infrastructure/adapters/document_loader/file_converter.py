"""
FileConverter — Rendu fidèle des slides PPTX en PNG et conversion DOCX → PDF.

Stratégie par plateforme :
    Windows  → Word COM (win32com)       pour DOCX → PDF  (arabe / RTL natif)
               PowerPoint COM (win32com)  pour PPTX → PNG  (pixel-perfect)
    Linux    → LibreOffice headless      pour DOCX → PDF et PPTX → PNG
    macOS    → LibreOffice headless      pour DOCX → PDF et PPTX → PNG

Dépendances :
    Windows     : pip install pywin32   (Word + PowerPoint COM)
    Linux/macOS : apt install libreoffice  /  brew install libreoffice
    Fallback PDF→PNG : pip install pymupdf
"""
import logging
import platform
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import List
import win32com.client
import fitz

from src.domain.exceptions.document_loader_exception import DocumentLoaderException
from src.infrastructure.adapters.config.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

CONVERTED_DOCS_DIR = Path(__file__).resolve().parents[4] / "converted_docs"


class FileConverter:
    """Convertit .pptx / .docx en PDF ou en images — cross-platform."""

    CONVERTIBLE_EXTENSIONS = {".pptx", ".docx"}

    def __init__(self, output_dir: Path = CONVERTED_DOCS_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileConverter initialized with output directory: {self.output_dir}")


    # ------------------------------------------------------------------ #
    #  Context manager — .docx / .pptx → PDF                             #
    # ------------------------------------------------------------------ #
    @contextmanager
    def as_pdf_if_needed(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        if ext not in self.CONVERTIBLE_EXTENSIONS:
            yield file_path
            return
        pdf_path = self.convert_to_pdf(file_path)
        yield pdf_path

    # ------------------------------------------------------------------ #
    #  PPTX → une PNG par slide                                          #
    # ------------------------------------------------------------------ #
    def pptx_to_images(
        self,
        pptx_path: str,
        width: int = 3840,
        height: int = 2160,
    ) -> List[str]:
        pptx_path_obj = Path(pptx_path)
        if not pptx_path_obj.exists():
            raise DocumentLoaderException(f"Fichier introuvable : {pptx_path}")

        slide_dir = self.output_dir / pptx_path_obj.stem
        slide_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Converting PPTX to images: {pptx_path} → {slide_dir}")

        if platform.system() == "Windows":
            return self._pptx_to_images_windows(
                str(pptx_path_obj.resolve()), slide_dir, width, height
            )
        else:
            return self._pptx_to_images_libreoffice(
                str(pptx_path_obj.resolve()), slide_dir
            )

    # ------------------------------------------------------------------ #
    #  Conversion vers PDF (dispatch plateforme)                         #
    # ------------------------------------------------------------------ #
    def convert_to_pdf(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        logger.info(f"Converting {file_path} to PDF")

        if ext == ".docx":
            if platform.system() == "Windows":
                return self._docx_to_pdf_word_com(file_path)
            else:
                return self._to_pdf_libreoffice(file_path)
        if ext == ".pptx":
            return self._to_pdf_libreoffice(file_path)
        raise DocumentLoaderException(f"Extension non supportée : {ext}")

    # ------------------------------------------------------------------ #
    #  DOCX → PDF via Word COM  (Windows — supporte arabe / RTL)        #
    # ------------------------------------------------------------------ #
    def _docx_to_pdf_word_com(self, file_path: str) -> str:
        """Utilise Microsoft Word via COM pour exporter en PDF.

        Word gère nativement l'arabe, le RTL et toutes les polices — aucune
        dégradation du texte, contrairement à ReportLab.
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise DocumentLoaderException(f"Fichier introuvable : {file_path}")

        dest_pdf = self.output_dir / f"{file_path_obj.stem}.pdf"
        logger.info(f"Converting DOCX to PDF via Word COM: {file_path} → {dest_pdf}")

        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False

            doc = word.Documents.Open(
                str(file_path_obj.resolve()),
                ReadOnly=True,
            )
            doc.SaveAs2(str(dest_pdf.resolve()), FileFormat=17)
            logger.info(f"Successfully converted DOCX to PDF: {dest_pdf}")

        except DocumentLoaderException:
            raise
        except Exception as e:
            logger.error(f"Failed Word COM export for {file_path_obj.name}: {e}")
            raise DocumentLoaderException(
                f"Échec export Word COM ({file_path_obj.name}) : {e}"
            ) from e
        finally:
            if doc is not None:
                try:
                    doc.Close(False)  # False = ne pas sauvegarder
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass

        if not dest_pdf.exists():
            logger.error(f"PDF not found after conversion: {dest_pdf}")
            raise DocumentLoaderException(
                f"PDF introuvable après conversion Word COM : {dest_pdf}"
            )

        return str(dest_pdf)

    # ------------------------------------------------------------------ #
    #  → PDF via LibreOffice headless  (Linux / macOS)                  #
    # ------------------------------------------------------------------ #
    def _to_pdf_libreoffice(self, file_path: str) -> str:
        """Convertit DOCX ou PPTX en PDF via LibreOffice headless."""
        file_path_obj = Path(file_path)
        logger.info(f"Converting {file_path} to PDF via LibreOffice headless")

        if not file_path_obj.exists():
            logger.error(f"LibreOffice →PDF failed: {file_path}")
            raise DocumentLoaderException(f"Fichier introuvable : {file_path}")

        libreoffice_cmd = self._find_libreoffice()

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    libreoffice_cmd,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmp_dir,
                    str(file_path_obj.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise DocumentLoaderException(
                    f"LibreOffice →PDF failed ({file_path_obj.name}) : "
                    f"{result.stderr.strip()}"
                )

            tmp_pdfs = list(Path(tmp_dir).glob("*.pdf"))
            if not tmp_pdfs:
                raise DocumentLoaderException(
                    f"LibreOffice n'a produit aucun PDF depuis : {file_path}"
                )

            dest_pdf = self.output_dir / f"{file_path_obj.stem}.pdf"
            shutil.copy2(str(tmp_pdfs[0]), str(dest_pdf))
            logger.info(f"LibreOffice conversion succeeded: {dest_pdf}")

        return str(dest_pdf)

    # ------------------------------------------------------------------ #
    #  Windows — PowerPoint COM (PPTX → PNG)                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _pptx_to_images_windows(
        pptx_path: str,
        slide_dir: Path,
        width: int,
        height: int,
    ) -> List[str]:
        logger.info("Starting PPTX → PNG conversion on Windows: %s", pptx_path)

        powerpoint = None
        prs = None
        image_paths: List[str] = []

        try:
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            powerpoint.Visible = 0

            prs = powerpoint.Presentations.Open(
                pptx_path,
                ReadOnly=True,
                Untitled=False,
                WithWindow=True,
            )

            time.sleep(2)

            slide_count = prs.Slides.Count
            if slide_count == 0:
                raise DocumentLoaderException(
                    f"PowerPoint a ouvert '{Path(pptx_path).name}' mais "
                    "signale 0 slides. Le fichier est peut-être protégé ou corrompu."
                )

            for i in range(1, slide_count + 1):
                output_path = str((slide_dir / f"slide_{i:03d}.png").resolve())
                prs.Slides(i).Export(output_path, "PNG", width, height)
                image_paths.append(output_path)
                logger.info("Exported slide %d → %s", i, output_path)

        except DocumentLoaderException:
            raise
        except Exception as e:
            logger.error("Échec export PowerPoint COM (%s): %s", Path(pptx_path).name, e)
            raise DocumentLoaderException(
                f"Échec export PowerPoint COM ({Path(pptx_path).name}) : {e}"
            ) from e
        finally:
            if prs is not None:
                try:
                    prs.Close()
                except Exception:
                    pass
            if powerpoint is not None:
                try:
                    powerpoint.Quit()
                except Exception:
                    pass

        if not image_paths:
            raise DocumentLoaderException(
                f"Aucune slide exportée depuis : {pptx_path}"
            )
        return image_paths

    # ------------------------------------------------------------------ #
    #  Linux / macOS — LibreOffice headless (PPTX → PNG)               #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _pptx_to_images_libreoffice(
        pptx_path: str,
        slide_dir: Path,
    ) -> List[str]:
        logger.info("Starting PPTX → PNG conversion via LibreOffice: %s", pptx_path)

        libreoffice_cmd = FileConverter._find_libreoffice()

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    libreoffice_cmd,
                    "--headless",
                    "--convert-to", "png",
                    "--outdir", tmp_dir,
                    pptx_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.error("LibreOffice conversion failed: %s", result.stderr.strip())
                raise DocumentLoaderException(
                    f"LibreOffice conversion failed : {result.stderr.strip()}"
                )

            tmp_pngs = sorted(Path(tmp_dir).glob("*.png"))

            if tmp_pngs:
                image_paths: List[str] = []
                for idx, png in enumerate(tmp_pngs, start=1):
                    dest = slide_dir / f"slide_{idx:03d}.png"
                    shutil.copy2(str(png), str(dest))
                    image_paths.append(str(dest))
                    logger.info("Exported slide %d → %s", idx, dest)
                return image_paths

            # Fallback : LibreOffice a produit un PDF → découpe avec fitz
            tmp_pdfs = list(Path(tmp_dir).glob("*.pdf"))
            if tmp_pdfs:
                logger.warning("LibreOffice produced PDF instead of PNG, falling back to PyMuPDF")
                return FileConverter._pdf_to_images_fitz(
                    str(tmp_pdfs[0]), slide_dir
                )

            raise DocumentLoaderException(
                f"LibreOffice n'a produit aucune image depuis : {pptx_path}"
            )

    @staticmethod
    def _pdf_to_images_fitz(pdf_path: str, slide_dir: Path) -> List[str]:
        """Convertit un PDF en PNG par page via PyMuPDF."""

        logger.info("Converting PDF → PNG via PyMuPDF: %s", pdf_path)

        doc = fitz.open(pdf_path)
        image_paths: List[str] = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            output_path = slide_dir / f"slide_{page_num + 1:03d}.png"
            pix.save(str(output_path))
            image_paths.append(str(output_path))
            logger.info("Exported PDF page %d → %s", page_num + 1, output_path)

        doc.close()
        return image_paths

    # ------------------------------------------------------------------ #
    #  Utilitaires                                                        #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_libreoffice() -> str:
        candidates = [
            "libreoffice",
            "soffice",
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
            "/usr/local/bin/libreoffice",
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        ]
        for cmd in candidates:
            if shutil.which(cmd):
                logger.info("Found LibreOffice executable: %s", cmd)
                return cmd
        raise DocumentLoaderException(
            "LibreOffice introuvable. "
            "Linux : apt-get install libreoffice | "
            "macOS : brew install libreoffice"
        )

    # ------------------------------------------------------------------ #
    #  Nettoyage des fichiers convertis après traitement                  #
    # ------------------------------------------------------------------ #
    def clear(self, file_path: str) -> None:
        """Supprime le fichier converti et son dossier de slides si présent.

        À appeler après que le traitement du document est terminé.
        """
        file_path_obj = Path(file_path)

        # Supprimer le fichier lui-même (PDF converti, etc.)
        if file_path_obj.exists():
            try:
                file_path_obj.unlink()
                logger.info("Deleted converted file: %s", file_path_obj)
            except Exception as e:
                logger.warning("Impossible de supprimer %s : %s", file_path_obj.name, e)

        # Supprimer le dossier de slides PNG si présent (même nom sans extension)
        slide_dir = self.output_dir / file_path_obj.stem
        if slide_dir.exists() and slide_dir.is_dir():
            try:
                shutil.rmtree(slide_dir)
                logger.info("Deleted slide directory: %s", slide_dir)
            except Exception as e:
                logger.warning("Impossible de supprimer le dossier %s : %s", slide_dir.name, e)