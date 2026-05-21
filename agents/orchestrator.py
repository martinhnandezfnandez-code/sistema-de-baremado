"""
AgentOrchestrator — Coordina el flujo multi-agente mediante archivos de estado.

Flujo:
  PLANIFICADOR → genera Bloques.md
    → IDENTIFICADOR → clasifica docs, genera estado.md
      → REVISOR_1, REVISOR_2, REVISOR_3 (paralelo)
        → CALIFICADOR → baremo_final.md
          → PLANIFICADOR marca COMPLETADO
"""

import json
import logging
import shutil
import time
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
        self.block_size = config["pipeline"]["block_size"]
        self.current_block = 0
        self.active_students: list[str] = []

        for d in [TEMP_DIR, JSON_DIR, RESULTS_DIR, DESCARTADOS_DIR]:
            d.mkdir(exist_ok=True)

    def run(self):
        logger.info("=== INICIO ORQUESTACIÓN MULTI-AGENTE ===")

        students = self._get_all_students()
        if not students:
            logger.warning("No hay alumnos para procesar")
            return

        blocks = self._split_blocks(students)

        # Planificador: genera Bloques.md
        self._generar_bloques(blocks)

        for block_idx, block in enumerate(blocks):
            self.current_block = block_idx
            logger.info(f"\n--- Bloque {block_idx + 1}/{len(blocks)} ({len(block)} alumnos) ---")

            for student_id in block:
                self._process_student(student_id)

            # Planificador: marca bloque COMPLETADO
            self._marcar_bloque_completado(block_idx)

        logger.info("=== ORQUESTACIÓN COMPLETADA ===")

    def _get_all_students(self) -> list[str]:
        if not INPUT_DIR.exists():
            return []
        return sorted(
            [d.name for d in INPUT_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")],
        )

    def _split_blocks(self, students: list[str]) -> list[list[str]]:
        return [students[i:i + self.block_size] for i in range(0, len(students), self.block_size)]

    def _generar_bloques(self, blocks: list[list[str]]):
        """Planificador: escribe Bloques.md"""
        lines = ["# Bloques de Trabajo\n"]
        for i, block in enumerate(blocks):
            status = "COMPLETADO" if i < self.current_block else "EN_PROGRESO" if i == self.current_block else "PENDIENTE"
            lines.append(f"## Bloque {i + 1} (alumnos {block[0]}–{block[-1]})")
            lines.append(f"<promise>{status}</promise>\n")
            for sid in block:
                lines.append(f"- [ ] {sid} — PENDIENTE")
            lines.append("")
        (TEMP_DIR / "Bloques.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Bloques.md generado con {len(blocks)} bloques")

    def _marcar_bloque_completado(self, block_idx: int):
        """Planificador: marca el bloque como COMPLETADO en Bloques.md"""
        path = TEMP_DIR / "Bloques.md"
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        tag = f"<promise>EN_PROGRESO</promise>"
        new_tag = f"<promise>COMPLETADO</promise>"
        content = content.replace(f"## Bloque {block_idx + 1}", f"## Bloque {block_idx + 1}", 1)
        content = content.replace(tag, new_tag, 1) if tag in content else content
        path.write_text(content, encoding="utf-8")

    def _process_student(self, student_id: str):
        """Procesa un alumno completo: IDENTIFICADOR → REVISORES → CALIFICADOR."""
        logger.info(f"\n{'='*50}")
        logger.info(f"Procesando: {student_id}")

        # 1 — IDENTIFICADOR
        estado = self._identificador_run(student_id)
        if not estado:
            return

        # 2 — REVISORES (paralelo simulado)
        self._revisores_run(student_id, estado)

        # 3 — CALIFICADOR
        self._calificador_run(student_id)

        # 4 — Planificador: marca alumno COMPLETADO
        self._marcar_alumno_completado(student_id)

    def _identificador_run(self, student_id: str) -> dict | None:
        """Identificador: clasifica documentos y genera estado.md"""
        from pdf_utils import extract_texts_from_student
        from classifier import Classifier
        from extractor import Extractor

        logger.info(f"[IDENTIFICADOR] Clasificando documentos de {student_id}")

        pdf_texts = extract_texts_from_student(student_id)
        if not pdf_texts:
            logger.warning(f"  Sin PDFs, moviendo a descartados")
            self._mover_a_descartados(student_id, "Sin PDFs legibles")
            return None

        classifier = Classifier(self.llm)
        classified = classifier.classify(pdf_texts)

        extractor = Extractor(self.llm)
        extracted = extractor.extract_all(classified)

        # Guardar JSON
        (JSON_DIR / f"{student_id}.json").write_text(
            json.dumps(extracted, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Generar estado.md
        estado = self._generar_estado_md(student_id, classified, extracted)
        return estado

    def _generar_estado_md(self, student_id: str, classified: dict, extracted: dict) -> dict:
        """Escribe estado.md para el alumno."""
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
        lines.append("")

        lines.append("<!-- SECCIÓN REVISOR 1 (Carta Aceptación + CV) - NO EDITAR OTROS REVISORES -->")
        lines.append("<revisor_1></revisor_1>")
        lines.append("")
        lines.append("<!-- SECCIÓN REVISOR 2 (Expediente + Nota Media) - NO EDITAR OTROS REVISORES -->")
        lines.append("<revisor_2></revisor_2>")
        lines.append("")
        lines.append("<!-- SECCIÓN REVISOR 3 (Solicitud) - NO EDITAR OTROS REVISORES -->")
        lines.append("<revisor_3></revisor_3>")
        lines.append("")
        lines.append("<sincronizacion>")
        lines.append("  <revisor_1>PENDIENTE</revisor_1>")
        lines.append("  <revisor_2>PENDIENTE</revisor_2>")
        lines.append("  <revisor_3>PENDIENTE</revisor_3>")
        lines.append("</sincronizacion>")

        (TEMP_DIR / f"{student_id}_estado.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  estado.md generado — {estado_alumno}")

        if estado_alumno == "Descartado":
            self._mover_a_descartados(student_id, descripcion)
            return None

        return {
            "student_id": student_id,
            "doc_types": doc_types,
            "classified": classified,
            "extracted": extracted,
        }

    def _revisores_run(self, student_id: str, estado: dict):
        """Ejecuta los 3 revisores (paralelo simulado con skills)."""
        estado_path = TEMP_DIR / f"{student_id}_estado.md"
        if not estado_path.exists():
            return

        extracted = estado.get("extracted", {})
        classified = estado.get("classified", {})

        # Revisor 1: Carta Aceptación + CV
        rev1 = self._revisor_ejecutar(
            student_id, "revisor_carta_cv",
            extracted.get("carta_aceptacion", {}),
            extracted.get("cv", {}),
        )
        self._escribir_seccion_revisor(estado_path, "revisor_1", json.dumps(rev1, ensure_ascii=False))

        # Revisor 2: Expediente + Nota Media
        rev2 = self._revisor_ejecutar(
            student_id, "revisor_expediente",
            extracted.get("expediente_academico", {}),
            extracted.get("nota_media", {}),
        )
        self._escribir_seccion_revisor(estado_path, "revisor_2", json.dumps(rev2, ensure_ascii=False))

        # Revisor 3: Solicitud
        rev3 = self._revisor_ejecutar(
            student_id, "revisor_solicitud",
            extracted.get("solicitud", {}),
        )
        self._escribir_seccion_revisor(estado_path, "revisor_3", json.dumps(rev3, ensure_ascii=False))

        # Marcar sincronización
        self._actualizar_sincronizacion(estado_path, {
            "revisor_1": "COMPLETADO",
            "revisor_2": "COMPLETADO",
            "revisor_3": "COMPLETADO",
        })
        logger.info(f"  [REVISORES] Los 3 revisores completados para {student_id}")

    def _revisor_ejecutar(self, student_id: str, revisor_type: str, *doc_entries) -> dict:
        """Ejecuta un revisor vía LLM con su skill correspondiente."""
        skill_path = SKILLS_DIR / f"{revisor_type}.md"
        skill_content = ""
        if skill_path.exists():
            skill_content = skill_path.read_text(encoding="utf-8")

        system_prompt = (
            f"Eres un agente revisor especializado ({revisor_type}).\n\n"
            f"{skill_content}\n\n"
            "Debes evaluar los documentos proporcionados y devolver una puntuación (0-10) "
            "y observaciones detalladas en formato JSON."
        )

        docs_text = json.dumps([e for e in doc_entries if e], indent=2, ensure_ascii=False)
        user_prompt = f"Alumno: {student_id}\n\nDocumentos a revisar:\n{docs_text}"

        try:
            raw = self.llm._call(system_prompt, user_prompt)
            return self.llm._parse_json(raw)
        except Exception as e:
            logger.error(f"  Error en revisor {revisor_type}: {e}")
            return {"error": str(e), "puntuacion": 0}

    def _escribir_seccion_revisor(self, estado_path: Path, seccion: str, contenido: str):
        if not estado_path.exists():
            return
        content = estado_path.read_text(encoding="utf-8")
        marker = f"<{seccion}>"
        end_marker = f"</{seccion}>"
        if marker in content:
            start = content.find(marker) + len(marker)
            end = content.find(end_marker)
            if end > start:
                content = content[:start] + contenido + content[end:]
                estado_path.write_text(content, encoding="utf-8")

    def _actualizar_sincronizacion(self, estado_path: Path, estados: dict):
        if not estado_path.exists():
            return
        content = estado_path.read_text(encoding="utf-8")
        for revisor, status in estados.items():
            old = f"<{revisor}>PENDIENTE</{revisor}>"
            new = f"<{revisor}>{status}</{revisor}>"
            content = content.replace(old, new)
        estado_path.write_text(content, encoding="utf-8")

    def _calificador_run(self, student_id: str):
        """Calificador: lee los revisores y genera baremo_final.md y Excel."""
        from scorer import Scorer
        from validator import Validator
        from export import ExcelExporter

        logger.info(f"[CALIFICADOR] Puntuando a {student_id}")

        estado_path = TEMP_DIR / f"{student_id}_estado.md"
        json_path = JSON_DIR / f"{student_id}.json"

        if not json_path.exists():
            logger.warning(f"  No hay JSON para {student_id}")
            return

        extracted = json.loads(json_path.read_text(encoding="utf-8"))

        validator = Validator()
        validation = validator.validate(student_id, extracted)

        if validation.estado == "Descartado":
            logger.info(f"  {student_id} descartado por validación: {validation.descripcion}")
            return

        scorer = Scorer(baremo=self.config.get("baremo"), baremo_docs=self.config.get("baremo_docs"))
        score = scorer.score_student(student_id, validation.datos)

        # Guardar baremo_final.md
        baremo_lines = [
            f"# Baremo Final: {student_id}",
            f"",
            f"**Puntuación Total:** {score.puntuacion_total}",
            f"**Orden:** {score.orden}",
            f"",
            "## Puntuaciones por Documento",
        ]
        for dtype, pts in score.puntuaciones.items():
            baremo_lines.append(f"- {dtype}: {pts}/10")
        baremo_lines.append("")
        baremo_lines.append(f"<promise>COMPLETADO</promise>")

        (TEMP_DIR / f"{student_id}_baremo.md").write_text(
            "\n".join(baremo_lines), encoding="utf-8"
        )
        logger.info(f"  Puntuación: {score.puntuacion_total}")

    def _marcar_alumno_completado(self, student_id: str):
        """Planificador: marca alumno como COMPLETADO en Bloques.md."""
        path = TEMP_DIR / "Bloques.md"
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
