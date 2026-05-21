"""Utility functions for reading PDF files from student folders."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PDF_EXTENSIONS = {".pdf", ".PDF"}

# Umbral mínimo de caracteres para considerar que un PDF tiene texto real
# Si tras extraer con pdfminer/PyPDF2 obtenemos menos, se activa OCR
OCR_TEXT_THRESHOLD = 20


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
    """Extract text from a PDF using multiple strategies.

    Intenta primero extracción directa de texto (pdfminer, PyPDF2).
    Si el resultado es muy corto o vacío, cae en OCR con Tesseract
    por si el PDF es un escaneado (imagen).
    """
    text = ""
    # --- Estrategia 1: pdfminer ---
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(str(pdf_path))
        if len(text.strip()) >= OCR_TEXT_THRESHOLD:
            return text
    except Exception as e:
        logger.debug(f"pdfminer failed for {pdf_path.name}: {e}")

    # --- Estrategia 2: PyPDF2 ---
    if len(text.strip()) < OCR_TEXT_THRESHOLD:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(pdf_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if len(text.strip()) >= OCR_TEXT_THRESHOLD:
                return text
        except Exception as e:
            logger.debug(f"PyPDF2 failed for {pdf_path.name}: {e}")

    # --- Estrategia 3: OCR con Tesseract (para PDFs escaneados) ---
    if len(text.strip()) < OCR_TEXT_THRESHOLD:
        ocr_text = _ocr_pdf(pdf_path)
        if ocr_text:
            logger.info(f"  OCR aplicado a {pdf_path.name} ({len(ocr_text)} caracteres)")
            return ocr_text

    return text


def _ocr_pdf(pdf_path: Path) -> str:
    """Convierte un PDF a imágenes y extrae texto mediante Tesseract OCR."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        logger.warning(
            "OCR no disponible. Instala: pip install pytesseract pdf2image\n"
            "  Además necesitas Tesseract: https://github.com/tesseract-ocr/tesseract\n"
            "  y poppler: https://github.com/oschwartz10612/poppler-windows/releases/"
        )
        return ""

    try:
        images = convert_from_path(str(pdf_path), dpi=300)
    except Exception as e:
        logger.debug(f"pdf2image failed for {pdf_path.name}: {e}")
        return ""

    texts = []
    for i, img in enumerate(images):
        try:
            page_text = pytesseract.image_to_string(img, lang="spa+eng")
            texts.append(page_text)
        except Exception as e:
            logger.debug(f"Tesseract failed on page {i+1} of {pdf_path.name}: {e}")

    return "\n".join(texts) if texts else ""
