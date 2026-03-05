# Proyecto: Administrador de Inasistencias (CRUD App)

## Meta
Construir una aplicación o módulo independiente (pero vinculada al ecosistema de Gestión Centro) para administrar las Inasistencias del personal, adhiriéndose a principios de Master Data Management (DAMA).

## Problemática Actual
Actualmente, las inasistencias fluyen a través de `sync_inasistencias.gs` desde una planilla de Google Sheets.
- **Limitación DAMA:** Google Sheets maneja bien los inserts y updates (UPSERT mediante ID), pero **falla categóricamente en las eliminaciones (DELETE)**. Si un usuario borra localmente una fila, el script no detecta el evento de borrado y el registro persiste huérfano en la base de datos Supabase, pervirtiendo el estado real de disponibilidad.

## Solución Arquitectónica: Single Source of Truth UI
Desplazar todo el CRUD (Create, Read, Update, Delete) de Inasistencias hacia una interfaz React/Next.js consumiendo directamente de Supabase.

### Requisitos Funcionales
1. **Vista de Grilla (Read):** Tabla reactiva que traiga `SELECT * FROM inasistencias` (posiblemente con JOIN a `datos_personales` para traer nombres) paginada o filtrada por horizontes de tiempo (ej. mes actual).
2. **Formulario de Carga (Create):** Modal simple para dar de alta una inasistencia seleccionando Agente, Fecha, Motivo y Estado.
3. **Modal de Edición (Update):** Al tocar un registro, permitir modificar los campos no clave (motivo, observaciones, comprobantes).
4. **Acción de Borrado Seguro (Delete):** Botón con confirmación para ejecutar el `DELETE` definitivo sobre Supabase (limpiando el error de las asignaciones fantasmas).

Establecer Supabase como la única fuente interactiva terminará de desvincular el sistema de fragilidades generadas por el modelo de hojas de cálculo sincrónicas.
