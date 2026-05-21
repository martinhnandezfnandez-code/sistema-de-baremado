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
        self.detalle_docs: dict[str, dict] = {}

    def to_dict(self) -> dict:
        d = {
            "student_id": self.student_id,
            "puntuaciones": self.puntuaciones,
            "puntuacion_total": round(self.puntuacion_total, 2),
            "orden": self.orden,
        }
        if self.detalle_docs:
            d["detalle_docs"] = self.detalle_docs
        return d


class Scorer:
    """Aplica las reglas del baremo de forma determinista en Python.

    Cada tipo de documento puede tener un método de puntuación definido
    en config.json → baremo_docs:
      - "numerical":  usa un valor numérico directo (con escala y rangos)
      - "ratio":      calcula proporción entre dos campos
      - "keyword":    busca palabras clave en campos extraídos por la IA
    """

    BAREMO = {
        "nota_media": {"weight": 40, "max": 10},
        "expediente_academico": {"weight": 30, "max": 10},
        "cv": {"weight": 15, "max": 10},
        "carta_aceptacion": {"weight": 10, "max": 10},
        "solicitud": {"weight": 5, "max": 10},
    }

    BAREMO_DOCS: dict = {}

    def __init__(self, baremo: dict | None = None, baremo_docs: dict | None = None):
        if baremo is not None:
            self.BAREMO = baremo
        if baremo_docs is not None:
            self.BAREMO_DOCS = baremo_docs

    def score_student(self, student_id: str, datos: dict) -> StudentScore:
        score = StudentScore(student_id)
        score.detalle_docs = {}

        for doc_type, cfg in self.BAREMO.items():
            doc_data = datos.get(doc_type, {})
            raw, detalle = self._extract_score(doc_type, doc_data)
            normalized = min(raw, cfg["max"])
            weighted = (normalized / cfg["max"]) * cfg["weight"]
            score.puntuaciones[doc_type] = round(normalized, 2)
            score.puntuacion_total += weighted
            if detalle:
                score.detalle_docs[doc_type] = detalle

        score.puntuacion_total = round(score.puntuacion_total, 2)
        logger.info(f"  {student_id}: {score.puntuacion_total} pts")
        return score

    def _extract_score(self, doc_type: str, data: dict) -> tuple[float, dict]:
        """Extract a numeric score from document data.

        Returns:
            (score, detail_dict) where detail_dict has sub-score breakdown.
        """
        rules = self.BAREMO_DOCS.get(doc_type, {})
        method = rules.get("method", "")

        try:
            if method == "numerical":
                return self._score_numerical(data, rules)
            elif method == "ratio":
                return self._score_ratio(data, rules)
            elif method == "keyword":
                return self._score_keywords(data, rules)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error scoring {doc_type}: {e}")

        return (0.0, {})

    def _score_numerical(self, data: dict, rules: dict) -> tuple[float, dict]:
        """Score based on a numerical field with scale conversion and ranges."""
        field = rules.get("field", "")
        val = float(data.get(field, 0) or 0)
        escala = str(data.get(rules.get("scale_field", ""), "10"))

        scales = rules.get("scales", {})
        for scale_str, factor in scales.items():
            if scale_str in escala:
                val = val * factor
                break

        ranges = rules.get("ranges", [])
        for r in sorted(ranges, key=lambda x: x.get("min", 0), reverse=True):
            if val >= r.get("min", 0):
                score = r.get("score", 0)
                return (score, {"nota": {"valor": val, "puntos": score}})

        return (val, {"nota": {"valor": val, "puntos": val}})

    def _score_ratio(self, data: dict, rules: dict) -> tuple[float, dict]:
        """Score based on ratio between two fields (e.g. pass rate)."""
        num = float(data.get(rules.get("numerator", ""), 0) or 0)
        den = float(data.get(rules.get("denominator", ""), 1) or 1)
        pct = (num / den * 100) if den > 0 else 0

        ranges = rules.get("ranges", [])
        for r in sorted(ranges, key=lambda x: x.get("min_pct", 0), reverse=True):
            if pct >= r.get("min_pct", 0):
                score = r.get("score", 0)
                return (score, {"aprobados": {"valor": f"{pct:.0f}%", "puntos": score}})

        return (0.0, {"aprobados": {"valor": f"{pct:.0f}%", "puntos": 0}})

    def _score_keywords(self, data: dict, rules: dict) -> tuple[float, dict]:
        """Score by matching keyword fields and numeric ranges from config.

        Cada campo en rules['fields'] puede ser:
          - "keywords": dict de palabra → puntuación
          - "ranges": lista de rangos con "min" (o "min_meses") y "score"
          - "default": valor por defecto si no hay match
        """
        total = 0.0
        detalle = {}

        for field_name, cfg in rules.get("fields", {}).items():
            if "keywords" in cfg:
                raw_val = (data.get(field_name) or "").strip().lower()
                kw = cfg.get("keywords", {})
                puntos = cfg.get("default", 0)
                for keyword, valor in kw.items():
                    if keyword in raw_val:
                        puntos = valor
                        break
                total += puntos
                detalle[field_name] = {"valor": raw_val, "puntos": puntos}

            elif "ranges" in cfg:
                raw_val = float(data.get(field_name, 0) or 0)
                rangos = cfg.get("ranges", [])
                puntos = 0
                for r in sorted(rangos, key=lambda x: x.get("min", 0), reverse=True):
                    min_key = next((k for k in ("min", "min_meses") if k in r), "min")
                    if raw_val >= r.get(min_key, 0):
                        puntos = r.get("score", 0)
                        break
                total += puntos
                detalle[field_name] = {"valor": raw_val, "puntos": puntos}

        return (total, detalle)

    def rank_students(self, scores: list[StudentScore]) -> list[StudentScore]:
        sorted_scores = sorted(scores, key=lambda s: s.puntuacion_total, reverse=True)
        for i, s in enumerate(sorted_scores, 1):
            s.orden = i
        return sorted_scores
