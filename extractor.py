import logging

from llm_client import LLMClient

logger = logging.getLogger(__name__)


class Extractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_all(self, classified: dict[str, list[dict]]) -> dict:
        """Extract structured data for every classified document type.

        Args:
            classified: {doc_type: [{"file": ..., "text": ..., "confianza": ...}, ...]}

        Returns:
            {doc_type: {"file": ..., "datos": {...}, "confianza": ...}, ...}
        """
        extracted = {}
        for categoria, items in classified.items():
            if not items:
                continue
            if categoria == "desconocido":
                continue
            best = items[0]
            text = best["text"]
            try:
                data = self.llm.extract_data(categoria, text)
            except Exception as e:
                logger.error(f"Error extracting data from {categoria}: {e}")
                data = {"error": str(e)}

            extracted[categoria] = {
                "file": best["file"],
                "confianza": best.get("confianza", "BAJA"),
                "datos": data,
            }
            logger.info(f"  Extraídos datos de {categoria} desde {best['file']}")

        return extracted
