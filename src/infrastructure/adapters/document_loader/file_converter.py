"""Convert DOCX/PPTX to PDF or images for downstream processing.

Platform strategy:
    - Windows: Word COM for DOCX -> PDF, PowerPoint COM for PPTX -> PNG.
    - Linux/macOS: LibreOffice headless for DOCX/PPTX conversions.
    - Fallback: PyMuPDF for PDF -> PNG.
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
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

CONVERTED_DOCS_DIR = Path(__file__).resolve().parents[4] / "converted_docs"


class FileConverter:
    """Convert PPTX/DOCX to PDF or PNG images across platforms."""

    CONVERTIBLE_EXTENSIONS = {".pptx", ".docx"}

    def __init__(self, output_dir: Path = CONVERTED_DOCS_DIR):
        """Initialize the converter.

        :param output_dir: Output directory for converted files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("FileConverter initialized with output directory: %s", self.output_dir)
    @contextmanager
    def as_pdf_if_needed(self, file_path: str):
        """Yield a PDF path, converting if needed.

        :param file_path: Input file path.
        :return: PDF path as a context-managed value.
        """
        ext = Path(file_path).suffix.lower()
        if ext not in self.CONVERTIBLE_EXTENSIONS:
            yield file_path
            return
        pdf_path = self.convert_to_pdf(file_path)
        yield pdf_path

    def pptx_to_images(
        self,
        pptx_path: str,
        width: int = 3840,
        height: int = 2160,
    ) -> List[str]:
        """Convert a PPTX file to PNG images.

        :param pptx_path: Path to the PPTX file.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :return: List of image paths.
        :raises DocumentLoaderException: If the file is missing or conversion fails.
        """
        pptx_path_obj = Path(pptx_path)
        if not pptx_path_obj.exists():
            raise DocumentLoaderException(f"Fichier introuvable : {pptx_path}")

        slide_dir = self.output_dir / pptx_path_obj.stem
        slide_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Converting PPTX to images: %s -> %s", pptx_path, slide_dir)

        if platform.system() == "Windows":
            return self._pptx_to_images_windows(
                str(pptx_path_obj.resolve()), slide_dir, width, height
            )
        else:
            return self._pptx_to_images_libreoffice(
                str(pptx_path_obj.resolve()), slide_dir
            )

    def convert_to_pdf(self, file_path: str) -> str:
        """Convert a DOCX or PPTX file to PDF.

        :param file_path: Path to the input file.
        :return: Path to the generated PDF.
        :raises DocumentLoaderException: If the extension is unsupported or conversion fails.
        """
        ext = Path(file_path).suffix.lower()
        logger.info("Converting %s to PDF", file_path)

        if ext == ".docx":
            if platform.system() == "Windows":
                return self._docx_to_pdf_word_com(file_path)
            else:
                return self._to_pdf_libreoffice(file_path)
        if ext == ".pptx":
            return self._to_pdf_libreoffice(file_path)
        raise DocumentLoaderException(f"Extension non supportée : {ext}")

    def _docx_to_pdf_word_com(self, file_path: str) -> str:
        """Convert DOCX to PDF using Word COM on Windows.

        :param file_path: Path to the DOCX file.
        :return: Path to the generated PDF.
        :raises DocumentLoaderException: If conversion fails.
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise DocumentLoaderException(f"Fichier introuvable : {file_path}")

        dest_pdf = self.output_dir / f"{file_path_obj.stem}.pdf"
        logger.info("Converting DOCX to PDF via Word COM: %s -> %s", file_path, dest_pdf)

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
            logger.info("Successfully converted DOCX to PDF: %s", dest_pdf)

        except DocumentLoaderException:
            raise
        except Exception as e:
            logger.error("Failed Word COM export for %s: %s", file_path_obj.name, e)
            raise DocumentLoaderException(
                f"Échec export Word COM ({file_path_obj.name}) : {e}"
            ) from e
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass

        if not dest_pdf.exists():
            logger.error("PDF not found after conversion: %s", dest_pdf)
            raise DocumentLoaderException(
                f"PDF introuvable après conversion Word COM : {dest_pdf}"
            )

        return str(dest_pdf)

    def _to_pdf_libreoffice(self, file_path: str) -> str:
        """Convert DOCX or PPTX to PDF using LibreOffice.

        :param file_path: Path to the input file.
        :return: Path to the generated PDF.
        :raises DocumentLoaderException: If conversion fails.
        """
        file_path_obj = Path(file_path)
        logger.info("Converting %s to PDF via LibreOffice headless", file_path)

        if not file_path_obj.exists():
            logger.error("LibreOffice -> PDF failed: %s", file_path)
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
            logger.info("LibreOffice conversion succeeded: %s", dest_pdf)

        return str(dest_pdf)

    @staticmethod
    def _pptx_to_images_windows(
        pptx_path: str,
        slide_dir: Path,
        width: int,
        height: int,
    ) -> List[str]:
        """Convert PPTX to PNG images using PowerPoint COM.

        :param pptx_path: Path to the PPTX file.
        :param slide_dir: Output directory for images.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :return: List of image paths.
        :raises DocumentLoaderException: If conversion fails.
        """
        logger.info("Starting PPTX -> PNG conversion on Windows: %s", pptx_path)

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
                logger.info("Exported slide %d -> %s", i, output_path)

        except DocumentLoaderException:
            raise
        except Exception as e:
            logger.error("PowerPoint COM export failed (%s): %s", Path(pptx_path).name, e)
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

    @staticmethod
    def _pptx_to_images_libreoffice(
        pptx_path: str,
        slide_dir: Path,
    ) -> List[str]:
        """Convert PPTX to PNG images using LibreOffice.

        :param pptx_path: Path to the PPTX file.
        :param slide_dir: Output directory for images.
        :return: List of image paths.
        :raises DocumentLoaderException: If conversion fails.
        """
        logger.info("Starting PPTX -> PNG conversion via LibreOffice: %s", pptx_path)

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
                    logger.info("Exported slide %d -> %s", idx, dest)
                return image_paths

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
        """Convert a PDF to PNG images using PyMuPDF.

        :param pdf_path: Path to the PDF file.
        :param slide_dir: Output directory for images.
        :return: List of image paths.
        """

        logger.info("Converting PDF -> PNG via PyMuPDF: %s", pdf_path)

        doc = fitz.open(pdf_path)
        image_paths: List[str] = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            output_path = slide_dir / f"slide_{page_num + 1:03d}.png"
            pix.save(str(output_path))
            image_paths.append(str(output_path))
            logger.info("Exported PDF page %d -> %s", page_num + 1, output_path)

        doc.close()
        return image_paths

    @staticmethod
    def _find_libreoffice() -> str:
        """Locate the LibreOffice executable on the system.

        :return: Command name or full path to LibreOffice.
        :raises DocumentLoaderException: If LibreOffice is not found.
        """
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

    def clear(self, file_path: str) -> None:
        """Delete converted files and any slide directories.

        :param file_path: Path to the converted file.
        :return: None.
        """
        file_path_obj = Path(file_path)

        if file_path_obj.exists():
            try:
                file_path_obj.unlink()
                logger.info("Deleted converted file: %s", file_path_obj)
            except Exception as e:
                logger.warning("Impossible de supprimer %s : %s", file_path_obj.name, e)

        slide_dir = self.output_dir / file_path_obj.stem
        if slide_dir.exists() and slide_dir.is_dir():
            try:
                shutil.rmtree(slide_dir)
                logger.info("Deleted slide directory: %s", slide_dir)
            except Exception as e:
                logger.warning("Impossible de supprimer le dossier %s : %s", slide_dir.name, e)