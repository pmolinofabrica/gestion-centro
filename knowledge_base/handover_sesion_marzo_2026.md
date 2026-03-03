# 🚀 Handover Sesión Marzo 2026 (Para la próxima IA)

¡Hola! Si estás leyendo esto al iniciar una nueva sesión, venimos de un trabajo muy profundo estabilizando el **Motor de Asignaciones v2.0** y el Frontend. Aquí tienes el estado exacto del proyecto hoy:

## 1. Estado de la Base de Datos (Supabase)
- **Fuente de Verdad de Cupos:** La tabla `calendario_dispositivos` es la jefa. El motor ya **NO inventa cupos** ni lee `cupo_optimo` por defecto. Si algo no está en `calendario_dispositivos`, el motor asume `cupo = 0` y no asigna.
- **Límite de 1000 filas vencido:** La DB tiene +22,000 registros históricos. Todas las queries masivas en Python (`motor_asignaciones_supabase.py`) ahora MUST usan filtros de fecha estables (`.gte("fecha", inicio).lte("fecha", fin)`) para evitar que PostgREST trunque los datos y el motor se quede "ciego".
- **Crash `chk_orden` solucionado:** El algoritmo multicriterio usa semillas (reproducibilidad matemática) y penaliza duro la rotación. Como daba números negativos, crasheaba al intentar insertarse en la tabla `menu` en Postgres. Ahora se usa `max(1, score)`.

## 2. Qué logramos en la sesión anterior
1. **Curamos la Ilusión de la Matriz Borrada**: Antes, si el motor fallaba en silencio, la UI no encontraba datos y autocompletaba la pantalla con `matriz.length` (llena de 0s), lo cual el humano accidentalmente guardaba destruyendo la DB. Ahora el data flow es unidireccional estricto.
2. **Undo Compuesto**: Arreglamos el sistema de "Deshacer" en React. Revertir un "Swap" (intercambio) de residentes ahora usa un `snapshot compuesto` que restaura a las 2 personas involucradas de un solo impacto.
3. **PK de tabla `menu`**: Documentamos que `menu` NO tiene `id_asignacion`. Su identificador único es la tupla composita `(id_agente, fecha_asignacion)`.

## 3. Comandos Operativos
- **Levantar el proyecto:**
  ```bash
  cd /home/pablo/Documentos/gestion-centro/frontend
  npm run dev
  ```
- El motor en Python se llama directamente desde el botón "Generar" del frontend vía el endpoint Next.js API `/api/run-engine`.

## 4. Próximos pasos pendientes (To-Do para esta nueva sesión)
- [ ] Revisar y testear mejoras solicitadas por el humano en la interacción manual de la UI (Barra lateral, intercambios, visualización de ausentes).
- [ ] Cualquier optimización del "Undo" que haya quedado suelta en la lista de deseos del humano.

> Archivos críticos a revisar en caso de duda: `frontend/src/app/page.tsx`, `scripts/python/motor_asignaciones_supabase.py`, y la subcarpeta `knowledge_base/` que fue purgada y actualizada.

## 5. Integración Google Apps Script + Supabase (Hallazgos y Reglas)
En sesiones recientes conectamos Google Forms con Supabase a través de Apps Script (`sync_formularios.gs`), resolviendo múltiples bloqueos técnicos:
- **CHECK Constraints Estrictos (`chk_motivo_inasis`, `chk_estado_inasis`):** Supabase rechaza inserciones si el string no coincide exactamente con el `ARRAY` definido. *Regla de oro:* En `sync_formularios.gs`, siempre mapear las respuestas largas del formulario humano (ej. "Inasistencia justificada por enfermedad") a los *tokens exactos* esperados por la base de datos (ej. `"medico"`, `"estudio"`, `"injustificada"`).
- **Fechas y el Constraint `chk_fecha_inasis_valida`:** Postgres y Supabase son implacables con años erróneos (ej. 2025, 0026, 2027) ingresados por error humano. *Solución:* La función `normalizarFecha_` de Apps Script ahora **fuerza el año actual** (`new Date().getFullYear()`) al armar el string `YYYY-MM-DD` que viaja por el REST API de Supabase, garantizando que no haya error `23514` (Failing row).
- **Booleanos y UI Forms:** Columnas como `requiere_certificado` o `genera_descuento` se interpolan lógicamente dependiendo del motivo exacto seleccionado en el formulario, quitándole carga mental al usuario e impidiendo errores en base de datos.
