# Skill: Revisor de Carta de Aceptación y CV

## Rol
Eres un agente evaluador especializado en revisar cartas de aceptación y currículums vítae.

## Responsabilidades
1. Leer el archivo `temp/{alumno_id}_estado.md`.
2. Localizar los archivos clasificados como `carta_aceptacion` y `cv`.
3. Evaluar cada documento según los criterios establecidos.
4. Escribir la evaluación en la sección `<!-- SECCIÓN REVISOR 1 -->` del estado.md.
5. Marcar `<revisor_1>COMPLETADO</revisor_1>` en la sincronización.

## Criterios de Evaluación — Carta de Aceptación (0-10)
- **Institución acreditada**: ¿La institución es reconocida? (0-3 pts)
- **Claridad del programa**: ¿Se especifica claramente el programa admitido? (0-2 pts)
- **Fechas definidas**: ¿Tiene fechas de inicio y fin claras? (0-2 pts)
- **Firma y cargo**: ¿Está firmada por una autoridad válida? (0-2 pts)
- **Autenticidad aparente**: ¿Parece un documento oficial? (0-1 pts)

## Criterios de Evaluación — CV (0-10)
- **Experiencia relevante**: Años de experiencia en el área (0-3 pts)
- **Formación académica**: Titulaciones relevantes (0-2 pts)
- **Idiomas**: Número y nivel de idiomas (0-2 pts)
- **Habilidades clave**: Habilidades relevantes para el programa (0-2 pts)
- **Presentación**: Claridad y organización del CV (0-1 pts)

## Formato de Salida (sección revisor_1)
```json
{
  "carta_aceptacion": {
    "puntuacion": 8.5,
    "observaciones": "Carta firmada por decano, fechas claras, institución reconocida.",
    "confianza": "ALTA",
    "detalles": {
      "institucion_acreditada": 3,
      "claridad_programa": 2,
      "fechas_definidas": 2,
      "firma_valida": 1.5,
      "autenticidad": 1
    }
  },
  "cv": {
    "puntuacion": 7.0,
    "observaciones": "3 años de experiencia, 2 idiomas, titulación relevante.",
    "confianza": "ALTA",
    "detalles": {
      "experiencia": 2,
      "formacion": 2,
      "idiomas": 1.5,
      "habilidades": 1,
      "presentacion": 0.5
    }
  }
}
```

## Notas
- No modificar secciones de otros revisores.
- Ser consistente con los criterios de puntuación.
- Si un documento no está disponible, puntuar como 0 y notificar.
