import json
import logging
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)["lmstudio"]
        self.client = OpenAI(
            base_url=cfg["base_url"],
            api_key="not-needed",
        )
        self.model = cfg["model"]
        self.temperature = cfg["temperature"]
        self.max_tokens = cfg["max_tokens"]

    def _call(self, system: str, user: str, response_format=None) -> str:
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def classify_document(self, text: str) -> dict:
        system = (
            "Eres un clasificador de documentos académicos. "
            "Clasifica el siguiente texto en una de estas categorías:\n"
            "- solicitud (formulario de solicitud de admisión)\n"
            "- carta_aceptacion (carta de aceptación del programa)\n"
            "- expediente_academico (historial académico, notas, materias cursadas)\n"
            "- nota_media (documento que indica la nota media/ GPA)\n"
            "- cv (curriculum vitae)\n"
            "- desconocido\n\n"
            "Responde SOLO con un JSON: {\"categoria\": \"...\", \"confianza\": \"ALTA|MEDIA|BAJA\", \"justificacion\": \"...\"}"
        )
        raw = self._call(system, f"Texto del documento:\n\n{text[:3000]}")
        return self._parse_json(raw)

    def extract_data(self, categoria: str, text: str) -> dict:
        schemas = {
            "solicitud": (
                "Extrae del siguiente documento de solicitud: nombre completo, dni/pasaporte, "
                "email, telefono, programa_solicitado. "
                "Responde JSON: {\"nombre\": \"\", \"dni\": \"\", \"email\": \"\", \"telefono\": \"\", \"programa\": \"\"}"
            ),
            "carta_aceptacion": (
                "Extrae del siguiente documento de carta de aceptación: institucion, programa, "
                "fecha_inicio, fecha_fin, nombre_estudiante, nombre_firmante, cargo_firmante. "
                "Responde JSON: {\"institucion\": \"\", \"programa\": \"\", \"fecha_inicio\": \"\", \"fecha_fin\": \"\", \"nombre_estudiante\": \"\", \"nombre_firmante\": \"\", \"cargo_firmante\": \"\"}"
            ),
            "expediente_academico": (
                "Extrae del siguiente expediente académico: nombre_estudiante, institucion, "
                "carrera, año_inicio, año_fin, total_asignaturas, asignaturas_cursadas, asignaturas_aprobadas. "
                "Responde JSON: {\"nombre_estudiante\": \"\", \"institucion\": \"\", \"carrera\": \"\", \"año_inicio\": \"\", \"año_fin\": \"\", \"total_asignaturas\": 0, \"asignaturas_cursadas\": 0, \"asignaturas_aprobadas\": 0}"
            ),
            "nota_media": (
                "Extrae la nota media / GPA del siguiente documento. "
                "Responde JSON: {\"nota_media\": 0.0, \"escala\": \"\", \"nombre_estudiante\": \"\", \"institucion\": \"\"}"
            ),
            "cv": (
                "Extrae del siguiente CV: nombre_completo, email, telefono, "
                "titulacion, anos_experiencia, habilidades_clave (array), idiomas (array). "
                "Responde JSON: {\"nombre_completo\": \"\", \"email\": \"\", \"telefono\": \"\", \"titulacion\": \"\", \"anos_experiencia\": 0, \"habilidades_clave\": [], \"idiomas\": []}"
            ),
        }
        instruccion = schemas.get(categoria, "Extrae toda la información relevante en formato JSON.")
        raw = self._call(f"Eres un extractor de datos. {instruccion}", f"Documento:\n\n{text[:4000]}")
        return self._parse_json(raw)

    def review_document(self, categoria: str, text: str, criterios: str) -> dict:
        system = (
            f"Eres un revisor especializado en documentos tipo '{categoria}'. "
            f"Criterios de revisión: {criterios}\n\n"
            "Responde SOLO con JSON: {\"puntuacion\": 0-10, \"observaciones\": \"...\", \"confianza\": \"ALTA|MEDIA|BAJA\", \"detalles\": {...}}"
        )
        raw = self._call(system, f"Documento a revisar:\n\n{text[:4000]}")
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM response: {raw[:200]}")
            return {"error": "parse_failed", "raw": raw[:500]}
