-- ============================================================================
-- MIGRATION: Add 'lugar' field to planificacion table
-- Author: Pablo - Data Analyst
-- Date: 2026-02-09
-- Description: Adds a TEXT field to store location information for planned shifts
-- ============================================================================

-- Add the lugar column
ALTER TABLE planificacion 
ADD COLUMN lugar TEXT DEFAULT NULL;

-- Add comment for DAMA compliance (metadata documentation)
COMMENT ON COLUMN planificacion.lugar IS 
'Ubicación física o sala donde se realizará el turno planificado. Campo opcional de texto libre.';

-- Verification query
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns 
-- WHERE table_name = 'planificacion' AND column_name = 'lugar';
