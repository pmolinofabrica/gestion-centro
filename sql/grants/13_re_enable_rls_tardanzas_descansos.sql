-- ============================================================================
-- SQL: Fix Security Lints for Tardanzas y Descansos
-- ============================================================================
-- Objetivo: Volver a activar RLS en las tablas que habíamos apagado para 
-- permitir que Google Apps Script escribiera datos temporales. 
-- Para que el GAS siga funcionando tras este cambio, se DEBE cambiar
-- el NEXT_PUBLIC_SUPABASE_ANON_KEY por el SERVICE_ROLE_KEY en el script.
-- ============================================================================

-- REACTIVAR RLS
ALTER TABLE public.descansos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tardanzas ENABLE ROW LEVEL SECURITY;

-- Nota: Como ya existen políticas (Policies) en estas tablas de antes, o
-- al menos al estar el RLS encendido, cualquier request que use el ANON_KEY 
-- será rechazado. El Service Role Key bypassea esto automáticamente.
