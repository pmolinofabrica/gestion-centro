# Fase 3: La Piel - Frontend, UX y Flujos de Interacción (Next.js)

Documentación exhaustiva de la interfaz. Cada componente, botón, color y acción esperada.

## 1. Arquitectura de Navegación (3 Tabs)

### A. Matriz de Planificación (`plan`)
- **Propósito**: Vista macro mensual (Dispositivos × Fechas).
- **Tabla principal**: Grilla scrolleable. Columna izquierda = Dispositivos con piso y rango (ej: `(P1) FÁBRICA DE LENGUAJES - Rango: 1-1`). Columnas = Fechas activas.
- **Headers de fecha**: Muestran badges `LIBR.` (residentes libres) y `VAC.` (cupos vacíos en dispositivos).
- **Celdas**: Contienen tarjetas de residentes con color de score. Click en celda abre sidebar de dispositivo; click en tarjeta abre sidebar de residente.
- **Botón "Ver Vacantes / Sin Asignar"**: Esquina superior derecha, abre sidebar izquierdo con residentes convocados sin mesa.

### B. Apertura / Inasistencias (`exec`)
- **Propósito**: Operación diaria. Kanban de dispositivos activos + pool de sin asignar.
- **Selector de fecha**: Dropdown con las fechas activas del mes.
- **Botón "Menú"**: Abre panel lateral de dispositivos (habilitar/deshabilitar, ver asignados, botón "Cerrar y Bajar").
- **Tarjeta P0 "Sin Asignar"**: Background amarillo. Muestra residentes convocados sin dispositivo con capacitaciones resumidas por piso.
- **Tarjetas de Dispositivo**: Background blanco con header coloreado por piso. Cada residente tiene botón "Quitar" y "Cambiar Residente".
- **Botón "Buscar en Descansos"**: Pie de la tarjeta P0. Abre modal con residentes en descanso (dinámico desde DB).

### C. Dispositivos (`devices`)
- **Propósito**: Configuración mensual de cupos.
- **Tabla editable**: Inputs numéricos por dispositivo × fecha.
- **Botones rápidos**: "Mes (1)" y "Mes (0)" para rellenar toda la fila.
- **Footer sticky**: Totales de Convocados, Dispositivos Abiertos, Métricas de Vacancia (👤 y 🧩).
- **Barra de métricas superior**: Cards scrolleables con resumen por fecha (Convocados, Disp. Abiertos, Libres, Vacantes).

---

## 2. Sistema de Diseño (Paleta y Tokens)

### Colores por Piso
| Piso | Background | Text | Border | Uso |
|---|---|---|---|---|
| P1 | `bg-cyan-50` | `text-cyan-800` | `border-cyan-200` | Headers, badges, sidebar |
| P2 | `bg-rose-50` | `text-rose-800` | `border-rose-200` | Headers, badges, sidebar |
| P3 | `bg-amber-50` | `text-amber-800` | `border-amber-200` | Headers, badges, sidebar |
| Neutro | `bg-slate-50` | `text-slate-800` | `border-slate-200` | Dispositivos sin piso, inactivos |

### Score Colors (Tarjetas de Residente en Matriz)
| Rango | Clase | Significado |
|---|---|---|
| ≥ 900 | `bg-emerald-100 text-emerald-800` | Alta rotación, bien distribuido |
| ≥ 600 | `bg-amber-100 text-amber-800` | Rotación aceptable |
| < 600 | `bg-rose-100 text-rose-800` | Alta repetición, necesita ajuste |

### Subrayado de Grupo A/B
- **Grupo A**: `border-b-2 border-indigo-400` + `text-indigo-900`
- **Grupo B**: `border-b-2 border-rose-400` + `text-rose-900`

---

## 3. Sidebars y Modales (Detalle de Acciones)

### 3.1 Sidebar de Reemplazo (Derecha) — Click en Residente
| Zona | Contenido |
|---|---|
| Header | Nombre del residente, dispositivo actual, fecha. Color de piso. Botón **Quitar** (rojo). |
| Score | Breakdown visual: Base 1000 − Penalidad = Score actual. |
| Tier 1 | **Capacitados y Convocados**: Background verde. Click → ejecuta swap inmediato. |
| Tier 2 | **No Capacitados y Convocados**: Background ámbar. Swap de emergencia. |
| Tier 3 | **Capacitados en Descanso**: Background rosa. |
| Tier 4 | **No Capacitados y Descanso**: Background gris. Último recurso. |

**Acción de cada botón de Tier**: Ejecuta `handleSwapResident(id)` → UPDATE en `menu` → reload.

### 3.2 Sidebar de Vacantes (Izquierda) — Botón "Ver Vacantes"
- Lista agrupada por fecha: "X sueltos" por día.
- Cada residente muestra badges de capacitaciones por piso (P1: X Disp., P2: X Disp.).
- Click en residente → abre **Sidebar de Ubicación de Vacante** (derecha).

### 3.3 Sidebar de Ubicación de Vacante (Derecha) — Click en Vacante
| Zona | Contenido |
|---|---|
| Header | Nombre del vacante, fecha. Background indigo. |
| Tier 1 | Dispositivos donde **está capacitado**: Coloreados por piso. Muestra ocupación actual vs cupo. |
| Tier 2 | Dispositivos donde **no está capacitado**: Background gris neutro. |

**Acción**: Click en dispositivo → `handleAssignVacant(deviceId)` → UPDATE o INSERT → reload.

### 3.4 Panel de Dispositivos (Derecha, en Apertura) — Botón "Menú"
- Lista todos los dispositivos del catálogo.
- **Operativos**: Header coloreado por piso. Lista residentes asignados con botón "Cerrar y Bajar" (elimina la asignación).
- **Inactivos**: Gris. Click → expande dropdown de residentes sin asignar para habilitar manualmente con "Abrir +".

### 3.5 Modal "Plantilla en Descanso" — Botón "Buscar en Descansos"
- **Dinámico**: Consulta `allResidentsDb` filtrando los que NO están en `convocadosDb[fecha]`.
- Muestra hasta 3 capacitaciones por residente.
- Botón "Llamar y Asignar" → ejecuta `handleAssignFromPool(apellido)`.

### 3.6 Sidebar de Dispositivo (Derecha, en Planificación) — Click en Dispositivo
- Header coloreado por piso con nombre y tip de uso.
- Si se selecciona fecha: filtra y muestra solo convocados de ese día con badge 🟢 CONVOCADO o 🟠 DESCANSO.
- Ordenamiento inteligente: Capacitados+Convocados primero, No capacitados al final.

---

## 4. Botones del Header (Global)

| Botón | Ubicación | Acción |
|---|---|---|
| **Selector de Mes** | Izquierda | Dropdown: Febrero/Marzo/Abril 2026 |
| **Bóveda Amancio Williams** | Derecha | Placeholder. SVG de 4 paraboloides interconectados. Aura dorada (`shadow-[0_0_15px_rgba(251,191,36,0.4)]`). Alert informativo al click. |
| **Deshacer (N)** | Derecha | `handleUndoLastAction()`. Muestra contador de acciones pendientes. Deshabilitado si N=0. |
| **🔮 Generar** | Derecha | `handleRunAI()` → POST a `/api/run-engine` → ejecuta Python (`undo_menu_marzo.py` + `motor_asignaciones_supabase.py`) → reload. |

---

## 5. API Route: `/api/run-engine` (`route.ts`)

| Paso | Script | Propósito |
|---|---|---|
| 1 | `undo_menu_marzo.py {startDate}` | Limpia asignaciones desde la fecha hacia adelante |
| 2 | `motor_asignaciones_supabase.py --start-date {startDate}` | Regenera asignaciones con el motor de scoring |

> [!CAUTION]
> Este endpoint ejecuta `child_process.exec()` con rutas absolutas hardcodeadas (`/home/pablo/...`). No es portable a producción sin parametrizar.

---

## 6. Estado Global (React useState)

| Variable | Tipo | Propósito |
|---|---|---|
| `activeTab` | `'plan' \| 'exec' \| 'devices'` | Tab activo |
| `dbDevices` | `Array` | Catálogo de dispositivos (desde Supabase, fallback a mock) |
| `dbResidents` | `Array` | Padrón de residentes activos (cohorte 2026) |
| `allResidentsDb` | `Array` | Residentes con mapa de capacitaciones |
| `assignmentsDb` | `Record<fecha, Record<dispositivo, Array>>` | Matriz de asignaciones |
| `calendarDb` | `Record<fecha, Record<dispositivo, cupo>>` | Cupos habilitados por día |
| `convocadosCountDb` | `Record<fecha, number>` | Total convocados por fecha |
| `convocadosDb` | `Record<fecha, number[]>` | IDs de convocados por fecha |
| `agentGroups` | `Record<id, 'A' \| 'B'>` | Grupo de cada residente |
| `undoStack` | `Array<UndoEntry>` | Pila de acciones deshacibles |
| `selectedResident` | `Object \| null` | Residente seleccionado para sidebar |
| `selectedDevice` | `Object \| null` | Dispositivo seleccionado para sidebar |
| `selectedVacant` | `Object \| null` | Vacante seleccionado para sidebar de ubicación |

---

## 7. UndoStack: Estructura de Entradas

```typescript
type UndoEntry = {
  fecha_asignacion: string;          // YYYY-MM-DD
  old_id_agente: number;             // ID del residente original
  old_id_dispositivo: string|number; // ID del dispositivo original
  id_asignacion?: number;            // Solo para AssignVacant (Ruta A de undo)
  action_type?: string;              // 'swap' | 'quitar_inline' (informativo)
}
```

El handler `handleUndoLastAction` decide la ruta de reversión:
- **Ruta A** (tiene `id_asignacion`): Filtra por PK directa.
- **Ruta B** (sin `id_asignacion`): Filtra por `id_agente` + `fecha_asignacion`.

> [!NOTE]
> El `undoStack` vive en memoria (React state). Se pierde al recargar la página. No persiste entre sesiones.
