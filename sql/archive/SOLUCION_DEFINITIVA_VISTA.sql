-- ==============================================================================
-- SOLUCIÓN DEFINITIVA: RPC Security Definer para la Vista
-- Ejecutar en Supabase SQL Editor
-- ==============================================================================

-- 1. Asegurar permisos en tablas base faltantes (dias era la culpable probable)
GRANT SELECT ON TABLE dias TO anon, authenticated;
GRANT SELECT ON TABLE turnos TO anon, authenticated;

-- 2. Crear función RPC que encapsula la vista con permisos de administrador (SECURITY DEFINER)
-- Esto ignora RLS y permisos específicos de tablas para quien la llame
CREATE OR REPLACE FUNCTION rpc_obtener_vista_capacitados()
RETURNS SETOF vista_agentes_capacitados
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT * FROM vista_agentes_capacitados;
$$;

-- 3. Permiso para ejecutar esta función
GRANT EXECUTE ON FUNCTION rpc_obtener_vista_capacitados() TO anon, authenticated;

-- 4. Re-aplicar permisos a la vista por si acaso
GRANT SELECT ON TABLE vista_agentes_capacitados TO anon, authenticated;
