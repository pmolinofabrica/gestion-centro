-- ============================================================
-- LIMPIEZA DE DUPLICADOS: Participantes Multi-Grupo
-- ============================================================
-- El ETL asignó erróneamente a cada persona a TODOS los grupos
-- de una fecha, en lugar de solo su grupo correspondiente.
-- 
-- Esta migración corrige el problema eliminando registros duplicados
-- y preservando solo uno por combinación (fecha, dispositivo, agente).
-- ============================================================

BEGIN;

-- 1. Crear tabla temporal con las asignaciones correctas (una por fecha+dispositivo+agente)
CREATE TEMP TABLE participantes_limpios AS
SELECT DISTINCT ON (d.fecha, cd.id_dispositivo, cp.id_agente)
    cp.id_participante,
    cp.id_cap,
    cp.id_agente,
    cp.asistio,
    d.fecha,
    c.grupo
FROM capacitaciones_participantes cp
JOIN capacitaciones c ON cp.id_cap = c.id_cap
JOIN capacitaciones_dispositivos cd ON c.id_cap = cd.id_cap
JOIN dias d ON c.id_dia = d.id_dia
ORDER BY d.fecha, cd.id_dispositivo, cp.id_agente, cp.id_participante;

-- 2. Contar cuántos se eliminarán
DO $$
DECLARE
    total_antes INT;
    total_despues INT;
    eliminados INT;
BEGIN
    SELECT count(*) INTO total_antes FROM capacitaciones_participantes;
    SELECT count(*) INTO total_despues FROM participantes_limpios;
    eliminados := total_antes - total_despues;
    
    RAISE NOTICE 'Total antes: %, Total después: %, Eliminados: %', 
        total_antes, total_despues, eliminados;
END $$;

-- 3. Eliminar registros que NO están en la tabla limpia
DELETE FROM capacitaciones_participantes
WHERE id_participante NOT IN (SELECT id_participante FROM participantes_limpios);

-- 4. Verificar resultado
SELECT 
    count(*) as total_participantes,
    count(DISTINCT id_agente) as agentes_unicos
FROM capacitaciones_participantes;

COMMIT;

-- Limpiar tabla temporal
DROP TABLE IF EXISTS participantes_limpios;
