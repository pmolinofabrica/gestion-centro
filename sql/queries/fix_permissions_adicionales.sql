-- ============================================================================
-- FIX: PERMISOS PARA TABLA ADICIONAL
-- Error 403 prohibido indica falta de GRANTs o bloqueo RLS
-- ============================================================================

-- 1. Habilitar RLS (Mejor practica, aunque service_role lo bypassea, 
-- a veces es necesario para que funcionen las policies si se usa otra key)
ALTER TABLE datos_personales_adicionales ENABLE ROW LEVEL SECURITY;

-- 2. Crear Policy permisiva para la migración (y uso general por ahora)
-- Permite todo a todos (ajustar luego para prod si es necesario)
DROP POLICY IF EXISTS "Enable all access for all users" ON datos_personales_adicionales;

CREATE POLICY "Enable all access for all users"
ON datos_personales_adicionales
FOR ALL
USING (true)
WITH CHECK (true);

-- 3. Grants explícitos
GRANT ALL ON datos_personales_adicionales TO postgres;
GRANT ALL ON datos_personales_adicionales TO anon;
GRANT ALL ON datos_personales_adicionales TO authenticated;
GRANT ALL ON datos_personales_adicionales TO service_role;

-- 4. Grant a la secuencia/id si fuera serial (en este caso es FK manual, no aplica, pero por dudas)
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
