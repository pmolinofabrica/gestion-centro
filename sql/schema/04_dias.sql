-- DIAS
SELECT 'DIAS' as tabla, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'dias' AND table_schema = 'public'
ORDER BY ordinal_position;
