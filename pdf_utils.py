"""Utility functions for reading PDF files from student folders."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PDF_EXTENSIONS = {".pdf", ".PDF"}


def extract_texts_from_student(student_id: str, input_dir: str = "input") -> dict[str, str]:
    """Read all PDFs in a student's folder and extract text content.

    Args:
        student_id: Folder name (e.g. "alumno_001").
        input_dir: Base input directory.

    Returns:
        {filename: text_content} for each readable PDF.
    """
    folder = Path(input_dir) / student_id
    if not folder.exists() or not folder.is_dir():
        logger.warning(f"Carpeta no encontrada: {folder}")
        return {}

    pdf_files = sorted(
        [f for f in folder.iterdir() if f.suffix in PDF_EXTENSIONS]
    )
    if not pdf_files:
        logger.warning(f"No se encontraron PDFs en {folder}")
        return {}

    texts = {}
    for pdf_path in pdf_files:
        text = _extract_pdf_text(pdf_path)
        if text and text.strip():
            texts[pdf_path.name] = text
            logger.info(f"  Leídos {len(text)} caracteres de {pdf_path.name}")
        else:
            logger.warning(f"  No se pudo extraer texto de {pdf_path.name}")

    return texts


def _extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF using multiple strategies."""
    text = ""
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(str(pdf_path))
        if text.strip():
            return text
    except Exception as e:
        logger.debug(f"pdfminer failed for {pdf_path.name}: {e}")

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception as e:
        logger.debug(f"PyPDF2 failed for {pdf_path.name}: {e}")

    return text
