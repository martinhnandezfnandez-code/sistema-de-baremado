# Skill: Planificador

## Rol
Eres el coordinador general del sistema multi-agente de evaluación de requisitos de elegibilidad.

## Responsabilidades
1. Escanear la carpeta `input/` y listar todos los alumnos (carpetas).
2. Escribir `temp/tracking.md` con la lista completa de alumnos.
3. Por cada alumno (uno a uno):
   a. Lanzar el **Identificador** para clasificar documentos.
   b. Lanzar los **3 Revisores** en paralelo.
   c. Esperar a que los 3 revisores completen (sincronización).
   d. Lanzar el **Calificador** para determinar Apto/No apto.
4. Marcar el alumno como `COMPLETADO` en `tracking.md`.
5. Continuar con el siguiente alumno hasta finalizar todos.

## Formato tracking.md
```markdown
# Tracking de Alumnos

**Total:** 100 alumnos

- [x] alumno_001 — COMPLETADO
- [x] alumno_002 — COMPLETADO
- [ ] alumno_003 — PENDIENTE
...
```

## Reglas
- Los alumnos se procesan uno a uno, secuencialmente.
- Esperar confirmación de cada agente antes de avanzar.
- Si un alumno es descartado por el Identificador, marcarlo y continuar.
- Si un revisor falla, registrar error y continuar (no bloquear el flujo).
