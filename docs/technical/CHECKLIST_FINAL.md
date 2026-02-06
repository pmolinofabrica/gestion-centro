# Checklist de Despliegue Final

## ✅ Archivos a Copiar en GAS

En [script.google.com](https://script.google.com), abre tu proyecto y agrega estos archivos:

### Archivos Existentes (ya deberías tenerlos)
1. ✅ `Code.gs` — **ACTUALIZAR** con versión que tiene `onOpen_old()`
2. ✅ `config.gs` — Sin cambios
3. ✅ `sync.gs` — Sin cambios
4. ✅ `utils.gs` — Sin cambios

### Archivos Nuevos (agregar ahora)
5. ⭐ **`menu_updates.gs`** — Menú con `onOpen()` activa
6. ⭐ **`config_manager.gs`** — Sistema CONFIG
7. ⭐ **`sync_convocatoria.gs`** — Sync de convocatoria

---

## Pasos de Despliegue

### 1. Actualizar Code.gs
```
1. Abrir Code.gs en GAS
2. Reemplazar TODO el contenido con el archivo actualizado
   (que ahora tiene onOpen_old en vez de onOpen)
```

### 2. Agregar Archivos Nuevos
Para cada archivo nuevo:
```
1. En GAS: + → Archivo de comandos
2. Nombre del archivo (sin .gs):
   - menu_updates
   - config_manager
   - sync_convocatoria
3. Pegar contenido correspondiente
```

### 3. Guardar Proyecto
```
Ctrl+S o Archivo → Guardar
```

### 4. Verificar en Google Sheets
```
1. Cerrar y reabrir tu hoja de cálculo
2. Deberías ver menú actualizado:
   🔌 Supabase
   ├── 🧪 Test Conexión
   ├── ⚙️ Configuración
   ├── 📥 Descargar Datos
   ├── 📤 Sincronizar a Supabase
   ├── 🧮 Cálculos Automáticos
   ├── 📊 Actualizar Dashboard  ← NUEVO
   └── 🧹 Limpiar Status
```

### 5. Configurar Filtros (Opcional)
```
Menú → ⚙️ Configuración → Configurar Filtros
- Año activo: 2026
- Cohorte activa: (dejar vacío o poner año)
```

### 6. Crear Hoja CONVOCATORIA
```
Estructura mínima:
| agente | fecha | tipo_turno | estado | sync_status |
|--------|-------|------------|--------|-------------|
```

### 7. Probar Sincronización
```
1. Descargar referencias:
   📥 → Datos Personales
   📥 → Turnos
   📥 → Días
   
2. Llenar CONVOCATORIA con datos de prueba
3. Ejecutar: 📤 → Convocatoria
4. Verificar columna sync_status
```

---

## Validaciones que Verás

| Status | Causa |
|--------|-------|
| ✅ OK 26/1/2026 | Sincronizado correctamente |
| ❌ Agente no encontrado | DNI/nombre no existe |
| ❌ Fecha no encontrada | Fecha no existe en tabla dias |
| ❌ Tipo turno no encontrado | Tipo turno no configurado |
| ❌ Turno no planificado para... | No hay planificación para esa fecha/turno |

---

## Resumen de Archivos GAS

Total: **7 archivos**

| # | Archivo | Líneas | Función |
|---|---------|--------|---------|
| 1 | Code.gs | ~260 | Conexión, descarga, `onOpen_old()` |
| 2 | config.gs | ~213 | Validación DAMA |
| 3 | sync.gs | ~315 | Sync datos_personales, planificacion |
| 4 | utils.gs | ~33 | Utilidades |
| 5 | **menu_updates.gs** | ~80 | **Menú activo `onOpen()`** ⭐ |
| 6 | **config_manager.gs** | ~140 | **Sistema CONFIG filtros** ⭐ |
| 7 | **sync_convocatoria.gs** | ~230 | **Triple lookup convocatoria** ⭐ |
| 8 | **sync_saldos.gs** | ~330 | **Sync Saldos + Cálculo** ⭐ |
| 9 | **dashboard.gs** | ~200 | **Visualización KPIs** ⭐ |

**Total código**: ~1,800 líneas + docs

---

## Si Hay Problemas

### Error: "Cannot find function onOpen"
→ Verifica que `menu_updates.gs` tenga función `onOpen()` (no onOpenV2)

### Error: "Duplicate function onOpen"
→ Verifica que Code.gs tenga `onOpen_old()` (no onOpen)

### Menú no aparece
→ Cierra y abre la hoja de nuevo. O ejecuta manualmente `onOpen()` desde editor GAS

### "Agente no encontrado" siempre
→ Descarga primero REF_PERSONAL con 📥 Descargar Datos
