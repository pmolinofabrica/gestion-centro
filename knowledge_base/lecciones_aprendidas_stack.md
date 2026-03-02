# Lecciones Aprendidas y Gotchas

Esta nota recopila los conocimientos clave adquiridos durante el desarrollo del sistema de gestión del Centro Cultural. Sirve como referencia rápida para evitar errores comunes y documentar decisiones de diseño de manera viva.

## 1. Google Apps Script (Frontend)
- **Uso exclusivo de `db_helpers.gs`**: NUNCA realizar llamadas `UrlFetchApp` directas en funciones de negocio. 
  - **Solución**: Utilizar siempre `fetchAll`, `insertRow`, `upsertRecord`, o `callRpc` de `scripts/google_apps/db_helpers.gs`. Estas funciones ya manejan la autenticación y paginación.
- **Aplanar datos (Flattening)**: Al traer datos de tablas relacionadas (JOINs), Supabase devuelve objetos anidados (ej: `tabla_b: { campo: val }`). 
  - **Solución**: "Aplanar" esta estructura en JavaScript antes de pintarla en la hoja de cálculo (tomar como ejemplo la función `loadDatosPersonales`).

## 2. Supabase y Base de Datos (Backend)
- **Permisos y RLS (Row Level Security)**:
  - Si creas una tabla nueva, **NO OLVIDES** habilitar RLS y crear las políticas (Policies) correspondientes (`GRANT ALL ... TO anon, authenticated`).
  - *Contexto de claves*: El Frontend usa claves limitadas (anon/authenticated), mientras que el backend y las migraciones en Python usan la `service_role_key` (acceso total).
  - *Síntoma de error*: Error `403` o `404` al intentar insertar/leer desde Google Apps Script.
  - *Fix de referencia*: Revisar `sql/queries/fix_permissions_adicionales.sql`.

## 3. Scripts de Migración (Python)
- **Plantilla base de migración**: Usar siempre `migrate_2026.py` (ubicado en `scripts/python/`) como punto de partida.
  - Resuelve la conexión a la bd leyendo desde `config/supabase.json`.
  - Cuenta con manejo de errores por lotes.
  - Asegura la corrección de URLs (reemplazando `db.` por `project.`).
- **Calidad de datos (Data Governance)**: Recordar siempre validar y limpiar los datos antes de enviarlos a Supabase (ej: truncar teléfonos largos, unificar formatos de fechas, etc.) previo a la inserción masiva.

---
*Tags:* #lecciones-aprendidas #supabase #gas #python #buenas-practicas #troubleshooting
