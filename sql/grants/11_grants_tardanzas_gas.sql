-- ============================================================================
-- SQL Fix: Permisos para Google Apps Script en tabla tardanzas
-- ============================================================================
-- Objetivo: Solucionar el error HTTP 403 "permission denied for table tardanzas"
-- Entorno: Local / Desarrollo
-- Impacto Operativo: Permite a Google Forms insertar tardanzas
-- ============================================================================

-- 1. Otorgar permisos de lectura y escritura al rol anónimo y autenticado (usados por el API REST de Supabase)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tardanzas TO anon, authenticated, service_role;

-- 2. Otorgar permisos sobre la secuencia del ID (necesario para hacer INSERTs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- 3. Desactivar RLS (Row Level Security) temporalmente para esta tabla, 
-- permitiendo que Apps Script se comunique sin firmar como un usuario de Supabase Auth
ALTER TABLE public.tardanzas DISABLE ROW LEVEL SECURITY;
