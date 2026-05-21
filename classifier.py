import logging
from pathlib import Path

from llm_client import LLMClient

logger = logging.getLogger(__name__)

DOC_TYPES = {"solicitud", "carta_aceptacion", "expediente_academico", "nota_media", "cv"}


class Classifier:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def classify(self, pdf_texts: dict[str, str]) -> dict[str, list[dict]]:
        """Classify each PDF text and return mapping of doc types to file info.

        Args:
            pdf_texts: {filename: text_content}

        Returns:
            {doc_type: [{"file": filename, "confianza": "...", "text": text}, ...]}
        """
        result: dict[str, list[dict]] = {}
        for fname, text in pdf_texts.items():
            if not text.strip():
                logger.warning(f"Empty text for {fname}, skipping")
                continue
            try:
                cls = self.llm.classify_document(text)
            except Exception as e:
                logger.error(f"Error classifying {fname}: {e}")
                result.setdefault("desconocido", []).append({"file": fname, "error": str(e)})
                continue

            categoria = cls.get("categoria", "desconocido")
            entry = {
                "file": fname,
                "confianza": cls.get("confianza", "BAJA"),
                "justificacion": cls.get("justificacion", ""),
                "text": text,
            }
            result.setdefault(categoria, []).append(entry)
            logger.info(f"  {fname} → {categoria} ({entry['confianza']})")

        return result

    def get_best_per_type(self, classified: dict[str, list[dict]]) -> dict[str, dict]:
        """Pick the best file per doc type (highest confidence, first by priority)."""
        order = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        best = {}
        for dtype in DOC_TYPES:
            items = classified.get(dtype, [])
            if not items:
                continue
            items_sorted = sorted(items, key=lambda x: order.get(x["confianza"], 99))
            best[dtype] = items_sorted[0]
        return best
