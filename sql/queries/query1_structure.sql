-- Query 1: Ver estructura de convocatoria
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_name = 'convocatoria' AND table_schema = 'public'
ORDER BY ordinal_position;
