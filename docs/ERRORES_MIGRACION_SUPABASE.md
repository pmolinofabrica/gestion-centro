# Registro de Errores y Soluciones: Migración a Supabase y Dashboard

Este documento recopila los problemas técnicos, errores de SQL y ajustes de lógica de negocio encontrados durante la migración de la base de datos local (SQLite) a la nube (Supabase/PostgreSQL) y el desarrollo del dashboard de visualización.

**Objetivo:** Servir de contexto para futuras iteraciones o para que otra IA pueda retomar el proyecto entendiendo las decisiones tomadas.

---

## 1. Lógica de Negocio: Cálculo de Saldos

### El Problema
Originalmente, la columna `horas_anuales` en la tabla `saldos` solo sumaba las horas de convocatorias con estados: `'confirmada', 'vigente', 'cumplida'`.
El usuario requirió que el estado `'con_inasistencia'` (ej. licencias pagas) **también sumara horas**.

### La Solución
Se modificaron los Triggers de base de datos para incluir este estado en la suma condicional.

**Cambio en SQL (Lógica):**
```sql
-- ANTES
WHERE estado IN ('confirmada', 'vigente', 'cumplida')

-- DESPUÉS
WHERE estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
```

### Archivos Afectados
*   `sql/migracion_01_modelo_hibrido_descansos.sql` (SQLite Triggers)
*   `sql/schema_postgresql.sql` (PostgreSQL Functions/Triggers)

---

## 2. Errores de SQL en PostgreSQL (Supabase)

### Error 42803: Agrupamiento y Subconsultas
Al intentar recalcular los saldos masivamente en Supabase, surgió el siguiente error:

> `ERROR: 42803: subquery uses ungrouped column "c.fecha_convocatoria" from outer query`

**Causa:**
PostgreSQL es más estricto que SQLite. No permite referenciar una columna no agrupada (`c.fecha_convocatoria`) dentro de una subconsulta selecta cuando la consulta externa ya está agrupada.

**Solución Implementada:**
Se reescribió la lógica utilizando **CTEs (Common Table Expressions)** para separar el cálculo mensual del anual, evitando la subconsulta correlacionada dentro del `GROUP BY`.

```sql
-- Solución con CTE
WITH monthly_data AS (
    -- Calcular sumas por mes
    SELECT ... GROUP BY mes
),
annual_data AS (
    -- Sumar los meses para obtener el anual
    SELECT ... FROM monthly_data GROUP BY anio
)
INSERT INTO saldos ...
SELECT ... FROM monthly_data JOIN annual_data ...
```

---

## 3. Dashboard y Entorno Python

### Dependencias Faltantes
Al intentar ejecutar el nuevo dashboard, surgió el error:
> `streamlit: no se encontró la orden`

**Solución:**
Se actualizó `python/setup_proyecto.py` para incluir `streamlit>=1.24.0` en la generación automática de `requirements.txt`.

### Requerimientos de Visualización (Dashboard v2)
Se implementaron lógicas específicas para manejar grandes volúmenes de datos (2800+ registros) sin saturar la interfaz:
1.  **Paginación Manual:** Implementada en Python/Pandas (`df.iloc[...]`) con controles de "Anterior/Siguiente".
2.  **Filtros tipo Excel:** Uso de `st.multiselect` dentro de un `st.expander` para simular filtros de hoja de cálculo.
3.  **Doble Tabla Opcional:** Checkbox para renderizar condicionalmente una segunda tabla comparativa.

---

## 4. Lógica de Negocio: Arquitectura Híbrida (SQLite + Supabase)

### El Problema
El `dashboard_rrhh_5.py` usa una lógica híbrida para consultar datos: Supabase para el año actual e histórico, y SQLite para años pasados. La lógica original comparaba el año solicitado con el año del sistema (`datetime.now().year`).

Esto causaba un error: al estar en **2026**, una consulta para el año **2025** era dirigida a SQLite (considerado "pasado"), que no tenía datos, en lugar de a Supabase, que es la fuente de verdad para 2025.

### La Solución
Se modificó la lógica en `dashboard_rrhh_5.py` (dentro de la función `execute_query`). La decisión ya no se basa en el "año actual", sino en un **año de corte fijo (2025)**.

**Cambio en Lógica (Python):**
```python
# ANTES
if int(year) == datetime.now().year:
    use_supabase = True

# DESPUÉS
cutoff_year = 2025
if int(year) >= cutoff_year:
    use_supabase = True
```
Esto asegura que todos los datos de 2025 en adelante se busquen siempre en Supabase.

---

## 5. Resumen de Archivos Clave

| Archivo | Propósito | Estado Actual |
| :--- | :--- | :--- |
| `sql/schema_postgresql.sql` | Esquema maestro para Supabase | **Actualizado** con lógica de inasistencias |
| `python/dashboard_v2.py` | Dashboard principal (Streamlit) | **Operativo** con paginación y filtros |
| `python/setup_proyecto.py` | Configuración del entorno | **Actualizado** con dependencias |
| `dashboard_rrhh_5.py` | Dashboard principal (Dash) | **Operativo** con lógica híbrida corregida |

---

**Nota para la IA:** Al retomar este proyecto, prestar especial atención a la lógica híbrida de `dashboard_rrhh_5.py` y al año de corte (`cutoff_year = 2025`). Verificar siempre si los Triggers en Supabase coinciden con la lógica definida en `sql/schema_postgresql.sql`.