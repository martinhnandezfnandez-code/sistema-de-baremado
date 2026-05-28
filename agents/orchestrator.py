"""
AgentOrchestrator — Coordina el flujo multi-agente mediante archivos de estado.

Flujo:
  PLANIFICADOR → genera tracking.md
    → Por cada alumno (uno a uno):
      → IDENTIFICADOR → clasifica docs, extrae datos, genera estado.md
        → CALIFICADOR → evalúa requisitos, genera resultado_final.md
          → PLANIFICADOR marca COMPLETADO en tracking.md
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

from llm_client import LLMClient

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("skills")
TEMP_DIR = Path("temp")
INPUT_DIR = Path("input")
JSON_DIR = Path("json")
RESULTS_DIR = Path("results")
DESCARTADOS_DIR = Path("descartados")


class AgentOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient()
        self.active_students: list[str] = []

        for d in [TEMP_DIR, JSON_DIR, RESULTS_DIR, DESCARTADOS_DIR]:
            d.mkdir(exist_ok=True)

    def run(self):
        logger.info("=== INICIO ORQUESTACIÓN MULTI-AGENTE ===")

        students = self._get_all_students()
        if not students:
            logger.warning("No hay alumnos para procesar")
            return

        # Planificador: genera tracking.md con todos los alumnos
        self._generar_tracking(students)

        active_scores = []
        rejected = []

        for student_id in students:
            score, rejection = self._process_student(student_id)
            if score:
                active_scores.append(score)
            elif rejection:
                rejected.append(rejection)

        # Generar Excel
        if active_scores or rejected:
            from scorer import Evaluator
            from export import ExcelExporter

            evaluator = Evaluator()
            ranked_dicts = [s for s in sorted(active_scores, key=lambda x: x["student_id"])]
            aptos = [s for s in ranked_dicts if s.get("apto")]
            no_aptos = [s for s in ranked_dicts if not s.get("apto")]
            ranked_dicts = aptos + no_aptos
            for i, s in enumerate(ranked_dicts, 1):
                s["orden"] = i

            exporter = ExcelExporter()
            path = exporter.export_results(ranked_dicts, rejected)
            logger.info(f"\nExcel generado: {path}")
        else:
            logger.warning("No hay alumnos para evaluar")

        logger.info(f"Resumen: {len(active_scores)} admitidos, {len(rejected)} descartados")
        logger.info("=== ORQUESTACIÓN COMPLETADA ===")

    def _get_all_students(self) -> list[str]:
        if not INPUT_DIR.exists():
            return []
        return sorted(
            [d.name for d in INPUT_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")],
        )

    def _generar_tracking(self, students: list[str]):
        """Planificador: escribe tracking.md con todos los alumnos en lista plana."""
        lines = ["# Tracking de Alumnos\n"]
        lines.append(f"**Total:** {len(students)} alumnos\n")
        for sid in students:
            lines.append(f"- [ ] {sid} — PENDIENTE")
        (TEMP_DIR / "tracking.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"tracking.md generado con {len(students)} alumnos")

    def _process_student(self, student_id: str) -> tuple:
        """Procesa un alumno completo: IDENTIFICADOR → CALIFICADOR.

        Returns:
            (result_dict, rejection_dict) — uno de los dos es None.
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"Procesando: {student_id}")

        # 1 — IDENTIFICADOR
        estado, rejection = self._identificador_run(student_id)
        if not estado:
            return (None, rejection)

        # 2 — CALIFICADOR
        result, rejection = self._calificador_run(student_id)
        if result:
            # 3 — Planificador: marca alumno COMPLETADO
            self._marcar_alumno_completado(student_id)
            return (result, None)
        else:
            return (None, rejection)

    def _identificador_run(self, student_id: str) -> tuple:
        """Identificador: clasifica y extrae datos de documentos en una sola pasada.

        Returns:
            (estado_dict, None) si el alumno sigue activo,
            (None, rejection_dict) si es descartado.
        """
        from pdf_utils import extract_texts_from_student

        logger.info(f"[IDENTIFICADOR] Procesando documentos de {student_id}")

        pdf_texts = extract_texts_from_student(student_id)
        if not pdf_texts:
            logger.warning(f"  Sin PDFs, moviendo a descartados")
            rejection = {
                "student_id": student_id, "estado": "Descartado",
                "descripcion": "Sin PDFs legibles", "missing_docs": [], "low_confidence_docs": [],
            }
            self._mover_a_descartados(student_id, "Sin PDFs legibles")
            return (None, rejection)

        classified = {}
        extracted = {}

        for fname, text in pdf_texts.items():
            logger.info(f"  Procesando {fname}...")
            result = self.llm.process_document(text)
            if not result or result.get("error"):
                logger.warning(f"  Error procesando {fname}")
                classified.setdefault("desconocido", []).append({"file": fname, "error": "parse_failed"})
                continue

            categoria = result.get("categoria", "desconocido")
            confianza = result.get("confianza", "BAJA")
            datos = result.get("datos", {})

            classified.setdefault(categoria, []).append({
                "file": fname,
                "confianza": confianza,
                "text": text,
            })
            extracted[categoria] = {
                "file": fname,
                "confianza": confianza,
                "datos": datos,
            }
            logger.info(f"    → {categoria} ({confianza})")

        # Guardar JSON
        (JSON_DIR / f"{student_id}.json").write_text(
            json.dumps(extracted, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Generar estado.md
        estado = self._generar_estado_md(student_id, classified, extracted)
        return estado

    def _generar_estado_md(self, student_id: str, classified: dict, extracted: dict) -> tuple:
        """Escribe estado.md para el alumno.

        Returns:
            (estado_dict, None) si activo,
            (None, rejection_dict) si descartado.
        """
        doc_types = {
            "carta_aceptacion": "NO_ENCONTRADO",
            "expediente_academico": "NO_ENCONTRADO",
            "nota_media": "NO_ENCONTRADO",
            "cv": "NO_ENCONTRADO",
            "solicitud": "NO_ENCONTRADO",
        }

        for categoria, items in classified.items():
            if categoria == "desconocido":
                continue
            files = [it["file"] for it in items]
            doc_types[categoria] = ", ".join(files)

        # Determinar estado del alumno
        required = {"carta_aceptacion", "expediente_academico", "nota_media", "cv", "solicitud"}
        found = {k for k, v in doc_types.items() if v != "NO_ENCONTRADO"}
        missing = required - found

        if missing:
            estado_alumno = "Descartado"
            descripcion = f"Documentos faltantes: {', '.join(sorted(missing))}"
            confianza = "BAJA"
        else:
            estado_alumno = "Activo"
            descripcion = "Todos los documentos requeridos encontrados"
            confianza = "ALTA"

        lines = [
            f"# Estado: {student_id}",
            f"",
            f"<nombrado>{'Si' if doc_types else 'No'}</nombrado>",
            f"<estado>{estado_alumno}</estado>",
            f"<descripcion>{descripcion}</descripcion>",
            f"<confianza>{confianza}</confianza>",
            f"",
            f"## Archivos clasificados",
            f"",
        ]
        lines.append("<archivos>")
        for dtype, files in doc_types.items():
            lines.append(f"  <{dtype}>{files}</{dtype}>")
        lines.append("</archivos>")

        (TEMP_DIR / f"{student_id}_estado.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  estado.md generado — {estado_alumno}")

        if estado_alumno == "Descartado":
            rejection = {
                "student_id": student_id, "estado": "Descartado",
                "descripcion": descripcion, "missing_docs": sorted(missing),
                "low_confidence_docs": [],
            }
            self._mover_a_descartados(student_id, descripcion)
            return (None, rejection)

        return ({
            "student_id": student_id,
            "doc_types": doc_types,
            "classified": classified,
            "extracted": extracted,
        }, None)

    def _calificador_run(self, student_id: str) -> tuple:
        """Calificador: evalúa requisitos y genera resultado final.

        Returns:
            (result_dict, None) si apto,
            (None, rejection_dict) si no apto o descartado.
        """
        from scorer import Evaluator
        from validator import Validator

        logger.info(f"[CALIFICADOR] Evaluando a {student_id}")

        json_path = JSON_DIR / f"{student_id}.json"

        if not json_path.exists():
            logger.warning(f"  No hay JSON para {student_id}")
            return (None, {
                "student_id": student_id, "estado": "Descartado",
                "descripcion": "No hay JSON de datos extraídos",
                "missing_docs": [], "low_confidence_docs": [],
            })

        extracted = json.loads(json_path.read_text(encoding="utf-8"))

        config_req = self.config.get("requisitos", {})
        validator = Validator(config_requisitos=config_req)
        validation = validator.validate(student_id, extracted)

        evaluator = Evaluator()
        result = evaluator.evaluate(validation)

        # Guardar resultado final
        req_lines = [
            f"# Resultado Final: {student_id}",
            f"",
            f"**Estado:** {result.estado}",
            f"**Descripción:** {result.descripcion}",
            f"",
            "## Requisitos",
        ]
        for r in result.requisitos:
            icono = "✓" if r.get("cumple") else "✗"
            req_lines.append(f"- {icono} {r.get('clave')}: {r.get('detalle', '')}")
        req_lines.append("")
        req_lines.append(f"<promise>COMPLETADO</promise>")

        (TEMP_DIR / f"{student_id}_baremo.md").write_text(
            "\n".join(req_lines), encoding="utf-8"
        )
        logger.info(f"  {student_id}: {result.estado}")
        return (result.to_dict(), None)

    def _marcar_alumno_completado(self, student_id: str):
        """Planificador: marca alumno como COMPLETADO en tracking.md."""
        path = TEMP_DIR / "tracking.md"
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        old = f"- [ ] {student_id} — PENDIENTE"
        new = f"- [x] {student_id} — COMPLETADO"
        content = content.replace(old, new, 1)
        path.write_text(content, encoding="utf-8")

    def _mover_a_descartados(self, student_id: str, razon: str):
        """Mueve la carpeta del alumno a descartados/ con registro."""
        src = INPUT_DIR / student_id
        dst = DESCARTADOS_DIR / student_id
        if src.exists():
            shutil.move(str(src), str(dst))
            logger.info(f"  Movido {student_id} → descartados/ ({razon})")

        # Guardar registro
        registro = DESCARTADOS_DIR / "_registro.json"
        data = []
        if registro.exists():
            data = json.loads(registro.read_text(encoding="utf-8"))
        data.append({
            "student_id": student_id,
            "fecha": datetime.now().isoformat(),
            "razon": razon,
        })
        registro.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
