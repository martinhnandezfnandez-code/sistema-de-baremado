import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

REQUIRED_DOCS = ["carta_aceptacion", "expediente_academico", "nota_media", "cv", "solicitud"]


class ValidationResult:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.is_complete: bool = True
        self.missing_docs: list[str] = []
        self.low_confidence_docs: list[str] = []
        self.estado: str = "Activo"
        self.descripcion: str = ""
        self.datos: dict = {}

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "is_complete": self.is_complete,
            "missing_docs": self.missing_docs,
            "low_confidence_docs": self.low_confidence_docs,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "datos": self.datos,
        }


class Validator:
    def __init__(self, min_confidence: str = "MEDIA"):
        self.min_confidence = min_confidence
        self._order = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        self._min_val = self._order.get(min_confidence, 1)

    def validate(self, student_id: str, extracted: dict) -> ValidationResult:
        """Validate a student's extracted documents against requirements.

        Args:
            student_id: Student folder name.
            extracted: {doc_type: {"file": ..., "confianza": ..., "datos": {...}}}

        Returns:
            ValidationResult with pass/fail and reason.
        """
        result = ValidationResult(student_id)

        found_types = set(extracted.keys())
        required_set = set(REQUIRED_DOCS)

        missing = required_set - found_types
        if missing:
            result.is_complete = False
            result.missing_docs = sorted(missing)
            logger.info(f"  {student_id}: Faltan documentos: {missing}")

        for doc_type in REQUIRED_DOCS:
            entry = extracted.get(doc_type)
            if entry is None:
                continue
            conf = entry.get("confianza", "BAJA")
            if self._order.get(conf, 99) > self._min_val:
                result.low_confidence_docs.append(doc_type)
                logger.info(f"  {student_id}: {doc_type} tiene confianza {conf}")

        if not result.is_complete or result.low_confidence_docs:
            result.estado = "Descartado"
            reasons = []
            if result.missing_docs:
                reasons.append(f"Faltan documentos: {', '.join(result.missing_docs)}")
            if result.low_confidence_docs:
                reasons.append(f"Baja confianza en: {', '.join(result.low_confidence_docs)}")
            result.descripcion = "; ".join(reasons)
        else:
            result.estado = "Activo"
            result.descripcion = "Documentación completa y válida"

        result.datos = {k: v.get("datos", {}) for k, v in extracted.items() if v.get("datos")}
        return result
