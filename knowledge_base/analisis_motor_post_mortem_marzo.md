# Post-Mortem y Arquitectura de Asignaciones (Marzo 2026)

## El Problema: "La Ilusión Óptica de la Matriz Borrada"

Durante las pruebas de la interfaz de asignación, surgió un error severo donde al hacer clic en "Generar", la matriz de dispositivos configurada por el usuario (los cupos) aparentemente se borraba y regresaba a `0`. Si el usuario volvía a guardar, los datos en la base de datos se destruían permanentemente. Parecía que el motor estaba reseteando intencionalmente la matriz.

La investigación profunda reveló que no era una sola falla, sino **3 bugs críticos fallando en cadena** en 3 sistemas diferentes:

### 1. El Truncamiento de Supabase (Límite Oculto de 1000)
* **Dónde:** Motor Python (`motor_asignaciones_supabase.py`)
* **Qué:** La tabla `calendario_dispositivos` tenía más de 22,000 registros históricos. El motor extraía los datos usando un simple `select("*")` sin filtro de fechas.
* **El Fallo:** PostgREST (Supabase) tiene un límite de seguridad estricto que corta las respuestas masivas en 1000 filas. El motor solo descargó las primeras 1000 filas, que correspondían al año 2024.
* **Consecuencia:** Para el motor, Marzo de 2026 **estaba vacío**. Al no encontrar configuraciones dictaminadas por el humano, la regla del motor dictaba no asumir nada y asignar a nadie (Cupo = 0).

### 2. El Crash Silencioso (Violación `chk_orden`)
* **Dónde:** Motor Python (Cálculo Multicriterio > Tabla `menu`)
* **Qué:** Al no poder asignar casi nadie, el algoritmo de scoring (que resta puntos por inactividad o repeticiones) otorgó puntajes negativos (ej. `-55`) a algunos residentes sobrantes de Fase 1.
* **El Fallo:** Al intentar escribir los resultados en la tabla `menu` usando este puntaje negativo para la columna `orden`, la base de datos Postgres disparó el constraint `chk_orden` (que requiere números positivos). Esto **destruyó la ejecución de Python en seco**.
* **Consecuencia:** Python crasheó silenciosamente antes de escribir los datos, dejando la tabla `menu` completamente vacía (dado que el botón Generar primero limpia la fecha actual con el script `undo`).

### 3. El Fallback Destructivo del Frontend
* **Dónde:** Interfaz React (`page.tsx`)
* **Qué:** Tras el crash del motor, el frontend refrescó la página (`window.location.reload()`).
* **El Fallo:** Al cargar, intentó llenar `calendarDb` (la matriz visual). Como había un problema de parseo de fechas (`01/03` vs `1/3`), no logró matchear los datos de Supabase. El código entonces decía: *"Si no encontrás el cupo configurado en bd, mostrá la cantidad de gente actualmente asignada" (`matriz.length`)*. Como la tabla `menu` estaba vacía por el crash del motor, `matriz.length` era = 0.
* **Consecuencia:** El frontend inyectó `0`s en todas las pantallas. Peor aún, cuando el usuario apretaba **"Guardar Matriz de Dispositivos"**, el frontend tomaba estos `0` falsos y los commiteaba a la tabla `calendario_dispositivos`, destruyendo la base de datos de manera definitiva e instruyéndole conscientemente al motor que asigne a 0 personas.

---

## La Solución Implementada (Arquitectura Data-Flow v2.0)

Para asegurar que esto jamás vuelva a ocurrir, se estableció el siguiente data flow rígido:

1. **La Única Verdad:`calendario_dispositivos`:**
   El frontend ya no intenta derivar ni adivinar cupos. Extrae estricta y limpiamente de `calendario_dispositivos` mapeando `parseInt(dia)` y `parseInt(mes)` para garantizar consistencia UI.

2. **Cero Inventos (Regla de Oro):**
   Si la base de datos no tiene un registro para ese Día/Dispositivo, el algoritmo ya no asume `cupo_optimo`. Asume estrictamente **0** y no asigna a nadie. El Humano debe decidir abrirlo configurando la matriz.

3. **Paginación Defensiva:**
   **TODAS** las consultas de alto volumen en el Motor Python (`calendario_dispositivos`, `dias`, `inasistencias`) han sido recubiertas con barreras `.gte` y `.lte` al inicio y fin del mes (`mes_objetivo`) para asegurar que jamás gatillen el límite de seguridad de 1000 filas de PostgREST.

4. **Clamp Protector de Scoring:**
   El puntaje final de priorización multi-criterio se sube con `max(1, score)` antes de impactar en Postgres. Esto asegura el cumplimiento de `chk_orden` y blindaje contra crash backend.

## Acciones de Actualización (Knowledge Base)

Se sobrescribió por completo el archivo `Fase_2_Motor_Python.md` eliminando toda referencia a los prototipos `motor_asignacion_apertura5.py` desactualizados. Ahora documenta estricta y detalladamente cómo el Motor Python responde únicamente a las reglas de la v2.0 actualizadas en `page.tsx` y `supabase`. Se actualizaron los síntomas y soluciones exactos en `errores_y_soluciones_frontend.md` como referencia técnica para futuras migraciones.
