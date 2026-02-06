# Guía de Implementación: Sincronización Bidireccional TURNOS y FERIADOS

## 📦 Archivos Nuevos Creados

1. **`sync_turnos.gs`** (~180 líneas) - Gestión completa de turnos
2. **`sync_dias_feriados.gs`** (~160 líneas) - Gestión de feriados
3. **`download_data.gs`** (~120 líneas) - Descarga de planificación y convocatoria

Total: **3 archivos nuevos + 1 actualizado** (`menu_updates.gs`)

---

## 🚀 Pasos de Despliegue

### 1. Copiar Archivos Nuevos

En tu proyecto de Google Apps Script:

**Crear archivo:** `sync_turnos.gs`
- Copiar contenido desde: [`admin_tools/gas_scripts/sync_turnos.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_turnos.gs)

**Crear archivo:** `sync_dias_feriados.gs`
- Copiar contenido desde: [`admin_tools/gas_scripts/sync_dias_feriados.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_dias_feriados.gs)

**Crear archivo:** `download_data.gs`
- Copiar contenido desde: [`admin_tools/gas_scripts/download_data.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/download_data.gs)

### 2. Actualizar Archivo Existente

**Reemplazar:** `menu_updates.gs`
- Con contenido de: [`admin_tools/gas_scripts/menu_updates.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/menu_updates.gs)

---

## 🎯 Nuevas Funcionalidades

### **TURNOS** (Bidireccional)

**Descargar turnos editables:**
1. Menú: `📥 Descargar Datos` → `✏️ Turnos (editable)`
2. Se crea hoja `TURNOS` con checkboxes en columnas booleanas
3. Columnas: `id_turno, tipo_turno, descripcion, hora_inicio_default, hora_fin_default, cant_horas_default, solo_fines_semana, solo_semana, activo`

**Editar turnos:**
- Modifica valores en hoja `TURNOS`
- Marca/desmarca checkboxes
- Agrega nuevas filas (sin `id_turno`)

**Sincronizar:**
- Menú: `📤 Sincronizar a Supabase` → `🕐 Turnos`
- UPSERT por `tipo_turno` (unique key)
- Validación DAMA automática

---

### **FERIADOS** (Bidireccional)

**Descargar para editar:**
1. Menú: `📥 Descargar Datos` → `✏️ Feriados (editable)`
2. Se crea hoja `DIAS_FERIADOS` con **todos** los días
3. Columnas: `id_dia, fecha, es_feriado (checkbox), descripcion_feriado`

**Marcar/desmarcar feriados:**
- Checkbox en columna `es_feriado`
- Escribir descripción en `descripcion_feriado`

**Sincronizar:**
- Menú: `📤 Sincronizar a Supabase` → `📅 Feriados`
- Solo actualiza campos `es_feriado` y `descripcion_feriado`
- No puede agregar/eliminar días (master data)

---

### **VER PLANIFICACION y CONVOCATORIA**

**Planificación:**
- Menú: `📥 Descargar Datos` → `📊 Planificación`
- Muestra planificaciones con lookups inversos:
  - `id_dia` → `fecha`
  - `id_turno` → `tipo_turno`
- Respeta filtro CONFIG (`año_activo`)

**Convocatoria:**
- Menú: `📥 Descargar Datos` → `👥 Convocatoria`
- Muestra convocatorias human-readable:
  - `id_agente` → `Apellido, Nombre`
  - `id_turno` → `tipo_turno`
- Filtrado por año

---

## 📋 Estructura de Hojas

| Hoja | Propósito | Editable | Sincronizable |
|------|-----------|----------|---------------|
| `REF_PERSONAL` | Caché agentes | ❌ No | ❌ No |
| `REF_TURNOS` | Caché turnos | ❌ No | ❌ No |
| `REF_DIAS` | Caché calendario | ❌ No | ❌ No |
| `TURNOS` | Gestión turnos | ✅ Sí | ✅ Sí |
| `DIAS_FERIADOS` | Gestión feriados | ✅ Sí | ✅ Sí |
| `DATOS_PERSONALES` | Gestión agentes | ✅ Sí | ✅ Sí |
| `PLANIFICACION` | Ver/editar plani | ✅ Sí | ✅ Sí |
| `CONVOCATORIA` | Ver/editar conv | ✅ Sí | ✅ Sí |
| `SALDOS` | Ver/editar saldos | ✅ Sí | ✅ Sí |

---

## ✅ Verificación Post-Despliegue

1. Refresca tu Hoja de Cálculo (F5)
2. Abre menú `🔌 Supabase`
3. Verifica que existan:
   - `📥 Descargar Datos` → `✏️ Turnos (editable)`
   - `📥 Descargar Datos` → `✏️ Feriados (editable)`
   - `📥 Descargar Datos` → `📊 Planificación`
   - `📥 Descargar Datos` → `👥 Convocatoria`
   - `📤 Sincronizar a Supabase` → `🕐 Turnos`
   - `📤 Sincronizar a Supabase` → `📅 Feriados`

4. Prueba descargando turnos: debería crear hoja con checkboxes

---

## 🎉 Resumen

**Ahora puedes:**
- ✅ Gestionar turnos completamente desde Sheets
- ✅ Marcar/desmarcar feriados visualmente
- ✅ Ver planificación y convocatoria existentes
- ✅ Todo con validación DAMA y feedback visual
