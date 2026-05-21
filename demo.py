#!/usr/bin/env python3
"""
Demo del Sistema de Baremado.

Genera documentos PDF de ejemplo, ejecuta el pipeline completo
y genera el Excel con resultados.

Uso:
    python demo.py                  # Pipeline completo (con LMStudio si está disponible)
    python demo.py --mock           # Usa datos simulados (sin LMStudio)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("demo")

# Desactivar logs de librerías
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def create_sample_pdfs(base_dir: str = "input"):
    """Generate sample text-based PDFs for demo students."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        logger.warning("reportlab no instalado. Usando PDFs simulados (txt).")
        _create_sample_txt(base_dir)
        return

    samples = {
        "alumno_001": {
            "carta_aceptacion.pdf": (
                "CARTA DE ACEPTACIÓN\n\n"
                "Universidad Politécnica de Madrid\n"
                "Por la presente, aceptamos al estudiante Juan García López\n"
                "en el programa de Máster en Inteligencia Artificial.\n"
                "Fecha de inicio: Septiembre 2025\n"
                "Fecha de fin: Junio 2026\n\n"
                "Firmado: Dra. María Rodríguez\n"
                "Decana de la Facultad de Informática"
            ),
            "expediente_academico.pdf": (
                "EXPEDIENTE ACADÉMICO\n\n"
                "Estudiante: Juan García López\n"
                "Carrera: Ingeniería Informática\n"
                "Institución: Universidad Politécnica de Madrid\n"
                "Año inicio: 2020  Año fin: 2024\n"
                "Total asignaturas: 40\n"
                "Asignaturas cursadas: 40\n"
                "Asignaturas aprobadas: 38"
            ),
            "nota_media.pdf": (
                "CERTIFICADO DE NOTA MEDIA\n\n"
                "Estudiante: Juan García López\n"
                "DNI: 12345678A\n"
                "Institución: Universidad Politécnica de Madrid\n"
                "Nota media: 8.7\n"
                "Escala: 0-10"
            ),
            "cv.pdf": (
                "CURRICULUM VITAE\n\n"
                "Nombre: Juan García López\n"
                "Email: juan.garcia@email.com\n"
                "Teléfono: +34 612 345 678\n\n"
                "FORMACIÓN:\n"
                "- Grado en Ingeniería Informática, UPM (2020-2024)\n\n"
                "EXPERIENCIA:\n"
                "- Desarrollador Junior en TechCorp (2024-presente) - 1 año\n"
                "- Prácticas en DataSys (2023) - 6 meses\n\n"
                "IDIOMAS:\n"
                "- Español (nativo)\n"
                "- Inglés (C1)\n"
                "- Francés (B1)\n\n"
                "HABILIDADES:\n"
                "Python, Machine Learning, SQL, Git, AWS"
            ),
            "solicitud.pdf": (
                "SOLICITUD DE ADMISIÓN\n\n"
                "Programa: Máster en Inteligencia Artificial\n"
                "Nombre: Juan García López\n"
                "DNI: 12345678A\n"
                "Email: juan.garcia@email.com\n"
                "Teléfono: +34 612 345 678\n\n"
                "Motivación: Deseo ampliar mis conocimientos en IA\n"
                "para aplicarlos en el sector de la salud."
            ),
        },
        "alumno_002": {
            "admission_letter.pdf": (
                "LETTER OF ACCEPTANCE\n\n"
                "Massachusetts Institute of Technology\n"
                "We are pleased to accept María Pérez Sánchez\n"
                "to the Master of Science in Data Science program.\n"
                "Start date: Fall 2025\n"
                "End date: Spring 2027\n\n"
                "Signed: Prof. James Wilson\n"
                "Dean of Graduate Studies"
            ),
            "transcript.pdf": (
                "ACADEMIC TRANSCRIPT\n\n"
                "Student: María Pérez Sánchez\n"
                "Degree: BSc Computer Science\n"
                "Institution: MIT\n"
                "Year start: 2021  Year end: 2025\n"
                "Total courses: 36\n"
                "Courses taken: 36\n"
                "Courses passed: 34"
            ),
            "gpa.pdf": (
                "GRADE POINT AVERAGE\n\n"
                "Student: María Pérez Sánchez\n"
                "GPA: 3.8\n"
                "Scale: 0-4.0"
            ),
            "curriculum_vitae.pdf": (
                "CURRICULUM VITAE\n\n"
                "Name: María Pérez Sánchez\n"
                "Email: maria.perez@email.com\n"
                "Phone: +34 698 765 432\n\n"
                "EDUCATION:\n"
                "- BSc Computer Science, MIT (2021-2025)\n\n"
                "EXPERIENCE:\n"
                "- Data Science Intern at Google (2024) - 3 months\n"
                "- Research Assistant at MIT AI Lab (2023-2024)\n\n"
                "LANGUAGES:\n"
                "- Spanish (native)\n"
                "- English (native)\n"
                "- German (B2)\n\n"
                "SKILLS:\n"
                "Python, R, TensorFlow, PyTorch, SQL, Spark, Docker"
            ),
            "application.pdf": (
                "ADMISSION APPLICATION\n\n"
                "Program: Master of Science in Data Science\n"
                "Name: María Pérez Sánchez\n"
                "Email: maria.perez@email.com\n"
                "Phone: +34 698 765 432\n\n"
                "Statement of Purpose: I aim to leverage data science\n"
                "to solve climate change challenges."
            ),
        },
        "alumno_003": {
            "aceptacion.pdf": (
                "ACEPTACIÓN DE PLAZA\n\n"
                "Universidad de Barcelona\n"
                "Se acepta a Carlos Martínez Ruiz\n"
                "en el Máster en Ciencia de Datos.\n"
                "Curso 2025-2026\n\n"
                "Fdo: Dr. Antonio López\n"
                "Director del Máster"
            ),
            "expediente.pdf": (
                "EXPEDIENTE ACADÉMICO\n\n"
                "Alumno: Carlos Martínez Ruiz\n"
                "Carrera: Matemáticas\n"
                "Universidad: Universidad de Barcelona\n"
                "Asignaturas totales: 36\n"
                "Aprobadas: 28\n"
                "Cursadas: 36"
            ),
            "nota_media.pdf": (
                "NOTA MEDIA\n\n"
                "Carlos Martínez Ruiz\n"
                "Nota media: 6.5\n"
                "Escala: 10"
            ),
            "cv.pdf": (
                "CURRICULUM VITAE\n\n"
                "Carlos Martínez Ruiz\n"
                "Email: carlos.martinez@email.com\n\n"
                "EDUCACIÓN:\n"
                "- Grado en Matemáticas, UB (2019-2023)\n\n"
                "IDIOMAS:\n"
                "- Español (nativo)\n"
                "- Inglés (B1)\n\n"
                "HABILIDADES:\n"
                "Estadística, R, Python básico"
            ),
            "solicitud.pdf": (
                "SOLICITUD\n\n"
                "Máster en Ciencia de Datos\n"
                "Carlos Martínez Ruiz\n"
                "carlos.martinez@email.com"
            ),
        },
        "alumno_004": {
            "carta_aceptacion.pdf": (
                "CARTA DE ACEPTACIÓN\n\n"
                "Universidad de Deusto\n"
                "Aceptamos a Ana López Fernández\n"
                "en el Máster en Ciberseguridad.\n"
                "Inicio: Oct 2025  Fin: Jun 2026\n"
                "Firmado: Dr. Javier Gómez, Decano"
            ),
            "expediente.pdf": (
                "HISTORIAL ACADÉMICO\n\n"
                "Ana López Fernández\n"
                "Ingeniería Informática - Universidad de Deusto\n"
                "Asignaturas: 42 total, 39 aprobadas"
            ),
            "cv.pdf": (
                "CURRICULUM VITAE\n\n"
                "Ana López Fernández\n"
                "Email: ana.lopez@email.com\n"
                "2 años como analista de seguridad\n"
                "Inglés C1, Alemán A2\n"
                "Python, redes, criptografía"
            ),
            "solicitud.pdf": (
                "SOLICITUD DE ADMISIÓN\n\n"
                "Ana López Fernández\n"
                "Máster en Ciberseguridad"
            ),
        },
    }

    for student_id, docs in samples.items():
        student_dir = Path(base_dir) / student_id
        student_dir.mkdir(parents=True, exist_ok=True)
        for fname, text in docs.items():
            pdf_path = student_dir / fname
            c = canvas.Canvas(str(pdf_path), pagesize=A4)
            width, height = A4
            y = height - 50
            for line in text.split("\n"):
                c.drawString(50, y, line[:90])
                y -= 14
                if y < 50:
                    c.showPage()
                    y = height - 50
            c.save()
        logger.info(f"  {student_id}: {len(docs)} PDFs generados")


def _create_sample_txt(base_dir: str):
    """Fallback: create text files when reportlab is not available."""
    samples = {
        "alumno_001": {
            "carta_aceptacion.txt": "CARTA DE ACEPTACION\nUniversidad Politecnica de Madrid\nJuan Garcia Lopez\nMaster en IA",
            "expediente_academico.txt": "EXPEDIENTE ACADEMICO\nJuan Garcia Lopez\n40 asignaturas, 38 aprobadas",
            "nota_media.txt": "NOTA MEDIA\nJuan Garcia Lopez\nNota media: 8.7/10",
            "cv.txt": "CV\nJuan Garcia Lopez\n1 ano experiencia\nIngles C1, Frances B1\nPython, ML, SQL",
            "solicitud.txt": "SOLICITUD\nJuan Garcia Lopez\nMaster en Inteligencia Artificial",
        },
        "alumno_002": {
            "carta_aceptacion.txt": "LETTER OF ACCEPTANCE\nMIT\nMaria Perez Sanchez\nMSc Data Science",
            "expediente_academico.txt": "ACADEMIC TRANSCRIPT\nMaria Perez Sanchez\n36 courses, 34 passed",
            "nota_media.txt": "GPA\nMaria Perez Sanchez\nGPA: 3.8/4.0",
            "cv.txt": "CV\nMaria Perez Sanchez\nGoogle intern, MIT research\nPython, R, TensorFlow\nEnglish native, German B2",
            "solicitud.txt": "APPLICATION\nMaria Perez Sanchez\nMSc Data Science",
        },
        "alumno_003": {
            "carta_aceptacion.txt": "ACEPTACION DE PLAZA\nUniversidad de Barcelona\nCarlos Martinez Ruiz\nMaster en Ciencia de Datos",
            "expediente_academico.txt": "EXPEDIENTE ACADEMICO\nCarlos Martinez Ruiz\n36 asignaturas, 28 aprobadas",
            "nota_media.txt": "NOTA MEDIA\nCarlos Martinez Ruiz\nNota media: 6.5/10",
            "cv.txt": "CV\nCarlos Martinez Ruiz\nMatematicas\nIngles B1\nEstadistica, R",
            "solicitud.txt": "SOLICITUD\nCarlos Martinez Ruiz\nMaster en Ciencia de Datos",
        },
        "alumno_004": {
            "carta_aceptacion.txt": "CARTA DE ACEPTACION\nUniversidad de Deusto\nAna Lopez Fernandez\nMaster en Ciberseguridad",
            "expediente_academico.txt": "HISTORIAL ACADEMICO\nAna Lopez Fernandez\n42 asignaturas, 39 aprobadas",
            "cv.txt": "CV\nAna Lopez Fernandez\n2 anos ciberseguridad\nIngles C1\nPython, redes, criptografia",
            "solicitud.txt": "SOLICITUD\nAna Lopez Fernandez\nMaster en Ciberseguridad",
        },
    }

    for student_id, docs in samples.items():
        student_dir = Path(base_dir) / student_id
        student_dir.mkdir(parents=True, exist_ok=True)
        for fname, text in docs.items():
            (student_dir / fname).write_text(text, encoding="utf-8")
        logger.info(f"  {student_id}: {len(docs)} documentos simulados")


def run_demo(mock: bool = False):
    """Execute the full demo pipeline."""
    logger.info("=" * 60)
    logger.info("SISTEMA DE BAREMADO — DEMO")
    logger.info("=" * 60)

    # Step 1: Clean and generate sample data
    logger.info("\n[1/5] Generando documentos de ejemplo...")
    import shutil
    for d in ["input", "json", "results", "temp", "descartados"]:
        if Path(d).exists():
            shutil.rmtree(d)
    Path("input").mkdir()
    create_sample_pdfs()
    students = [d.name for d in Path("input").iterdir() if d.is_dir()]
    logger.info(f"  {len(students)} alumnos preparados")

    if mock:
        # Use mock data pipeline (no LLM needed)
        logger.info("\n[2/5] Usando datos simulados (modo mock)...")
        _run_mock_pipeline(students)
    else:
        # Try real LLM pipeline
        logger.info("\n[2/5] Iniciando pipeline con IA...")
        from main import run_pipeline_mode
        import json
        config = json.loads(Path("config.json").read_text(encoding="utf-8"))
        try:
            run_pipeline_mode(config)
        except Exception as e:
            logger.error(f"Error con LLM: {e}")
            logger.info("¿Tienes LMStudio corriendo en http://localhost:1234?")
            logger.info("Ejecuta: python demo.py --mock  (para usar datos simulados)")
            return

    logger.info("\n" + "=" * 60)
    logger.info("DEMO COMPLETADA")
    logger.info("=" * 60)


def _run_mock_pipeline(students: list):
    """Mock pipeline that generates results without LLM."""
    from scorer import Scorer, StudentScore
    from validator import Validator, ValidationResult
    from export import ExcelExporter

    # Build mock validation results
    mock_data = {
        "alumno_001": {
            "nota_media": {"nota_media": 8.7, "escala": "10"},
            "expediente_academico": {"total_asignaturas": 40, "asignaturas_aprobadas": 38},
            "cv": {"anos_experiencia": 1, "idiomas": ["Inglés", "Francés"], "habilidades_clave": ["Python", "ML", "SQL"], "nivel_estudios": "grado", "grupo_profesional": "ingenieria"},
            "carta_aceptacion": {"tipo_institucion": "universidad", "tipo_programa": "master", "duracion_meses": 24, "cargo_firmante": "rector"},
            "solicitud": {"completitud": "completa", "motivacion": "alta", "presentacion": "digital"},
        },
        "alumno_002": {
            "nota_media": {"nota_media": 3.8, "escala": "4.0"},
            "expediente_academico": {"total_asignaturas": 36, "asignaturas_aprobadas": 34},
            "cv": {"anos_experiencia": 0.5, "idiomas": ["Español", "Inglés", "Alemán"], "habilidades_clave": ["Python", "R", "TensorFlow", "PyTorch", "SQL", "Spark", "Docker"], "nivel_estudios": "master", "grupo_profesional": "tecnologia"},
            "carta_aceptacion": {"tipo_institucion": "facultad", "tipo_programa": "grado", "duracion_meses": 48, "cargo_firmante": "decano"},
            "solicitud": {"completitud": "firmada", "motivacion": "media", "presentacion": "formulario"},
        },
        "alumno_003": {
            "nota_media": {"nota_media": 6.5, "escala": "10"},
            "expediente_academico": {"total_asignaturas": 36, "asignaturas_aprobadas": 28},
            "cv": {"anos_experiencia": 0, "idiomas": ["Inglés"], "habilidades_clave": ["Estadística", "R"], "nivel_estudios": "doctorado", "grupo_profesional": "sanidad"},
            "carta_aceptacion": {"tipo_institucion": "instituto", "tipo_programa": "curso", "duracion_meses": 6, "cargo_firmante": "coordinador"},
            "solicitud": {"completitud": "parcial", "motivacion": "baja", "presentacion": "físico"},
        },
    }

    import json as _json
    _cfg = _json.loads(Path("config.json").read_text(encoding="utf-8"))
    scorer = Scorer(baremo=_cfg.get("baremo"), baremo_docs=_cfg.get("baremo_docs"))
    validator = Validator()
    active_scores = []
    rejected = []

    for sid in students:
        datos = mock_data.get(sid, {})
        # Check if alumno_004 (incomplete - no nota_media)
        if sid == "alumno_004":
            rejected.append({
                "student_id": sid,
                "estado": "Descartado",
                "descripcion": "Documento faltante: nota_media",
                "missing_docs": ["nota_media"],
                "low_confidence_docs": [],
            })
            logger.info(f"  {sid}: Descartado — falta nota_media")
            continue

        score = scorer.score_student(sid, datos)
        active_scores.append(score.to_dict())

    # Rank and export
    ranked = sorted(active_scores, key=lambda s: s["puntuacion_total"], reverse=True)
    for i, s in enumerate(ranked, 1):
        s["orden"] = i

    exporter = ExcelExporter()
    path = exporter.export_results(ranked, rejected)

    # Show results
    logger.info("\nRanking:")
    logger.info(f"{'#':>4} {'Alumno':<20} {'Puntuación':>10}")
    logger.info("-" * 36)
    for s in ranked:
        logger.info(f"{s['orden']:>4} {s['student_id']:<20} {s['puntuacion_total']:>8.2f}")

    if rejected:
        logger.info(f"\nDescartados ({len(rejected)}):")
        for r in rejected:
            logger.info(f"  - {r['student_id']}: {r['descripcion']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo del Sistema de Baremado")
    parser.add_argument("--mock", action="store_true", help="Usar datos simulados (sin LLM)")
    args = parser.parse_args()
    run_demo(mock=args.mock)
