-- ============================================================================
-- MIGRACIÓN: asistencia → turno_cancelado
-- Ejecutar en orden: PASO 1 → PASO 2 → PASO 3
-- ============================================================================

-- ============================================================================
-- PASO 1: Recrear Vista SIN asistencia (usar estado = 'cumplida')
-- ============================================================================

-- Eliminar vista existente
DROP VIEW IF EXISTS vista_saldo_horas_live;

-- Recrear vista usando ESTADO en lugar de ASISTENCIA
-- NOTA: turno_cancelado aún no existe, se agrega en PASO 3
CREATE OR REPLACE VIEW vista_saldo_horas_live AS
SELECT 
    dp.id_agente,
    COALESCE(dp.apellido || ', ' || dp.nombre, dp.nombre, 'Sin Nombre') AS nombre_completo,
    dp.cohorte,
    (EXTRACT(DAY FROM (NOW() - c.fecha_inicio::timestamp)) / 7)::integer * c.horas_semanales_meta AS meta_teorica,
    (
        COALESCE(
            (SELECT COUNT(*) * 4 
             FROM convocatoria co
             WHERE co.id_agente = dp.id_agente 
               AND co.estado = 'cumplida'  -- CAMBIO: usa estado en lugar de asistencia
            ), 0
        )::numeric + 
        COALESCE(
            (SELECT SUM(ah.horas_delta) 
             FROM ajustes_horas ah
             WHERE ah.id_agente = dp.id_agente
            ), 0
        )
    ) AS horas_reales,
    (
        COALESCE(
            (SELECT COUNT(*) * 4 
             FROM convocatoria co
             WHERE co.id_agente = dp.id_agente 
               AND co.estado = 'cumplida'
            ), 0
        )::numeric + 
        COALESCE(
            (SELECT SUM(ah.horas_delta) 
             FROM ajustes_horas ah
             WHERE ah.id_agente = dp.id_agente
            ), 0
        ) - 
        ((EXTRACT(DAY FROM (NOW() - c.fecha_inicio::timestamp)) / 7)::integer * c.horas_semanales_meta)::numeric
    ) AS saldo_neto
FROM datos_personales dp
JOIN config_ciclo_lectivo c ON dp.cohorte = c.anio
WHERE dp.activo = TRUE;

-- Verificar que la vista funciona
SELECT * FROM vista_saldo_horas_live LIMIT 3;

-- ============================================================================
-- PASO 2: Modificar Tabla convocatoria
-- ============================================================================

-- Agregar nueva columna turno_cancelado
ALTER TABLE convocatoria 
ADD COLUMN turno_cancelado BOOLEAN DEFAULT FALSE;

-- Agregar comentario para documentación
COMMENT ON COLUMN convocatoria.turno_cancelado IS 
'Marca si el turno fue cancelado puntualmente. Los turnos cancelados NO cuentan para cálculo de saldos.';

-- Eliminar columna antigua asistencia (ahora es seguro)
ALTER TABLE convocatoria 
DROP COLUMN asistencia;

-- Verificar cambios
SELECT 
    turno_cancelado,
    estado,
    COUNT(*) as cantidad
FROM convocatoria
GROUP BY turno_cancelado, estado
ORDER BY estado, turno_cancelado;

-- ============================================================================
-- PASO 3: Actualizar Vista para Excluir Turnos Cancelados
-- ============================================================================

-- Recrear vista con lógica completa de exclusión de cancelados
DROP VIEW IF EXISTS vista_saldo_horas_live;

CREATE OR REPLACE VIEW vista_saldo_horas_live AS
SELECT 
    dp.id_agente,
    COALESCE(dp.apellido || ', ' || dp.nombre, dp.nombre, 'Sin Nombre') AS nombre_completo,
    dp.cohorte,
    (EXTRACT(DAY FROM (NOW() - c.fecha_inicio::timestamp)) / 7)::integer * c.horas_semanales_meta AS meta_teorica,
    (
        COALESCE(
            (SELECT COUNT(*) * 4 
             FROM convocatoria co
             WHERE co.id_agente = dp.id_agente 
               AND co.estado = 'cumplida'
               AND co.turno_cancelado = FALSE  -- NUEVO: excluir cancelados
            ), 0
        )::numeric + 
        COALESCE(
            (SELECT SUM(ah.horas_delta) 
             FROM ajustes_horas ah
             WHERE ah.id_agente = dp.id_agente
            ), 0
        )
    ) AS horas_reales,
    (
        COALESCE(
            (SELECT COUNT(*) * 4 
             FROM convocatoria co
             WHERE co.id_agente = dp.id_agente 
               AND co.estado = 'cumplida'
               AND co.turno_cancelado = FALSE
            ), 0
        )::numeric + 
        COALESCE(
            (SELECT SUM(ah.horas_delta) 
             FROM ajustes_horas ah
             WHERE ah.id_agente = dp.id_agente
            ), 0
        ) - 
        ((EXTRACT(DAY FROM (NOW() - c.fecha_inicio::timestamp)) / 7)::integer * c.horas_semanales_meta)::numeric
    ) AS saldo_neto
FROM datos_personales dp
JOIN config_ciclo_lectivo c ON dp.cohorte = c.anio
WHERE dp.activo = TRUE;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- 1. Verificar vista funciona correctamente
SELECT 
    nombre_completo,
    cohorte,
    meta_teorica,
    horas_reales,
    saldo_neto
FROM vista_saldo_horas_live
ORDER BY id_agente
LIMIT 5;

-- 2. Verificar estructura de tabla
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'convocatoria'
  AND column_name IN ('asistencia', 'turno_cancelado', 'estado')
ORDER BY ordinal_position;

-- 3. Verificar datos
SELECT 
    estado,
    turno_cancelado,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as porcentaje
FROM convocatoria
GROUP BY estado, turno_cancelado
ORDER BY estado, turno_cancelado;

-- ============================================================================
-- RESULTADO ESPERADO:
-- - Vista funciona sin errores
-- - Columna 'asistencia' NO existe
-- - Columna 'turno_cancelado' existe con DEFAULT FALSE
-- - Todos los registros tienen turno_cancelado = FALSE
-- ============================================================================
