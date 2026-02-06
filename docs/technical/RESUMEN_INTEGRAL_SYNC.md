# Actualización Integral de Funcionalidad

He implementado todas las funciones de sincronización que solicitaste.

## 🚀 Nuevas Capacidades

### 1. **Feriados y Días** (Bidireccional)
- **Editar**: `📥 Descargar Datos > ✏️ Feriados (editable)`
- **Sincronizar**: `📤 Sincronizar > 📅 Feriados`
- **Archivo:** `sync_dias_feriados.gs`

### 2. **Planificación** (Bidireccional)
- **Editar**: Ahora puedes agregar filas en la hoja `PLANIFICACION`
- **Lógica**: Busca automáticamente el `id_dia` usando la fecha y `id_turno` usando el tipo (ej: "mañana").
- **Archivo:** `sync_planificacion.gs`

### 3. **Convocatoria** (Turno Cancelado)
- **Lógica**: Soporta la nueva columna `turno_cancelado`.
- **Valores aceptados**: "Sí", "TRUE", o checkbox activado.
- **Archivo:** `sync_convocatoria.gs` (Actualizado)

---

## 🛠️ Instrucciones de Actualización

Copia el contenido de los siguientes archivos a tu Editor de Apps Script:

1.  [`sync_convocatoria.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_convocatoria.gs) (Actualizado)
2.  [`sync_planificacion.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_planificacion.gs) (Nuevo)
3.  [`sync_dias_feriados.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_dias_feriados.gs) (Nuevo/Verificar)
4.  [`menu_updates.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/menu_updates.gs) (Verificar que tenga todas las opciones)

Después de guardar, refresca tu hoja de cálculo y verás todas las nuevas opciones en el menú.
