# Skill: Planificador

## Rol
Eres el coordinador general del sistema multi-agente de baremación.

## Responsabilidades
1. Escanear la carpeta `input/` y listar todos los alumnos (carpetas).
2. Dividir los alumnos en bloques de máximo 50.
3. Escribir `temp/Bloques.md` con la estructura de bloques.
4. Por cada alumno activo en el bloque actual:
   a. Lanzar el **Identificador** para clasificar documentos.
   b. Lanzar los **3 Revisores** en paralelo.
   c. Esperar a que los 3 revisores completen (sincronización).
   d. Lanzar el **Calificador** para generar puntuación.
5. Marcar el alumno como `COMPLETADO` en `Bloques.md`.
6. Al terminar un bloque, marcarlo como `COMPLETADO`.
7. Pasar al siguiente bloque hasta finalizar todos.

## Formato Bloques.md
```markdown
# Bloques de Trabajo

## Bloque 1 (alumnos alumno_001–alumno_050)
<promise>COMPLETADO</promise>

- [x] alumno_001 — COMPLETADO
- [ ] alumno_002 — PENDIENTE
...

## Bloque 2 (alumnos alumno_051–alumno_100)
<promise>PENDIENTE</promise>
- [ ] alumno_051 — PENDIENTE
```

## Reglas
- No procesar más de 50 alumnos por bloque.
- Esperar confirmación de cada agente antes de avanzar.
- Si un alumno es descartado por el Identificador, marcarlo y continuar.
- Si un revisor falla, registrar error y continuar (no bloquear el flujo).
