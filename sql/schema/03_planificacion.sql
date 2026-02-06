-- PLANIFICACION
SELECT 'PLANIFICACION' as tabla, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'planificacion' AND table_schema = 'public'
ORDER BY ordinal_position;
