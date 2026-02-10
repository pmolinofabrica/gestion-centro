-- ============================================================
-- FIX PERMISOS: Tabla planificacion
-- ============================================================
-- Ejecutar en Supabase SQL Editor (una línea a la vez si falla)

-- 1. Otorgar permisos completos a service_role
GRANT ALL ON planificacion TO service_role;

-- 2. Eliminar políticas existentes si las hay
DROP POLICY IF EXISTS "service_role_full_access" ON planificacion;
DROP POLICY IF EXISTS "public_read_planificacion" ON planificacion;

-- 3. Crear política para service_role
CREATE POLICY "service_role_full_access" 
ON planificacion 
FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- 4. Crear política de lectura pública (opcional, solo si necesitas acceso desde frontend)
CREATE POLICY "public_read_planificacion" 
ON planificacion 
FOR SELECT 
TO anon, authenticated
USING (true);

-- ============================================================
-- VERIFICACIÓN
-- ============================================================
-- Copiar y ejecutar esto por separado para verificar:

SELECT 
  grantee, 
  privilege_type 
FROM information_schema.role_table_grants 
WHERE table_name = 'planificacion';
