# Guía de Despliegue: Convocatoria Sync

## Archivos Nuevos a Agregar

Has creado exitosamente los archivos base. Ahora necesitas agregar 3 archivos adicionales:

### 1. config_manager.gs

**Ubicación**: Archivo de comandos → `config_manager`

**Función**: Gestión de filtros globales (año_activo, cohorte_activa)

**Características**:
- Crea hoja CONFIG automáticamente
- `getActiveFilters()` — Lee filtros del usuario
- `configurarFiltros()` — UI para establecer año/cohorte
- `mostrarFiltrosActivos()` — Muestra configuración actual

### 2. sync_convocatoria.gs

**Ubicación**: Archivo de comandos → `sync_convocatoria`

**Función**: Sincronización de convocatoria con triple lookup

**Características**:
- **Triple FK Resolution**:
  - Agente: busca por DNI o nombre completo
  - Fecha → id_dia (desde REF_DIAS)
  - Tipo turno → id_turno (desde REF_TURNOS)
- **Validación de Integridad**: verifica que (id_dia, id_turno) exista en planificacion
- **Error Feedback**: mensaje específico según tipo de error

### 3. menu_updates.gs

**Ubicación**: Archivo de comandos → `menu_updates`

**Función**: Menú actualizado con configuración y convocatoria

**IMPORTANTE**: Debes REEMPLAZAR la función `onOpen()` en Code.gs con `onOpenV2()` de menu_updates.gs, O renombrar onOpenV2 → onOpen.

---

## Menú Actualizado

```
🔌 Supabase
├── 🧪 Test Conexión
├── ⚙️ Configuración
│   ├── Ver Filtros Activos
│   └── Configurar Filtros
├── 📥 Descargar Datos
│   ├── Datos Personales
│   ├── Turnos
│   └── Días (calendario)
├── 📤 Sincronizar a Supabase
│   ├── Datos Personales
│   ├── Planificación
│   └── Convocatoria  ← NUEVO
└── 🧹 Limpiar Status
```

---

## Estructura de Hoja CONVOCATORIA

| agente | fecha | tipo_turno | estado | motivo_cambio | sync_status |
|--------|-------|------------|--------|---------------|-------------|
| Pérez Juan (DNI: 12345678) | 2026-02-01 | mañana | vigente | | |
| 23456789 | 2026-02-02 | tarde | vigente | | |

**Agente**: Puede ser DNI solo o nombre completo  
**Fecha**: YYYY-MM-DD (debe existir en tabla dias)  
**Tipo turno**: mañana, tarde, intermedio, etc. (de REF_TURNOS)

---

## Validaciones Implementadas

1. ✅ **Agente existe** (por DNI o nombre)
2. ✅ **Fecha existe** en tabla dias
3. ✅ **Tipo turno existe** en tabla turnos
4. ✅ **Turno planificado** — El par (fecha, tipo_turno) debe existir en planificacion

Si falla cualquiera, se marca error en `sync_status` con mensaje descriptivo.

---

## Flujo de Uso

### Primera Vez

1. **Configurar filtros** (opcional):
   - Menú → ⚙️ Configuración → Configurar Filtros
   - Establecer año (ej: 2026) y cohorte (ej: 2025)

2. **Descargar referencias**:
   - 📥 Descargar Datos → Datos Personales
   - 📥 Descargar Datos → Turnos
   - 📥 Descargar Datos → Días

3. **Crear hoja CONVOCATORIA** con estructura de arriba

4. **Llenar datos** y ejecutar:
   - 📤 Sincronizar a Supabase → Convocatoria

### Mensajes de Status

| Status | Significado |
|--------|-------------|
| `✅ OK 26/1/2026` | Sincronizado correctamente |
| `❌ Agente no encontrado` | DNI/nombre no existe en tabla datos_personales |
| `❌ Fecha no encontrada` | Fecha no existe en tabla dias |
| `❌ Tipo turno no encontrado` | Tipo turno no existe en tabla turnos |
| `❌ Turno no planificado para 2026-02-01` | No hay planificación para esa fecha/turno |

---

## Optimización con CONFIG

La hoja CONFIG permite filtrar descargas para evitar traer TODO el histórico:

**Sin filtros**: Descarga TODOS los agentes históricos (puede ser lento)

**Con filtros**:
- `año_activo = 2026` → Solo planificaciones/convocatorias de 2026
- `cohorte_activa = 2025` → Solo agentes de cohorte 2025

Dejar vacío = sin filtro.
