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

## 6. Avances Frontend Recientes (Filtros, Paginación y Fechas)
- **Sincronización de Filtros (Mes y Turno):** Se solucionó el problema donde la Matriz no reaccionaba al cambio de Turnos o Meses al agrupar `selectedMonth` y `selectedShift` en el array de dependencias del `useEffect` principal. Además, la función de Guardar ahora hace borrado seguro circunscrito **sincrónicamente al turno activo** (`.eq('id_turno', activeTurno)`) evitando borrar los ingresos de otros turnos.
- **Techo de Paginación de Supabase Eludido:** El frontend presentaba el síntoma de "Ignorar guardados y mostrar ceros" porque el fetch general de `calendario_dispositivos` y `menu` se cortaba silenciosamente en la fila 1000 (límite por defecto de seguridad de PostgREST API). Ahora las llamadas obligatoriamente envían los boundaries de su mes de enfoque: `.gte('fecha', startOfMonth).lte('fecha', endOfMonth)`.
- **Días Inválidos de Postgres Fix:** Las peticiones de boundaries mandaban rangos matemáticamente ilegales (ej. el límite hardcodeado asumiendo `-31` días para el mes de Abril). Esto resultaba en `Error 400: date/time field value out of range`. La lógica fue reemplazada por la función nativa `new Date(year, month, 0).getDate()` que computa con exactitud el último día del calendario para cualquier mes.

## 7. Decisión Arquitectónica Clave: Motor de Fines de Semana vs Sistema de Soporte Manual (Días de Semana)
Tras un análisis exhaustivo de ingeniería de datos, se decidió formalmente **dividir el enfoque algorítmico** para lidiar con el alto ruido operativo ("volatilidad") de los días de semana escolares (ej: grupos que cancelan, rotaciones multi-piso intradiarias, residentes en distintos turnos híbridos) vs los fines de semana de Apertura al Público.

**El Plan de Acción (Opción B) a ejecutar en la NUEVA SESIÓN:**
1. **Blindaje del Algoritmo (Fines de Semana):** El script `motor_asignaciones_supabase.py` queda **exclusivo** para los días de "Apertura al Público". Su tracking de penalidades no debe contaminarse con el ruido estadístico de la semana diaria.
2. **Dashboard de Armado Rápido (Días de Semana):** No se creará un "segundo motor" en Python. Para Turno Mañana y Turno Tarde, el botón "🔮 Generar" cambiará a un diseño interactivo (drag-and-drop o 1-clic manual asistido). El esfuerzo de programación debe enfocarse 100% en la UI de Next.js para que el coordinador pueda armar visual y rapidísimamente la matriz con datos crudos (escuelas del día, capacitaciones, presentes), abrazando la naturaleza caótica/flexible del turno en lugar de forzar una IA predictiva.
