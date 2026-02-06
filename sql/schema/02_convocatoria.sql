-- ============================================================================
-- COLUMNAS DE TABLAS CRÍTICAS PARA PLANIFICACIÓN
-- ============================================================================

-- CONVOCATORIA
SELECT 'CONVOCATORIA' as tabla, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'convocatoria' AND table_schema = 'public'
ORDER BY ordinal_position;
