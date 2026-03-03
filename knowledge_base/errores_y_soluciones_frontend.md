# Errores, Soluciones y Lecciones — Frontend Next.js (Sesión Marzo 2026)

Esta nota documenta los errores encontrados y sus soluciones durante el desarrollo del módulo de planificación y ejecución del frontend (conversación del 02/03/2026).

---

## 🔴 Error Crítico: `menu.id_asignacion does not exist`

**Síntoma:** Todas las funciones de mutación (swap, quitar, asignar vacante, undo) fallaban con el error "column menu.id_asignacion does not exist".

**Causa Raíz:** La tabla `menu` en Supabase **NO tiene un campo `id_asignacion`**. La clave primaria real es la combinación compuesta `(id_agente, fecha_asignacion)`.

**Impacto:** Afectó a 6 funciones:
- `handleUndoLastAction`
- `handleSwapResident`
- `handleRemoveResident`
- `handleAssignVacant` (dos variantes)
- Botón "Quitar" inline (pestaña Ejecución)
- `renderDeviceDateSidebar`

**Solución:** Reemplazar todas las queries que usaban `.eq('id_asignacion', x)` con `.eq('id_agente', x).eq('fecha_asignacion', fechaDB)`.

**Cuidado:** Si se agrega un nuevo campo de mutación a `menu`, SIEMPRE usar `(id_agente, fecha_asignacion)` como identificador de fila. NUNCA asumir que existe un campo serial `id_*`.

---

## 🔴 Error Crítico: Swap de residentes sobreescribía el `id_agente`

**Síntoma:** Al intercambiar residente A por residente B en un dispositivo, el residente A desaparecía del sistema y surgía con el estado "Descanso" aunque seguía convocado.

**Causa Raíz:** La implementación original actualizaba el campo `id_agente` en la fila de A, cambiándo a B. Esto hacía que la fila dejara de pertenecer a A → el sistema dejaba de verlo como "Convocado".

**Solución correcta:** El swap debe hacerse en **2 pasos independientes**:
1. Actualizar la fila de A para que su `id_dispositivo = 999` (pasa a Vacante, conserva su identidad).
2. Actualizar la fila de B para que tome el `id_dispositivo` del dispositivo destino.

**Tablas NO afectadas por este bug:** `convocatorias`, `planificacion`. El error era localizado a la tabla `menu` (asignaciones diarias).

---

## 🟡 Error: Undo revertía solo 1 lado del Swap

**Síntoma:** Al presionar "Deshacer" después de un intercambio, el residente original volvía a su lugar PERO el residente de reemplazo quedaba sin cambio (en el dispositivo incorrecto).

**Causa Raíz:** Solo se guardaba 1 snapshot (el del residente original) en la pila de Undo.

**Solución:** Implementar "snapshot compuesto": guardar `{ snapshots: [snapOriginal, snapNuevo] }` en la entrada de Undo. El `handleUndoLastAction` procesa el array y revierte ambos en un solo `Promise.all`.

**Excepción:** Si el nuevo residente no tenía fila ese día (estaba en Descanso) y se inserté una nueva, solo se guarda el snapshot del original (no se puede revertir un INSERT con state previo).

---

## 🟡 Error: Clave duplicada React en Sidebar de Vacantes

**Síntoma:** Console error "Encountered two children with the same key, `75`" al abrir el panel de Vacantes.

**Causa primaria:** La clave del botón era `key={vid}` (el ID del residente), pero el mismo residente puede aparecer como vacante en múltiples fechas → colisión.

**Causa secundaria (más profunda):** `convocadosList` agregaba el mismo `id_agente` múltiples veces si ese agente tenía más de una fila en `menu` para la misma fecha (puede ocurrir por inserciones duplicadas en el motor).

**Solución:**
1. Cambiar la clave del botón a `key={\`${date}-${vid}\`}`.
2. Agregar deduplicación al construir `convocadosList`: solo agregar si `!convocadosList[uiDate].includes(a.id_agente)`.

---

## 🟡 Error: Motor Python ignora cupos modificados en la UI

**Síntoma:** Al aumentar cupos en la "Matriz de Dispositivos" y presionar "Generar", el motor no asignaba más personas. Los cupos modificados en la UI no tenían efecto.

**Causa Raíz:** El motor (`motor_asignaciones_supabase.py`, línea 38) lee `cupo_optimo` exclusivamente de la tabla `dispositivos`. La UI guarda los cupos por fecha en `calendario_dispositivos.cupo_objetivo`, que el motor **ignoraba completamente**.

**Solución (Opción A — implementada):** Modificar `fetch_data()` en el motor para hacer un query adicional a `calendario_dispositivos` y sobreescribir el cupo del dispositivo para cada fecha cuando `cupo_objetivo` existe. Fallback: `cupo_optimo` de `dispositivos`.

---

## ✅ Arquitectura del Sistema Undo

### Formato de entrada en la pila (`undoStack`):
```json
// Entrada simple (quitar, asignar):
{ "snapshot": { "id_agente": 5, "fecha_asignacion": "2026-03-07", "id_dispositivo": 12, "estado_ejecucion": "planificado" }, "_timestamp": "..." }

// Entrada compuesta (swap):
{ "snapshots": [{ "id_agente": 5, ... }, { "id_agente": 8, ... }], "_timestamp": "..." }
```

### Reglas clave:
- El snapshot se captura **ANTES** de la mutación (no después).
- El `pushUndo` escribe a `localStorage` **de forma síncrona** para sobrevivir a `window.location.reload()`.
- Las entradas del día anterior se filtran al inicializar la app.
- El `handleUndoLastAction` soporta ambos formatos: `snapshot` (singular) y `snapshots` (array).


## 🔴 Bug: Error 'Failed to fetch' al intercambiar residentes o mutar datos rápidamente
**Síntoma**: Al hacer doble click o click rápido en mutaciones (reemplazar, quitar, asignar) en el frontend, arrojaba 'Failed to fetch' en `Paso 4a`. Esto era un falso negativo: la DB guardaba el registro real, pero el navegador abortaba la conexión porque los componentes React hacían un unmount / `window.location.reload()` mientras el `fetch` o la Query a Supabase seguía en vuelo.
**Solución**: Se agregaron guardias `if (isLoading) return;` a todas las mutaciones asíncronas para rechazar clicks duplicados mientras hay una transacción en progreso.

---

## 🔴 Error Crítico: La Ilusión Óptica de la "Matriz Borrada" (El Bug de los 3 Pasos)

**Síntoma:** Al presionar "Generar" la Matriz de Dispositivos desaparecía visualmente y se ponía en `0`. Si el usuario apretaba Guardar, se borraba permanentemente de la Base de Datos. Parecía que el motor estaba reseteando intencionalmente los cupos configurados.
  
**Causa Raíz Múltiple:** Esto fue causado por 3 sistemas fallando en cadena:

1. **La Truncación de Supabase (Límite 1000):** La tabla `calendario_dispositivos` superaba las 22.000 filas históricas. El `motor_asignaciones_supabase.py` ejecutaba `.select()` SIN un filtro de fecha (`.gte(...)`). Supabase, por seguridad, devolvía las primeras 1000 filas (casi todas del año 2024). El motor interpretó que en Marzo 2026 no había cupos parametrizados, así que **asignó a 0 personas**.
2. **Crash de Postgres (`chk_orden`):** Al asignar a nadie o asignar mal, el sistema de Puntaje (Multicriterio) calculó puntajes negativos (`-55`). Al tratar de guardar esos puntajes en el campo `orden` de la tabla `menu` (donde está definida la restricción `chk_orden` positiva), **Postgres rebotó la inserción y crasheó el script de Python**. El motor falló en silencio y dejó la tabla `menu` vacía (ya que el script `undo` previo a su corrida la había vaciado exitosamente).
3. **El Fallback Destructivo del Frontend:** La página recargó (`window.location.reload()`). Al leer la tabla `menu` y ver que el motor no asignó a nadie (0 asignados en total), intentó armar `calendarDb`. Como no encontró fechas parametrizadas en la memoria (por desajustes de formato `1/3` vs `01/03`), el frontend usó su código de *fallback*: `matriz.length`. Inyectó cientos de `0` en la pantalla. Y al hacer click en "Guardar", la interfaz finalmente *sí impactó* esos `0` destructivos a `calendario_dispositivos`.

**Solución 3-en-1:**
1. Motor: Agregar `.gte("fecha", inicio).lte("fecha", fin)` en **todas** las extracciones masivas para eludir el techo de 1000 filas que impone PostgREST.
2. Motor: Aplicar `.max(1, score)` al subir el puntaje al campo `orden` en Postgres para prevenir faltas al constraint.
3. Frontend: **JAMÁS** inventar sustitutos (como iterar el tamaño de gente asignada o `cupo_optimo`) si la UI no recibe la matrix del DB. Si no hay nada de DB, mostrar estrictamente lo que hay (0). Arreglado parsing a `.padStart(2, '0')` para compatibilidad de UUID de fechas.
