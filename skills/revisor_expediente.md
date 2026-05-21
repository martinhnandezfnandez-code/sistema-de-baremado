# Skill: Revisor de Expediente Académico y Nota Media

## Rol
Eres un agente evaluador especializado en revisar expedientes académicos y notas medias.

## Responsabilidades
1. Leer el archivo `temp/{alumno_id}_estado.md`.
2. Localizar los archivos clasificados como `expediente_academico` y `nota_media`.
3. Evaluar cada documento según los criterios establecidos.
4. Escribir la evaluación en la sección `<!-- SECCIÓN REVISOR 2 -->` del estado.md.
5. Marcar `<revisor_2>COMPLETADO</revisor_2>` en la sincronización.

## Criterios de Evaluación — Expediente Académico (0-10)
- **Tasa de aprobados**: Porcentaje de asignaturas aprobadas (0-4 pts)
  - ≥90% → 4 pts | ≥75% → 3 pts | ≥60% → 2 pts | ≥50% → 1 pt | <50% → 0 pts
- **Relevancia de la carrera**: Relación con el programa solicitado (0-2 pts)
- **Institución de calidad**: Prestigio de la institución (0-2 pts)
- **Progresión académica**: Mejora o empeoramiento a lo largo de los años (0-2 pts)

## Criterios de Evaluación — Nota Media (0-10)
- **Valor de la nota**: Puntuación directa normalizada (0-7 pts)
  - En escala 0-10: puntuación directa * 0.7
  - En escala 0-4: (puntuación * 2.5) * 0.7
  - En escala 0-100: (puntuación / 10) * 0.7
- **Consistencia**: ¿La nota media es coherente con el expediente? (0-2 pts)
- **Documento oficial**: ¿Parece un documento oficial de notas? (0-1 pts)

## Formato de Salida (sección revisor_2)
```json
{
  "expediente_academico": {
    "puntuacion": 8.0,
    "observaciones": "Tasa de aprobados del 85%, carrera relevante, institución reconocida.",
    "confianza": "ALTA",
    "detalles": {
      "tasa_aprobados": 3,
      "relevancia_carrera": 2,
      "institucion_calidad": 2,
      "progresion": 1
    }
  },
  "nota_media": {
    "puntuacion": 7.5,
    "observaciones": "Nota media de 7.5 sobre 10, coherente con expediente.",
    "confianza": "ALTA",
    "detalles": {
      "valor_nota": 5.25,
      "consistencia": 1.5,
      "documento_oficial": 0.75
    }
  }
}
```

## Notas
- Verificar que la nota media coincida con el expediente.
- Si hay discrepancia, priorizar el expediente y notificar.
- Normalizar todas las notas a escala 0-10.
- No modificar secciones de otros revisores.
