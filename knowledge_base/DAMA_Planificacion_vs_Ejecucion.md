# Arquitectura de Datos DAMA: Planificación vs. Ejecución

Este documento establece los lineamientos arquitectónicos y de calidad de datos (Criterios DAMA) para el flujo de asignación de dispositivos en El Molino, diferenciando claramente el estado *Planificado* del estado *Ejecutado*.

---

## 1. Data Architecture: Separación de Estados (Planificación vs. Movimientos)

Según las mejores prácticas de Arquitectura de Datos, los sistemas operativos deben separar el "Deber Ser" (Plan) del "Ser" (Realidad), permitiendo medir desvíos.

### A. Tabla `asignaciones` (El Plan - "Deber Ser")
- **Rol:** Alimenta la interfaz de *Planificación*.
- **Naturaleza:** Teórica y predictiva. Dicta a dónde *debería* ir el residente según el motor y las reglas de negocio.
- **Columna Clave:** `es_capacitacion_servicio` (BOOLEAN). Si se asigna a alguien a un dispositivo sin estar capacitado previamente, se marca en `true`.

### B. Tabla `menu` (La Ejecución - "Movimientos Reales")
- **Rol:** Alimenta la interfaz de *Movimientos* diarios (Ejecución en piso).
- **Naturaleza:** Fáctica e histórica. Registra lo que *realmente* sucedió ese día.

Para cumplir con el registro exacto de movimientos, la tabla `menu` debe expandirse con las siguientes columnas (Data Quality & Lineage):
- `estado_ejecucion` (VARCHAR): `'planificado'`, `'ausente'`, `'reasignado_decision'`, `'reasignado_necesidad'`. Reemplaza la ambigüedad de ausencias o cambios bruscos.
- `dispositivo_origen` (INTEGER NULL): Si fue movido, ¿dónde estaba planificado originalmente? (Data Lineage).
- `dispositivo_cerrado` (BOOLEAN): Marca si el dispositivo no abrió al público finalmente.
- `es_capacitacion_servicio` (BOOLEAN): Copia de `asignaciones`, ya que el aprendizaje en servicio puede decidirse on-the-fly en la interfaz de Movimientos.

---

## 2. Master Data Management & Interoperabilidad (Triggers)

El usuario indicó que **ambas interfaces** (Planificación y Movimientos) pueden detonar una capacitación en servicio.

### El Trigger `es_capacitacion_servicio` -> `capacitaciones_participantes`
Cuando la columna `es_capacitacion_servicio` pasa a `true` (ya sea en `asignaciones` o `menu`), un Trigger (o función en la App) impacta la tabla de historial de capacitaciones.

**Campos obligatorios requeridos para evitar fallos (Data Quality Constraints):**
1. `id_agente` (viene de la asignación).
2. `id_cap` (Debe resolverse consultando `capacitaciones_dispositivos` usando el `id_dispositivo`).
3. `asistio` = `TRUE`.
4. `observaciones` = *"Acreditación por capacitación en servicio (Auto-generado)"*.

*Nota DAMA:* Es vital que el trigger valide si el agente ya tiene esa capacitación antes de intentar el INSERT, para prevenir violación de Unique Constraints de `(id_agente, id_cap)`.

---

## 3. Data Integration & Lineage: Conteo de Dispositivos Coordinados

El sistema lleva un ranking o puntaje de cuántas veces un residente coordinó un dispositivo (Score de Rotación).

**Flujo del Dato (Data Flow):**
1. **Paso 1 (Cálculo Previo):** El Motor de asignaciones lee el historial oficial para proponer el mes.
2. **Paso 2 (Proyección):** Durante el mes, la cantidad de coordinaciones proyectadas se nutre de la tabla `asignaciones` (planificadas).
3. **Paso 3 (Ajuste Real - "Single Source of Truth"):** Al finalizar el día, la interfaz de *Movimientos* (`menu`) tiene la última palabra. Si un residente faltó (`estado_ejecucion = 'ausente'`), el conteo debe **restarse** o simplemente recalcularse leyendo directamente de `menu` validado, y no de `asignaciones`.

### Recomendación de Modelado: Vista Materializada o CTE
Para el conteo real e histórico que alimenta al Motor de Asignación del próximo mes, la consulta SQL debe leer EXCLUSIVAMENTE de la tabla `menu` (movimientos confirmados), considerando solo aquellos registros donde `dispositivo_cerrado = FALSE` y el agente no haya estado ausente.
