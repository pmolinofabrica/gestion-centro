-- ============================================================================
-- SQL Fix: Permisos para Google Apps Script en tabla descansos
-- ============================================================================
-- Objetivo: Solucionar el error HTTP 403 "permission denied for table descansos"
-- Entorno: Local / Desarrollo
-- Impacto Operativo: Permite a Google Forms insertar/ver descansos
-- ============================================================================

-- 1. Otorgar permisos de lectura y escritura al rol anónimo y autenticado (usados por el API REST de Supabase)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.descansos TO anon, authenticated, service_role;

-- 2. Otorgar permisos sobre la secuencia del ID (necesario para hacer INSERTs)
-- (Captura genérica de todas las secuencias para evitar errores de nombre de secuencia)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- 3. Desactivar RLS (Row Level Security) temporalmente para esta tabla, 
-- replicando el mismo comportamiento que tienen las tablas calendario_dispositivos, convocatoria y turnos
-- documentado en sql/grants/09_disable_rls_for_gas.sql
ALTER TABLE public.descansos DISABLE ROW LEVEL SECURITY;
