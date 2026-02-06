-- VISITAS_GRUPALES
SELECT 'VISITAS_GRUPALES' as tabla, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'visitas_grupales' AND table_schema = 'public'
ORDER BY ordinal_position;
