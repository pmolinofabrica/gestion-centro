# Fase 1: Arquitectura de Datos y SSOT (Supabase)

Esta fase documenta el modelo relacional de "Gestión Centro", actuando como la fuente única de verdad (Single Source of Truth) para la persistencia de datos y la integridad referencial del sistema de asignaciones.

## 1. Modelo de Entidad-Relación (Conceptual)
El sistema se rige por un eje tripartito: **Agente (Personas) <-> Calendario (Tiempo) <-> Dispositivo (Espacio)**. La intersección de estas tres dimensiones ocurre en la tabla principal `menu`.

## 2. Diccionario de Tablas Principales

### A. `datos_personales` (Maestro de Residentes)
- **Propósito**: Repositorio central de información de los residentes.
- **PK**: `id_agente` (Integer).
- **Columnas Críticas**:
  - `apellido`, `nombre`: Identidad.
  - `cohorte`: Filtro temporal (actualmente priorizando 2026).
- **Nota DAMA**: Actúa como el catálogo maestro de recursos humanos.

### B. `dispositivos` (Maestro de Espacios)
- **Propósito**: Definición de mesas de trabajo y dispositivos de mediación.
- **PK**: `id_dispositivo` (Integer).
- **Columnas Críticas**:
  - `piso_dispositivo`: Jerarquía de ubicación (P1, P2, P3).
  - `cupo_minimo`, `cupo_optimo`: Reglas de capacidad para el motor de asignación.
- **Identificador Especial**: El `id_dispositivo = 999` representa el "Pool de Vacantes" (Sin Asignar).

### C. `menu` (Corazón de la Asignación)
- **Propósito**: Registro oficial de quién está en qué dispositivo y en qué fecha.
- **PK**: `id_asignacion` (BigInt/Serial).
- **Columnas Críticas**:
  - `id_agente`: FK a `datos_personales`.
  - `id_dispositivo`: FK a `dispositivos`.
  - `fecha_asignacion`: Fecha Clave (Formato `AAAA-MM-DD`).
  - `estado_ejecucion`: Ciclo de vida del registro (`planificado`, `ausente`, `ejecutado`).
  - `orden`: Almacena el **Score Matemático** generado por el motor Python (prioridad).

### D. `calendario_dispositivos` (Planeamiento de Capacidad)
- **Propósito**: Define qué dispositivos se abren cada día y cuántas plazas ofrecen.
- **Columnas**: `id_dispositivo`, `fecha`, `cupo_habilitado`.

---

## 3. Lógica de Sincronización e Integridad

### Trazabilidad de Estados (`estado_ejecucion`)
Para separar la **Planificación** de la **Ejecución Real**, el sistema utiliza esta columna:
1. `planificado`: Estado inicial inyectado por el Motor Python o el Planificador React.
2. `ejecutado`: Confirmación de que el residente asistió al dispositivo.
3. `ausente`: Registro de inasistencia que libera la plaza.

### El Trigger de Capacitación en Servicio
Un pilar de eficiencia del sistema es el trigger `trg_cap_servicio_menu`:
- **Lógica**: Si un residente es asignado a un dispositivo para el cual no tiene registro previo de capacitación, y la columna `es_capacitacion_servicio` se marca como TRUE, el sistema crea/actualiza automáticamente su registro en `capacitaciones_participantes`.
- **Impacto**: Reduce la carga administrativa de acreditar formaciones que ocurren durante el desempeño real.

## 4. Mejores Prácticas Postgres Implementadas
- **Updates por Criterio Único**: Las mutaciones en Next.js se realizan cruzando `id_agente` + `fecha_asignacion` para garantizar atomicidad sin depender de IDs volátiles de sesión.
- **Normalización**: Separación clara entre el catálogo de personas y el historial de movimientos diarios.

### E. Tablas de Capacitaciones (Esquema Relacional)

| Tabla | Propósito |
|---|---|
| `capacitaciones` | Registro de sesiones de capacitación. FK a `dias` (para la fecha real). Columna `grupo` indica A/B. |
| `capacitaciones_participantes` | Relación M:N entre capacitaciones y agentes. Columna `asistio` (boolean). |
| `capacitaciones_dispositivos` | Relación M:N entre capacitaciones y dispositivos habilitados. |
| `dias` | Catálogo de fechas con `id_dia` → `fecha` (`YYYY-MM-DD`). |

### F. Vistas Materializadas

| Vista | Uso |
|---|---|
| `vista_historial_capacitaciones` | Consolidación de quién asistió a qué dispositivo y cuándo. Usada por el motor Python. |
| `vista_convocatoria_completa` | Convocatorias con fecha, agente, turno y tipo. Filtra descansos (`id_turno = 20`). |
| `cap_residentes` | Vista resumida de capacitaciones por residente (usada en diagnósticos). |

---
> [!TIP]
> **Próxima Etapa**: Fase 2 - El Cerebro (Lógica del Motor Python y heurísticas de asignación).

