-- Query para verificar si inasistencias tiene permisos RLS
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename = 'inasistencias' AND schemaname = 'public';

-- Query para ver las políticas RLS
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'inasistencias' AND schemaname = 'public';
