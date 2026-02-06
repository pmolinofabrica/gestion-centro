-- ============================================================================
-- QUERY MAESTRA: SCHEMA COMPLETO DE SUPABASE
-- ============================================================================

-- 1. TODAS LAS TABLAS EN EL SCHEMA PUBLIC
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name AND c.table_schema = 'public') as num_columnas
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
