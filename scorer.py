import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StudentResult:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.apto: bool = False
        self.requisitos: list[dict] = []
        self.estado: str = "No apto"
        self.descripcion: str = ""
        self.orden: int = 0

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "apto": self.apto,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "requisitos": self.requisitos,
            "orden": self.orden,
        }


class Evaluator:
    def __init__(self):
        pass

    def evaluate(self, validation_result) -> StudentResult:
        result = StudentResult(validation_result.student_id)
        result.apto = validation_result.apto
        result.estado = validation_result.estado
        result.descripcion = validation_result.descripcion
        result.requisitos = [r.to_dict() for r in validation_result.requisitos]
        logger.info(f"  {validation_result.student_id}: {result.estado}")
        return result

    def rank_students(self, results: list[StudentResult]) -> list[StudentResult]:
        aptos = [r for r in results if r.apto]
        no_aptos = [r for r in results if not r.apto]
        sorted_aptos = sorted(aptos, key=lambda s: s.student_id)
        sorted_no_aptos = sorted(no_aptos, key=lambda s: s.student_id)
        all_sorted = sorted_aptos + sorted_no_aptos
        for i, s in enumerate(all_sorted, 1):
            s.orden = i
        return all_sorted
