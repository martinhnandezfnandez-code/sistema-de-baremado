import json
import logging
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)["ollama"]
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

    def process_document(self, text: str) -> dict:
        """Clasifica y extrae datos de un documento en una sola llamada.

        Returns:
            {"categoria": "...", "confianza": "...", "justificacion": "...", "datos": {...}}
        """
        system = (
            "Eres un clasificador y extractor de documentos académicos.\n\n"
            "Primero clasifica el texto en UNA de estas categorías:\n"
            "- solicitud (formulario de solicitud de admisión)\n"
            "- carta_aceptacion (carta de aceptación del programa)\n"
            "- expediente_academico (historial académico, notas, materias cursadas)\n"
            "- nota_media (documento que indica la nota media/GPA)\n"
            "- cv (curriculum vitae)\n"
            "- desconocido\n\n"
            "Luego extrae los datos específicos según la categoría.\n\n"
            "Campos por categoría:\n"
            "carta_aceptacion: {\"institucion\": \"\", \"programa\": \"\", \"fecha_inicio\": \"\", \"fecha_fin\": \"\", \"nombre_estudiante\": \"\", \"nombre_firmante\": \"\", \"cargo_firmante\": \"\", \"tipo_institucion\": \"universidad/facultad/escuela/instituto/centro/academia/otros\", \"tipo_programa\": \"doctorado/master/grado/licenciatura/diplomatura/curso/otros\", \"duracion_meses\": 0}\n"
            "expediente_academico: {\"nombre_estudiante\": \"\", \"institucion\": \"\", \"carrera\": \"\", \"año_inicio\": \"\", \"año_fin\": \"\", \"total_asignaturas\": 0, \"asignaturas_cursadas\": 0, \"asignaturas_aprobadas\": 0, \"total_creditos\": 0, \"creditos_superados\": 0, \"tipo_titulacion\": \"grado/máster/master/doctorado/licenciatura/diplomatura\", \"matricula_vigor\": \"sí/no\", \"expediente_abierto\": \"sí/no\"}\n"
            "nota_media: {\"nota_media\": 0.0, \"escala\": \"\", \"nombre_estudiante\": \"\", \"institucion\": \"\"}\n"
            "cv: {\"nombre_completo\": \"\", \"email\": \"\", \"telefono\": \"\", \"titulacion\": \"\", \"anos_experiencia\": 0, \"habilidades_clave\": [], \"idiomas\": [], \"nivel_estudios\": \"doctorado/master/grado/licenciatura/fp/bachillerato/secundaria\", \"grupo_profesional\": \"sanidad/educacion/ingenieria/tecnologia/administracion/comercial/otros\"}\n"
            "solicitud: {\"nombre_completo\": \"\", \"dni\": \"\", \"email\": \"\", \"telefono\": \"\", \"programa\": \"\", \"universidad\": \"\", \"tipo_estudiante\": \"normal/movilidad/otras\", \"tipo_titulacion\": \"grado/máster/master/doctorado/licenciatura\", \"completitud\": \"completa/firmada/incompleta/parcial\", \"motivacion\": \"alta/media/baja\", \"interaccion_menores\": \"sí/no\", \"interaccion_discapacidad\": \"sí/no\", \"certificado_delitos\": \"sí/no\", \"practicas_previas_entidad\": \"\", \"duracion_practicas_entidad_meses\": 0, \"duracion_practicas_total_meses\": 0, \"bolsa_ayuda_actual\": \"sí/no\", \"meses_incorporado\": 0}\n\n"
            "Responde SOLO con JSON exactamente así: {\"categoria\": \"...\", \"confianza\": \"ALTA|MEDIA|BAJA\", \"justificacion\": \"...\", \"datos\": {...}}"
        )
        raw = self._call(system, f"Documento:\n\n{text[:4000]}")
        return self._parse_json(raw)

    def extract_data(self, categoria: str, text: str) -> dict:
        schemas = {
            "carta_aceptacion": (
                "Extrae del siguiente documento de carta de aceptación: institucion, programa, "
                "fecha_inicio, fecha_fin, nombre_estudiante, nombre_firmante, cargo_firmante, "
                "tipo_institucion (universidad/facultad/escuela/instituto/centro/academia/otros), "
                "tipo_programa (doctorado/master/grado/licenciatura/diplomatura/curso/otros), "
                "duracion_meses (duración estimada en meses, número). "
                "Responde JSON: {\"institucion\": \"\", \"programa\": \"\", \"fecha_inicio\": \"\", \"fecha_fin\": \"\", \"nombre_estudiante\": \"\", \"nombre_firmante\": \"\", \"cargo_firmante\": \"\", \"tipo_institucion\": \"\", \"tipo_programa\": \"\", \"duracion_meses\": 0}"
            ),
            "expediente_academico": (
                "Extrae del siguiente expediente académico: nombre_estudiante, institucion, "
                "carrera, año_inicio, año_fin, total_asignaturas, asignaturas_cursadas, asignaturas_aprobadas, "
                "total_creditos (número total de créditos del plan de estudios), "
                "creditos_superados (número de créditos aprobados), "
                "tipo_titulacion (grado/máster/master/doctorado/licenciatura/diplomatura), "
                "matricula_vigor (sí/no, si la matrícula está en vigor), "
                "expediente_abierto (sí/no, si el expediente está abierto). "
                "Responde JSON: {\"nombre_estudiante\": \"\", \"institucion\": \"\", \"carrera\": \"\", \"año_inicio\": \"\", \"año_fin\": \"\", \"total_asignaturas\": 0, \"asignaturas_cursadas\": 0, \"asignaturas_aprobadas\": 0, \"total_creditos\": 0, \"creditos_superados\": 0, \"tipo_titulacion\": \"\", \"matricula_vigor\": \"\", \"expediente_abierto\": \"\"}"
            ),
            "nota_media": (
                "Extrae la nota media / GPA del siguiente documento. "
                "Responde JSON: {\"nota_media\": 0.0, \"escala\": \"\", \"nombre_estudiante\": \"\", \"institucion\": \"\"}"
            ),
            "cv": (
                "Extrae del siguiente CV: nombre_completo, email, telefono, "
                "titulacion, anos_experiencia, habilidades_clave (array), idiomas (array), "
                "nivel_estudios (el más alto: doctorado/master/grado/licenciatura/fp/bachillerato/secundaria), "
                "grupo_profesional (sector: sanidad/educacion/ingenieria/tecnologia/administracion/comercial/otros). "
                "Responde JSON: {\"nombre_completo\": \"\", \"email\": \"\", \"telefono\": \"\", \"titulacion\": \"\", \"anos_experiencia\": 0, \"habilidades_clave\": [], \"idiomas\": [], \"nivel_estudios\": \"\", \"grupo_profesional\": \"\"}"
            ),
            "solicitud": (
                "Extrae del siguiente documento de solicitud: nombre_completo, dni/pasaporte, "
                "email, telefono, programa_solicitado, universidad (universidad donde está matriculado), "
                "tipo_estudiante (normal/movilidad/otras), "
                "tipo_titulacion (grado/máster/master/doctorado/licenciatura), "
                "completitud (completa/firmada/incompleta/parcial), "
                "motivacion (alta/media/baja), "
                "interaccion_menores (sí/no, si la práctica implica interacción con menores), "
                "interaccion_discapacidad (sí/no, si la práctica implica interacción con personas con discapacidad), "
                "certificado_delitos (sí/no, si dispone del certificado negativo de delitos sexuales), "
                "practicas_previas_entidad (nombre de la entidad donde hizo prácticas previas, o 'ninguna'), "
                "duracion_practicas_entidad_meses (meses de prácticas en esa misma entidad), "
                "duracion_practicas_total_meses (meses totales de prácticas realizadas), "
                "bolsa_ayuda_actual (sí/no, si recibe actualmente una bolsa o ayuda económica), "
                "meses_incorporado (meses que lleva incorporado en la entidad actual). "
                "Responde JSON: {\"nombre_completo\": \"\", \"dni\": \"\", \"email\": \"\", \"telefono\": \"\", \"programa\": \"\", \"universidad\": \"\", \"tipo_estudiante\": \"\", \"tipo_titulacion\": \"\", \"completitud\": \"\", \"motivacion\": \"\", \"interaccion_menores\": \"\", \"interaccion_discapacidad\": \"\", \"certificado_delitos\": \"\", \"practicas_previas_entidad\": \"\", \"duracion_practicas_entidad_meses\": 0, \"duracion_practicas_total_meses\": 0, \"bolsa_ayuda_actual\": \"\", \"meses_incorporado\": 0}"
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
