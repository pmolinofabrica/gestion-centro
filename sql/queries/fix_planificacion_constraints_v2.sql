-- ==============================================================================
-- FIX V2: RESTRICCIONES DE PLANIFICACIÓN PARA GRUPOS (ROBUSTO)
-- ==============================================================================
-- Este script realiza 4 pasos críticos:
-- 1. Asegura que la columna 'grupo' exista.
-- 2. Elimina duplicados existentes para evitar errores al crear la restricción.
-- 3. Elimina la restricción antigua.
-- 4. Crea la nueva restricción.

-- PASO 1: Asegurar columna 'grupo'
ALTER TABLE planificacion 
ADD COLUMN IF NOT EXISTS grupo VARCHAR(10) DEFAULT NULL;

-- PASO 2: Eliminar duplicados (Manejo de Limpieza de Datos)
-- Si ya existen filas idénticas (dia, turno, grupo), mantenemos solo la más antigua (min id_plani)
DELETE FROM planificacion a 
USING planificacion b
WHERE a.id_plani > b.id_plani
  AND a.id_dia = b.id_dia
  AND a.id_turno = b.id_turno
  AND (a.grupo = b.grupo OR (a.grupo IS NULL AND b.grupo IS NULL));

-- PASO 3: Eliminar restricciones antiguas
ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno;

ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno_grupo;

-- PASO 4: Crear nueva restricción UNIQUE
-- Ahora es seguro crearla porque eliminamos los duplicados en el Paso 2.
ALTER TABLE planificacion 
ADD CONSTRAINT uq_plani_dia_turno_grupo UNIQUE (id_dia, id_turno, grupo);

-- Verificación
COMMENT ON TABLE planificacion IS 'Fix V2 aplicado: Soporte multigrupo habilitado y duplicados limpiados.';
