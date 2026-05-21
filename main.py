#!/usr/bin/env python3
"""
sistema-de-baremado — Orquestador principal.

Modos de ejecución:
  python main.py --agent       # Pipeline completo con agentes IA
  python main.py --pipeline    # Solo pipeline Python (usa JSON existente o clasifica directo)

Flujo:
  1. Leer input/ → lista de alumnos
  2. Clasificar documentos (IA o directo)
  3. Extraer datos estructurados (IA)
  4. Validar requisitos (Python)
  5. Calcular puntuaciones (Python)
  6. Generar Excel (Python)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_student_folders(input_dir: str = "input") -> list[str]:
    base = Path(input_dir)
    if not base.exists():
        logger.warning(f"Directorio {input_dir} no existe")
        return []
    folders = sorted(
        [d.name for d in base.iterdir() if d.is_dir() and not d.name.startswith("_")],
        key=lambda x: int("".join(filter(str.isdigit, x)) or 0),
    )
    logger.info(f"Alumnos encontrados: {len(folders)}")
    return folders


def run_pipeline_mode(config: dict):
    """Pipeline directo: clasifica, extrae, valida, puntúa, exporta."""
    from llm_client import LLMClient
    from classifier import Classifier
    from extractor import Extractor
    from validator import Validator
    from scorer import Scorer
    from export import ExcelExporter

    from pdf_utils import extract_texts_from_student

    llm = LLMClient()
    classifier = Classifier(llm)
    extractor = Extractor(llm)
    validator = Validator(min_confidence=config["pipeline"]["min_confidence"])
    scorer = Scorer(baremo=config.get("baremo"))
    exporter = ExcelExporter()

    students = get_student_folders()
    active_scores = []
    rejected = []

    for sid in students:
        logger.info(f"\n{'='*50}")
        logger.info(f"Procesando: {sid}")

        # 1 — Leer PDFs del alumno
        pdf_texts = extract_texts_from_student(sid)
        if not pdf_texts:
            logger.warning(f"  {sid}: Sin PDFs legibles")
            rejected.append({
                "student_id": sid, "estado": "Descartado",
                "descripcion": "Sin PDFs legibles", "missing_docs": [], "low_confidence_docs": [],
            })
            continue

        # 2 — Clasificar
        logger.info(f"  Clasificando {len(pdf_texts)} documento(s)...")
        classified = classifier.classify(pdf_texts)

        # 3 — Extraer datos
        logger.info("  Extrayendo datos estructurados...")
        extracted = extractor.extract_all(classified)

        # Guardar JSON individual
        json_dir = Path(config.get("json_dir", "json"))
        json_dir.mkdir(exist_ok=True)
        with open(json_dir / f"{sid}.json", "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2, ensure_ascii=False)

        # 4 — Validar
        logger.info("  Validando requisitos...")
        validation = validator.validate(sid, extracted)
        logger.info(f"  Estado: {validation.estado} — {validation.descripcion}")

        if validation.estado == "Descartado":
            rejected.append(validation.to_dict())
            continue

        # 5 — Puntuar
        logger.info("  Calculando puntuación...")
        score = scorer.score_student(sid, validation.datos)
        active_scores.append(score.to_dict())

    # 6 — Ranking & Export
    if active_scores:
        ranked = scorer.rank_students(
            [type("_", (), {"puntuacion_total": s["puntuacion_total"], "to_dict": lambda self: self._d}) for s in active_scores]
        )
        # Rebuild ranked dicts
        ranked_dicts = sorted(active_scores, key=lambda s: s["puntuacion_total"], reverse=True)
        for i, s in enumerate(ranked_dicts, 1):
            s["orden"] = i

        path = exporter.export_results(ranked_dicts, rejected)
        logger.info(f"\nExcel generado: {path}")
    else:
        logger.warning("No hay alumnos activos para puntuar")

    logger.info(f"\nResumen: {len(active_scores)} admitidos, {len(rejected)} descartados")


def run_agent_mode(config: dict):
    """Orquestación multi-agente con comunicación basada en archivos."""
    from agents.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(config)
    orchestrator.run()


def main():
    parser = argparse.ArgumentParser(description="Sistema de Baremado")
    parser.add_argument("--mode", choices=["pipeline", "agent"], default="pipeline",
                        help="Modo de ejecución (default: pipeline)")
    parser.add_argument("--config", default="config.json", help="Ruta al config (default: config.json)")
    args = parser.parse_args()

    config = load_config(args.config)

    logger.info(f"Sistema de Baremado — Modo: {args.mode}")

    if args.mode == "agent":
        run_agent_mode(config)
    else:
        run_pipeline_mode(config)


if __name__ == "__main__":
    main()
