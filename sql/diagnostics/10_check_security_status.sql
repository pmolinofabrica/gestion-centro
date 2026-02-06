-- DIAGNOSTICO DE SEGURIDAD (RLS) - CORREGIDO
-- Verifica si Row Level Security (RLS) está activo en tus tablas.

-- 1. Estado de RLS (Activado/Desactivado)
SELECT 
    n.nspname as esquema,
    c.relname as tabla,
    c.relrowsecurity as rls_activo -- TRUE = Activado (Bloquea a GAS si no hay policy)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relname IN ('calendario_dispositivos', 'convocatoria', 'planificacion')
AND n.nspname = 'public';

-- 2. Policies Existentes (Si RLS está activo, necesitamos policies)
SELECT 
    tablename as tabla,
    policyname as politica,
    roles as roles_afectados,
    cmd as comando
FROM pg_policies 
WHERE tablename IN ('calendario_dispositivos', 'convocatoria', 'planificacion');
