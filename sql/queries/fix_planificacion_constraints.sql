-- ==============================================================================
-- FIX: RESTRICCIONES DE PLANIFICACIÓN PARA GRUPOS
-- ==============================================================================
-- Problema: Al intentar cargar un grupo 'B' cuando ya existe 'A' para el mismo día y turno,
-- el sistema actualiza el registro 'A' en lugar de crear uno nuevo.
-- Causa: Existe una restricción UNIQUE(id_dia, id_turno) antigua que forza el conflicto.
-- Solución: Eliminar esa restricción y usar UNIQUE(id_dia, id_turno, grupo).

-- 1. Eliminar restricción antigua (si existe)
ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno;

-- 2. Asegurar que existe la nueva restricción que incluye 'grupo'
-- Nota: Usamos NULLS NOT DISTINCT si es Postgres 15+ para que NULL sea tratado como valor único
-- Pero para compatibilidad segura y dado que 'grupo' es nullable, mejor usamos COALESCE en índice o simplemente aseguramos que el GAS envíe un valor por defecto.
-- Por ahora, creamos la constraint estándar.

ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno_grupo;

-- Opción A: Standard (NULL != NULL) -> Permite múltiples NULLs para mismo día/turno
-- Opción B: Unique Index con Coalesce -> Para que NULL cuente como único "Default"
-- Vamos con Opción A porque el código GAS maneja lógica. 
-- Lo importante es que 'A' y 'B' no conflictúen.

ALTER TABLE planificacion 
ADD CONSTRAINT uq_plani_dia_turno_grupo UNIQUE (id_dia, id_turno, grupo);

-- 3. Verificación
COMMENT ON TABLE planificacion IS 'Fix aplicado: Constraint uq_plani_dia_turno eliminada. Ahora permite múltiples grupos por turno.';
