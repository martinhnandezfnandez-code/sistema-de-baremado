import json
import logging
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


class ExcelExporter:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_results(
        self,
        scored_students: list,
        rejected_students: list,
        filename: str = "baremo_resultados.xlsx",
    ) -> str:
        """Generate Excel workbook with results.

        Args:
            scored_students: List of StudentScore.to_dict()
            rejected_students: List of ValidationResult.to_dict()
            filename: Output filename.

        Returns:
            Path to generated Excel file.
        """
        wb = Workbook()

        self._write_activos(wb, scored_students)
        self._write_descartados(wb, rejected_students)
        self._write_resumen(wb, scored_students, rejected_students)

        output_path = self.output_dir / filename
        wb.save(str(output_path))
        logger.info(f"Excel generado: {output_path}")
        return str(output_path)

    def _write_activos(self, wb: Workbook, students: list):
        ws = wb.active
        ws.title = "Admitidos"

        headers = [
            "Orden", "ID Alumno", "Puntuación Total",
            "Nota Media", "Expediente", "CV",
            "Carta Aceptación", "Solicitud",
        ]
        self._style_header(ws, headers)

        for i, s in enumerate(students, 1):
            row = i + 1
            p = s.get("puntuaciones", {})
            ws.cell(row=row, column=1, value=s.get("orden", i))
            ws.cell(row=row, column=2, value=s.get("student_id", ""))
            ws.cell(row=row, column=3, value=s.get("puntuacion_total", 0))
            ws.cell(row=row, column=4, value=p.get("nota_media", ""))
            ws.cell(row=row, column=5, value=p.get("expediente_academico", ""))
            ws.cell(row=row, column=6, value=p.get("cv", ""))
            ws.cell(row=row, column=7, value=p.get("carta_aceptacion", ""))
            ws.cell(row=row, column=8, value=p.get("solicitud", ""))

        self._auto_width(ws, headers)

    def _write_descartados(self, wb: Workbook, students: list):
        ws = wb.create_sheet("Descartados")

        headers = [
            "ID Alumno", "Estado", "Motivo",
            "Docs Faltantes", "Docs Baja Confianza",
        ]
        self._style_header(ws, headers)

        for i, s in enumerate(students, 1):
            row = i + 1
            ws.cell(row=row, column=1, value=s.get("student_id", ""))
            ws.cell(row=row, column=2, value=s.get("estado", ""))
            ws.cell(row=row, column=3, value=s.get("descripcion", ""))
            ws.cell(row=row, column=4, value=", ".join(s.get("missing_docs", [])))
            ws.cell(row=row, column=5, value=", ".join(s.get("low_confidence_docs", [])))

        self._auto_width(ws, headers)

    def _write_resumen(self, wb: Workbook, activos: list, descartados: list):
        ws = wb.create_sheet("Resumen")

        ws.cell(row=1, column=1, value="Métrica").font = Font(bold=True)
        ws.cell(row=1, column=2, value="Valor").font = Font(bold=True)

        ws.cell(row=2, column=1, value="Total Alumnos")
        ws.cell(row=2, column=2, value=len(activos) + len(descartados))

        ws.cell(row=3, column=1, value="Admitidos")
        ws.cell(row=3, column=2, value=len(activos))

        ws.cell(row=4, column=1, value="Descartados")
        ws.cell(row=4, column=2, value=len(descartados))

        if activos:
            ws.cell(row=6, column=1, value="Media Puntuación (Admitidos)")
            media = sum(s.get("puntuacion_total", 0) for s in activos) / len(activos)
            ws.cell(row=6, column=2, value=round(media, 2))

            ws.cell(row=7, column=1, value="Puntuación Máxima")
            ws.cell(row=7, column=2, value=max(s.get("puntuacion_total", 0) for s in activos))

        self._auto_width(ws, ["Métrica", "Valor"])

    def _style_header(self, ws, headers: list[str]):
        fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        font = Font(bold=True, color="FFFFFF", size=11)
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = font
            cell.fill = fill
            cell.alignment = Alignment(horizontal="center")

    def _auto_width(self, ws, headers: list[str]):
        for col, h in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(col)].width = max(len(h) + 3, 18)
