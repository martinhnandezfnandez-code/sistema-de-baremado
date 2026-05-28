import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RequisitoResult:
    def __init__(self, clave: str, descripcion: str):
        self.clave = clave
        self.descripcion = descripcion
        self.cumple: bool = False
        self.detalle: str = ""

    def to_dict(self) -> dict:
        return {
            "clave": self.clave,
            "descripcion": self.descripcion,
            "cumple": self.cumple,
            "detalle": self.detalle,
        }


class ValidationResult:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.requisitos: list[RequisitoResult] = []
        self.apto: bool = False
        self.estado: str = "Pendiente"
        self.descripcion: str = ""
        self.datos: dict = {}

    def _todos_cumplen(self) -> bool:
        return all(r.cumple for r in self.requisitos)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "apto": self.apto,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "requisitos": [r.to_dict() for r in self.requisitos],
            "datos": self.datos,
        }


class Validator:
    def __init__(self, config_requisitos: dict | None = None):
        self.config = config_requisitos or {}

    def validate(self, student_id: str, extracted: dict) -> ValidationResult:
        result = ValidationResult(student_id)
        datos = self._merge_datos(extracted)
        result.datos = datos

        for clave, cfg in self.config.items():
            if not cfg.get("activo", True):
                continue
            req_result = self._evaluar_requisito(clave, cfg, datos)
            result.requisitos.append(req_result)

        result.apto = result._todos_cumplen()
        result.estado = "Apto" if result.apto else "No apto"

        if result.apto:
            result.descripcion = "Cumple todos los requisitos de elegibilidad"
        else:
            fallos = [r for r in result.requisitos if not r.cumple]
            motivos = [f"{r.clave}: {r.detalle}" for r in fallos]
            result.descripcion = "; ".join(motivos)

        logger.info(f"  {student_id}: {result.estado} — {result.descripcion}")
        return result

    def _merge_datos(self, extracted: dict) -> dict:
        merged = {}
        for doc_type, entry in extracted.items():
            datos = entry.get("datos", {}) if isinstance(entry, dict) else {}
            for k, v in datos.items():
                if v not in (None, "", 0, "0", [], {}):
                    merged[k] = v
        return merged

    def _valor_limpio(self, val) -> str:
        if val is None:
            return ""
        return str(val).strip().lower()

    def _valor_float(self, val, default: float = 0.0) -> float:
        try:
            return float(val) if val not in (None, "", "ninguna", "ninguno") else default
        except (ValueError, TypeError):
            return default

    def _buscar_en_merged(self, datos: dict, *campos) -> str:
        for c in campos:
            val = datos.get(c)
            if val not in (None, "", "0", 0):
                return self._valor_limpio(val)
        return ""

    def _evaluar_requisito(self, clave: str, cfg: dict, datos: dict) -> RequisitoResult:
        rr = RequisitoResult(clave, cfg.get("descripcion", ""))

        if clave == "a_matriculado_uco":
            rr.cumple, rr.detalle = self._req_matriculado_uco(cfg, datos)
        elif clave == "b_matricula_vigor":
            rr.cumple, rr.detalle = self._req_matricula_vigor(cfg, datos)
        elif clave == "c_creditos_50":
            rr.cumple, rr.detalle = self._req_creditos_50(cfg, datos)
        elif clave == "d_certificado_delitos":
            rr.cumple, rr.detalle = self._req_certificado_delitos(cfg, datos)
        elif clave == "e_practicas_misma_entidad":
            rr.cumple, rr.detalle = self._req_practicas_misma_entidad(cfg, datos)
        elif clave == "f_practicas_maximo_total":
            rr.cumple, rr.detalle = self._req_practicas_maximo_total(cfg, datos)
        elif clave == "g_movilidad":
            rr.cumple, rr.detalle = self._req_movilidad(cfg, datos)
        elif clave == "h_bolsa_renuncia":
            rr.cumple, rr.detalle = self._req_bolsa_renuncia(cfg, datos)
        else:
            rr.cumple = True
            rr.detalle = "Requisito no implementado, se omite"

        return rr

    def _req_matriculado_uco(self, cfg: dict, datos: dict) -> tuple:
        campos = cfg.get("campos_busqueda", ["universidad", "institucion"])
        validos = cfg.get("valores_validos", ["universidad de córdoba", "uco", "córdoba"])

        valor = self._buscar_en_merged(datos, *campos)
        if not valor:
            return (False, "No se pudo determinar la universidad de origen")

        for v in validos:
            if v in valor:
                return (True, f"Matriculado en universidad válida: {valor}")

        return (False, f"Universidad no válida: {valor}. Debe ser Universidad de Córdoba o centros adscritos")

    def _req_matricula_vigor(self, cfg: dict, datos: dict) -> tuple:
        campo_mat = cfg.get("campo_matricula", "matricula_vigor")
        campo_exp = cfg.get("campo_expediente", "expediente_abierto")
        esperado = cfg.get("valor_esperado", "sí")

        matricula = self._valor_limpio(datos.get(campo_mat, ""))
        expediente = self._valor_limpio(datos.get(campo_exp, ""))

        fallos = []
        if matricula != esperado:
            fallos.append(f"matrícula en vigor: {matricula or 'no informada'}")
        if expediente != esperado:
            fallos.append(f"expediente abierto: {expediente or 'no informado'}")

        if fallos:
            return (False, "; ".join(fallos))
        return (True, "Matrícula en vigor y expediente abierto")

    def _req_creditos_50(self, cfg: dict, datos: dict) -> tuple:
        excepciones = cfg.get("excepcion_titulaciones", ["master", "máster", "doctorado"])
        tipo_tit = self._valor_limpio(datos.get("tipo_titulacion", ""))

        for exc in excepciones:
            if exc in tipo_tit:
                return (True, f"Titulación ({tipo_tit}) exenta del requisito de créditos mínimos")

        num = self._valor_float(datos.get(cfg["numerador"], 0))
        den = self._valor_float(datos.get(cfg["denominador"], 0))
        min_ratio = cfg.get("min_ratio", 0.5)

        if den <= 0:
            return (False, "No se pudo determinar el total de créditos")

        ratio = num / den
        if ratio >= min_ratio:
            return (True, f"Créditos superados: {num}/{den} ({ratio*100:.0f}%) ≥ 50%")
        else:
            return (False, f"Créditos superados: {num}/{den} ({ratio*100:.0f}%) < 50%")

    def _req_certificado_delitos(self, cfg: dict, datos: dict) -> tuple:
        campo_cond = cfg.get("campo_condicion", "interaccion_menores")
        campo_cond_alt = cfg.get("campo_condicion_alt", "interaccion_discapacidad")
        campo_cert = cfg.get("campo_certificado", "certificado_delitos")
        esperado = cfg.get("valor_esperado", "sí")

        condicion = self._valor_limpio(datos.get(campo_cond, ""))
        condicion_alt = self._valor_limpio(datos.get(campo_cond_alt, ""))
        certificado = self._valor_limpio(datos.get(campo_cert, ""))

        if condicion != esperado and condicion_alt != esperado:
            return (True, "No requiere certificado (sin interacción con menores o discapacidad)")

        if certificado == esperado:
            return (True, "Certificado negativo de delitos sexuales vigente")
        else:
            return (False, "Requiere certificado negativo de delitos sexuales y no se ha informado")

    def _req_practicas_misma_entidad(self, cfg: dict, datos: dict) -> tuple:
        campo_ent = cfg.get("campo_entidad", "practicas_previas_entidad")
        campo_dur = cfg.get("campo_duracion", "duracion_practicas_entidad_meses")
        max_meses = cfg.get("max_duracion_meses", 12)

        entidad = self._valor_limpio(datos.get(campo_ent, ""))
        duracion = self._valor_float(datos.get(campo_dur, 0))

        if not entidad or entidad in ("ninguna", "ninguno", "n/a", "no", ""):
            return (True, "Sin prácticas previas en misma entidad")

        if duracion < max_meses:
            return (True, f"Prácticas en {entidad}: {duracion} meses < {max_meses} meses máximo")
        else:
            return (False, f"Prácticas en {entidad}: {duracion} meses ≥ {max_meses} meses máximo")

    def _req_practicas_maximo_total(self, cfg: dict, datos: dict) -> tuple:
        campo_dur = cfg.get("campo_duracion_total", "duracion_practicas_total_meses")
        max_meses = cfg.get("max_duracion_meses", 24)

        duracion = self._valor_float(datos.get(campo_dur, 0))

        if duracion < max_meses:
            return (True, f"Duración total de prácticas: {duracion} meses < {max_meses} meses máximo")
        else:
            return (False, f"Duración total de prácticas: {duracion} meses ≥ {max_meses} meses máximo")

    def _req_movilidad(self, cfg: dict, datos: dict) -> tuple:
        campo_tipo = cfg.get("campo_tipo", "tipo_estudiante")
        valor_mov = cfg.get("valor_movilidad", "movilidad")
        campo_incomp = cfg.get("campo_incompatibilidad", "bolsa_ayuda_actual")
        valor_incomp = cfg.get("valor_incompatible", "sí")

        tipo = self._valor_limpio(datos.get(campo_tipo, ""))

        if valor_mov not in tipo:
            return (True, "Estudiante no es de movilidad")

        bolsa = self._valor_limpio(datos.get(campo_incomp, ""))
        if valor_incomp in bolsa:
            return (False, "Estudiante de movilidad incompatible con bolsa o ayuda económica actual")
        else:
            return (True, "Estudiante de movilidad sin incompatibilidades")

    def _req_bolsa_renuncia(self, cfg: dict, datos: dict) -> tuple:
        campo_bolsa = cfg.get("campo_bolsa", "bolsa_ayuda_actual")
        campo_meses = cfg.get("campo_meses", "meses_incorporado")
        min_meses = cfg.get("min_meses_incorporado", 1)
        valor_bolsa = cfg.get("valor_bolsa", "sí")

        bolsa = self._valor_limpio(datos.get(campo_bolsa, ""))
        meses = self._valor_float(datos.get(campo_meses, 0))

        if valor_bolsa not in bolsa:
            return (True, "Sin bolsa o ayuda económica activa")

        if meses > min_meses:
            return (False, f"Recibe bolsa/ayuda y lleva {meses} meses incorporado (> {min_meses}). No puede aceptar nueva práctica remunerada sin causa justificada")
        else:
            return (True, "Recibe bolsa pero lleva menos de 1 mes incorporado")
