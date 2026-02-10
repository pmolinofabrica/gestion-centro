# Google Apps Script - Organización de Archivos

Este directorio contiene los scripts de Google Apps Script (GAS) para tres hojas de cálculo distintas del proyecto de Gestión RRHH.

## Hojas de Cálculo y sus Archivos

### 📊 Hoja "carga 2026" (Principal)

Gestión de planificación, convocatoria, inasistencias y sincronización con Supabase.

| Archivo | Descripción |
|---------|-------------|
| `Code.gs` | Configuración Supabase, funciones base CRUD |
| `config.gs` | Metadata de tablas (tipos, validaciones DAMA) |
| `config_manager.gs` | Gestión de filtros (año/cohorte) |
| `menu_updates.gs` | Menú principal "🔌 Supabase" |
| `sync.gs` | Funciones core de upsert |
| `sync_planificacion.gs` | Sync Planificación → Supabase |
| `sync_convocatoria.gs` | Sync Convocatoria → Supabase |
| `sync_inasistencias.gs` | Sync Inasistencias → Supabase |
| `sync_certificados.gs` | Sync Certificados → Supabase |
| `sync_turnos.gs` | Sync Turnos → Supabase |
| `sync_dias_feriados.gs` | Sync Días/Feriados → Supabase |
| `sync_saldos.gs` | Cálculo y sync de Saldos |
| `download_data.gs` | Descarga de datos completos |
| `download_optimized.gs` | Descargas optimizadas (vistas) |
| `download_inasistencias.gs` | Descarga de inasistencias |
| `download_certificados.gs` | Descarga de certificados |
| `cache_manager.gs` | Gestión de caché local |
| `dashboard.gs` | Funciones de dashboard |
| `utils.gs` | Utilidades (loadDias, clearStatus) |
| `check_connectivity.gs` | Test de conexión |
| `debug_views.gs` | Debug de vistas |

---

### 🏠 Hoja "menu 2026" (Asignaciones)

Gestión de asignaciones de residentes a dispositivos.

| Archivo | Descripción |
|---------|-------------|
| `config_assignment.gs` | Configuración específica de asignaciones |
| `db_helpers.gs` | Helpers de conexión a Supabase |
| `asignacion.gs` | Lógica de asignación de residentes |
| `menu_assignment.gs` | Menú "🏠 Asignaciones" |

---

### 🎓 Hoja "capacitaciones 2026"

Gestión de capacitaciones y certificaciones.

| Archivo | Descripción |
|---------|-------------|
| `db_helpers.gs` | Helpers de conexión (compartido) |
| `Capacitaciones.gs` | Lógica de capacitaciones |
| `SidebarAsignacion.html` | UI sidebar para asignación |

---

## Notas Importantes

1. **`db_helpers.gs`** se usa en múltiples proyectos - al modificarlo, considerar impacto en todos.
2. Cada hoja de cálculo es un **proyecto GAS independiente** en la nube.
3. Los archivos locales son **copia de respaldo** - los cambios deben copiarse manualmente al editor de Apps Script.
4. Solo hay una función `onOpen()` por proyecto (definida en `menu_updates.gs` o `menu_assignment.gs`).
