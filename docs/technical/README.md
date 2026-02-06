# Google Apps Script - Admin Tools

Sistema de administración Low-Code para Gestión RRHH usando Google Sheets como interfaz y Supabase como backend.

## Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `Code.gs` | Conexión, test, y funciones de descarga |
| `config.gs` | Metadata de tablas y validación DAMA |
| `sync.gs` | Sincronización bidireccional Sheets ↔ Supabase |

---

## Instalación

### 1. Crear Proyecto GAS

1. Ir a [script.google.com](https://script.google.com)
2. Nuevo proyecto → Nombrar: "RRHH Admin"

### 2. Agregar Archivos

Copiar y pegar contenido de cada archivo `.gs`:
- Archivo → Crear archivo de comandos → Pegar `Code.gs`
- Repetir para `config.gs` y `sync.gs`

### 3. Configurar Credenciales

```
Configuración del proyecto (⚙️) → Propiedades de script → Agregar:

SUPABASE_URL = https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY = eyJhbG... (service_role key, NO anon)
```

> [!CAUTION]
> **Usar service_role key solo en entornos controlados**. Nunca compartir este script con usuarios externos.

### 4. Autorizar Permisos

Primera ejecución de `testConnection()`:
- Solicitará acceso a Google Sheets y servicios externos
- Revisar y autorizar

---

## Uso

### Menú Principal: 🔌 Supabase

Al abrir la hoja de cálculo aparecerá un menú personalizado:

#### 🧪 Test Conexión
Verifica conectividad con Supabase y muestra conteo de registros.

#### 📥 Descargar Datos
Descarga datos FROM Supabase TO hojas de referencia:
- **Datos Personales** → hoja `REF_PERSONAL`
- **Turnos** → hoja `REF_TURNOS`
- **Días** → hoja `REF_DIAS`

#### 📤 Sincronizar a Supabase
Sube datos FROM Sheets TO Supabase (con validación DAMA):
- **Datos Personales** → tabla `datos_personales`
- **Planificación** → tabla `planificacion`

> [!IMPORTANT]
> La sincronización usa **UPSERT** (insert o update). Registros con mismo `unique_key` se actualizan.

#### 🧹 Limpiar Status
Limpia la columna `sync_status` en todas las hojas.

---

## Validación DAMA

Antes de escribir en Supabase, cada registro pasa por validación:

✅ **Campos obligatorios** presentes  
✅ **Tipos de datos** correctos (int, float, date, bool)  
✅ **Valores permitidos** (ej: tipo_turno debe estar en lista)  
✅ **Foreign keys** resueltas (para planificación y convocatoria)

Si hay errores, se escriben en columna `sync_status` con ❌ y descripción.

---

## Estructura de Hojas Recomendada

### DATOS_PERSONALES
```
| nombre | apellido | dni      | cohorte | email           | sync_status |
|--------|----------|----------|---------|-----------------|-------------|
| Juan   | Pérez    | 12345678 | 2025    | juan@email.com  |             |
```

### PLANIFICACION
```
| fecha      | tipo_turno | cant_residentes_plan | sync_status |
|------------|------------|----------------------|-------------|
| 2026-02-01 | mañana     | 3                    |             |
```

> [!NOTE]
> Los campos `fecha` y `tipo_turno` se resuelven automáticamente a `id_dia` e `id_turno` antes de insertar.

---

## Solución de Problemas

### Error: "Faltan credenciales"
→ Revisar que `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` estén en Propiedades de script

### Error: "Tabla no configurada"
→ Verificar que el nombre de la tabla coincida con `TABLE_CONFIG` en `config.gs`

### Error: "Fecha no encontrada en tabla dias"
→ La fecha debe existir previamente en tabla `dias` de Supabase

---

## Próximas Funciones

- [ ] Sincronización de `convocatoria`
- [ ] Descarga con filtros (por cohorte, por año)
- [ ] Validación de dobles turnos
- [ ] Generación de reportes automáticos
