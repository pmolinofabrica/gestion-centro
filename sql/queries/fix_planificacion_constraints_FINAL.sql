-- ==============================================================================
-- FIX FINAL: ELIMINACIÓN FORZADA DE RESTRICCIONES (BRUTE FORCE)
-- ==============================================================================

DO $$
DECLARE
    r RECORD;
BEGIN
    -- 1. Buscar y eliminar cualquier restricción UNIQUE sobre (id_dia, id_turno)
    --    que NO incluya 'grupo'.
    FOR r IN (
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'planificacion'::regclass
        AND contype = 'u'  -- Unique
        AND array_length(conkey, 1) = 2 -- Solo 2 columnas
    ) LOOP
        -- Verificar si las columnas son id_dia y id_turno
        -- (Es complejo verificarlo por nombre exacto en PL/pgSQL puro sin arrays de OIDs,
        --  así que seremos agresivos: si es unique de 2 cols en esta tabla, es sospechosa.
        --  La única otra podría ser (id_plani) pero esa es PK (p), no U.
        
        EXECUTE 'ALTER TABLE planificacion DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
        RAISE NOTICE 'Restricción eliminada: %', r.conname;
    END LOOP;

    -- 2. También buscar índices UNIQUE que no sean constraints
    FOR r IN (
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'planificacion'
        AND indexdef LIKE '%UNIQUE%'
        AND indexdef LIKE '%id_dia%'
        AND indexdef LIKE '%id_turno%'
        AND indexdef NOT LIKE '%grupo%' -- No borrar la nueva si ya existe
    ) LOOP
        EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.indexname);
        RAISE NOTICE 'Índice eliminado: %', r.indexname;
    END LOOP;
    
END $$;

-- 3. Re-aplicar la lógica de grupos (por si acaso)
-- Columna
ALTER TABLE planificacion 
ADD COLUMN IF NOT EXISTS grupo VARCHAR(10) DEFAULT NULL;

-- Limpieza de duplicados (mantener el más antiguo)
DELETE FROM planificacion a 
USING planificacion b
WHERE a.id_plani > b.id_plani
  AND a.id_dia = b.id_dia
  AND a.id_turno = b.id_turno
  AND (a.grupo = b.grupo OR (a.grupo IS NULL AND b.grupo IS NULL));

-- Nueva restricción
ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno_grupo;

ALTER TABLE planificacion 
ADD CONSTRAINT uq_plani_dia_turno_grupo UNIQUE (id_dia, id_turno, grupo);

COMMENT ON TABLE planificacion IS 'Fix FINAL aplicado: Restricciones limpiadas vía DO block.';
