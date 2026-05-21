import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StudentScore:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.puntuaciones: dict[str, float] = {}
        self.puntuacion_total: float = 0.0
        self.orden: int = 0

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "puntuaciones": self.puntuaciones,
            "puntuacion_total": round(self.puntuacion_total, 2),
            "orden": self.orden,
        }


class Scorer:
    """Aplica las reglas del baremo de forma determinista en Python."""

    # Pesos por tipo de documento (de config.json)
    BAREMO = {
        "nota_media": {"weight": 40, "max": 10},
        "expediente_academico": {"weight": 30, "max": 10},
        "cv": {"weight": 15, "max": 10},
        "carta_aceptacion": {"weight": 10, "max": 10},
        "solicitud": {"weight": 5, "max": 10},
    }

    def __init__(self, baremo: dict | None = None):
        if baremo is not None:
            self.BAREMO = baremo

    def score_student(self, student_id: str, datos: dict) -> StudentScore:
        """Calculate final score for a single student.

        Args:
            student_id: Student identifier.
            datos: {doc_type: {extracted_fields...}}

        Returns:
            StudentScore with weighted total.
        """
        score = StudentScore(student_id)

        for doc_type, cfg in self.BAREMO.items():
            doc_data = datos.get(doc_type, {})
            raw = self._extract_score(doc_type, doc_data)
            normalized = min(raw, cfg["max"])
            weighted = (normalized / cfg["max"]) * cfg["weight"]
            score.puntuaciones[doc_type] = round(normalized, 2)
            score.puntuacion_total += weighted

        score.puntuacion_total = round(score.puntuacion_total, 2)
        logger.info(f"  {student_id}: {score.puntuacion_total} pts")
        return score

    def _extract_score(self, doc_type: str, data: dict) -> float:
        """Extract a numeric score from document data."""
        try:
            if doc_type == "nota_media":
                val = float(data.get("nota_media", 0))
                escala = data.get("escala", "10")
                if "10" in str(escala):
                    return val
                elif "4" in str(escala):
                    return val * 2.5
                elif "100" in str(escala):
                    return val / 10
                return val

            elif doc_type == "expediente_academico":
                total = int(data.get("total_asignaturas", 0) or 0)
                aprobadas = int(data.get("asignaturas_aprobadas", 0) or 0)
                if total > 0:
                    return (aprobadas / total) * 10
                return 0

            elif doc_type == "cv":
                anos = float(data.get("anos_experiencia", 0) or 0)
                idiomas = len(data.get("idiomas", []) or [])
                habs = len(data.get("habilidades_clave", []) or [])
                return min(10.0, (anos * 0.5) + (idiomas * 0.5) + (habs * 0.3))

            elif doc_type == "carta_aceptacion":
                return 10.0

            elif doc_type == "solicitud":
                return 10.0

        except (ValueError, TypeError) as e:
            logger.warning(f"Error scoring {doc_type} for data {data}: {e}")

        return 0

    def rank_students(self, scores: list[StudentScore]) -> list[StudentScore]:
        """Sort students by total score descending, assign rank order."""
        sorted_scores = sorted(scores, key=lambda s: s.puntuacion_total, reverse=True)
        for i, s in enumerate(sorted_scores, 1):
            s.orden = i
        return sorted_scores
