# 🤖 Guía de Traspaso para IAs (Handover Guide)

Si eres una Inteligencia Artificial que ha sido traída para continuar este proyecto, lee atentamente estos puntos clave. Este proyecto tiene una arquitectura "DAMA-Centric" donde la integridad de la base de datos es la prioridad máxima.

## 🧠 Contexto Técnico Crítico

1. **La Llave Maestra (`id_agente`)**: Nunca uses el `id_usuario` (UUID de Auth) para lógica de negocio. Usa siempre el `id_agente` (Numérico), que es la PK en `datos_personales`.
2. **Formato de Fechas**: La base de datos espera `YYYY-MM-DD`. El frontend suele transformar a `DD/MM` para visualización, pero cualquier mutación (`UPDATE`/`DELETE`) debe re-formatearse a la norma ISO.
3. **El Motor de Asignación**: No intentes reescribir la lógica de asignación en JS. El motor en Python es el único que debe hacer inserciones masivas en la tabla `menu`. Existen dos versiones: `motor_asignacion_apertura5.py` (planificación) y `motor_asignaciones_supabase.py` (escritura directa).
4. **Capacitación Automática**: Existe un trigger en Postgres (`trg_cap_servicio_menu`) que acredita capacitaciones automáticamente al marcar `asistio`.
5. **Modos de Rotación (`menu_semana`)**: Se ha introducido la tabla `menu_semana` para manejar "Rotación Simple" y "Rotación Completa". En estos modos, las validaciones de "ocupado" se relajan para permitir múltiples asignaciones por residente. Siempre consulta `orgTypes` para determinar si aplicar candados.
6. **Gestión de Grupos (`numero_grupo`)**: En "Rotación Completa", los residentes se organizan por grupos (1, 2, 3). Existe una lógica de **Propagación** (al asignar por primera vez) y **Herencia** (al mover desde vacantes) para mantener la consistencia del grupo en todos los pisos asignados.

## 🎨 Principios de UX (Estética Williams)
El usuario valora la limpieza visual y el simbolismo.
- Mantén la paleta por pisos: **P1 (Cyan), P2 (Rose), P3 (Amber)**.
- El botón de la "Bóveda Amancio Williams" es un elemento identitario sagrado del proyecto. No lo elimines ni cambies su estilo sin consultar; representa el vínculo con el edificio real.

## 🛠️ Flujo de Trabajo Recomendado
1. **Validar en DB**: Antes de cambiar el frontend, verifica el estado de las tablas en Supabase.
2. **Identificación Unívoca**: Evita búsquedas por `name` o `apellido`. Usa siempre el `id_agente` numérico para filtrado en queries de Supabase y estados de React.
3. **Uso de UndoStack**: El stack soporta snapshots compuestos (array de objetos) para desacer Swaps o movimientos complejos.
4. **`route.ts` es crítico**: Endpoint `/api/run-engine` ejecuta Python. Si cambias de entorno, verifica rutas absolutas.
5. **Categorización por Tiers**: El estándar visual para sidebars (Padrón/Menú Ejecución) es dividir por: 
   - Tier 1: Convocado & Capacitado (Esmeralda)
   - Tier 2: Convocado NO Capacitado (Ámbar)
   - Tier 3/4: Descanso (Gris)
   - Tier Inasistencia: (Rosa/Bloqueado)
6. **Cerrar y Bajar**: No borres registros. Mueve a `id_dispositivo: 999` (Vacantes) para mantener la trazabilidad de la convocatoria.
5. **Datos Mock**: Existen constantes mock (`ALL_RESIDENTS_DB`, `CALL_STATUS_DB`, `MOCK_DEVICES_BACKUP`) en `page.tsx` que sirven como fallback. No las elimines sin antes asegurar que la DB responde siempre.

---
*Buen viaje, colega. Que el código sea contigo.* 🖖
