# 🤖 Guía de Traspaso para IAs (Handover Guide)

Si eres una Inteligencia Artificial que ha sido traída para continuar este proyecto, lee atentamente estos puntos clave. Este proyecto tiene una arquitectura "DAMA-Centric" donde la integridad de la base de datos es la prioridad máxima.

## 🧠 Contexto Técnico Crítico

1. **La Llave Maestra (`id_agente`)**: Nunca uses el `id_usuario` (UUID de Auth) para lógica de negocio. Usa siempre el `id_agente` (Numérico), que es la PK en `datos_personales`.
2. **Formato de Fechas**: La base de datos espera `YYYY-MM-DD`. El frontend suele transformar a `DD/MM` para visualización, pero cualquier mutación (`UPDATE`/`DELETE`) debe re-formatearse a la norma ISO.
3. **El Motor de Asignación**: No intentes reescribir la lógica de asignación en JS. El motor en Python es el único que debe hacer inserciones masivas en la tabla `menu`. Existen dos versiones: `motor_asignacion_apertura5.py` (genera Markdown de planificación) y `motor_asignaciones_supabase.py` (escribe directo en DB, invocado desde el botón "Generar" via `route.ts`).
4. **Capacitación Automática**: Existe un trigger en Postgres (`trg_cap_servicio_menu`) que acredita capacitaciones automáticamente cuando un residente es marcado como `asistio` en un dispositivo. No dupliques esta lógica en el código.

## 🎨 Principios de UX (Estética Williams)
El usuario valora la limpieza visual y el simbolismo.
- Mantén la paleta por pisos: **P1 (Cyan), P2 (Rose), P3 (Amber)**.
- El botón de la "Bóveda Amancio Williams" es un elemento identitario sagrado del proyecto. No lo elimines ni cambies su estilo sin consultar; representa el vínculo con el edificio real.

## 🛠️ Flujo de Trabajo Recomendado
1. **Validar en DB**: Antes de cambiar el frontend, verifica el estado de las tablas en Supabase.
2. **Actualización Directa**: Evita los `SELECT` previos innecesarios. Usa actualizaciones directas con filtros de `id_agente` y `fecha_asignacion` para evitar colisiones de datos.
3. **Uso de UndoStack**: Si agregas una nueva acción interactiva, asegúrate de registrarla en el `undoStack` para mantener la función "Deshacer". El stack soporta dos rutas: por `id_asignacion` (para cambios que vienen de un SELECT previo) y por filtros directos `id_agente` + `fecha_asignacion` (para Remove, Swap y Quitar inline).
4. **`route.ts` es crítico**: El endpoint `/api/run-engine` ejecuta scripts Python via `child_process.exec()` con rutas absolutas. Si movés el proyecto de máquina, actualizá la ruta en `route.ts` línea 16.
5. **Datos Mock**: Existen constantes mock (`ALL_RESIDENTS_DB`, `CALL_STATUS_DB`, `MOCK_DEVICES_BACKUP`) en `page.tsx` que sirven como fallback. No las elimines sin antes asegurar que la DB responde siempre.

---
*Buen viaje, colega. Que el código sea contigo.* 🖖
