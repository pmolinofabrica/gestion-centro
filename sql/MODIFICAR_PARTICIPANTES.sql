-- ==============================================================================
-- SCRIPT: Modificaciones a tabla capacitaciones_participantes
-- Ejecutar en Supabase SQL Editor
-- ==============================================================================

-- IMPORTANTE: Estos comandos modifican la TABLA, no la vista

-- 1. Cambiar default de asistio a TRUE en la TABLA
ALTER TABLE capacitaciones_participantes 
ALTER COLUMN asistio SET DEFAULT true;

-- 2. Eliminar columna fecha_certificado de la TABLA
ALTER TABLE capacitaciones_participantes 
DROP COLUMN IF EXISTS fecha_certificado;

-- 4. Asegurar visibilidad (Si RLS está activo)
GRANT ALL ON TABLE capacitaciones_participantes TO postgres, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE capacitaciones_participantes TO anon, authenticated;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'capacitaciones_participantes' AND rowsecurity = true) THEN
        DROP POLICY IF EXISTS "Acceso total participantes" ON capacitaciones_participantes;
        CREATE POLICY "Acceso total participantes" ON capacitaciones_participantes FOR ALL USING (true);
    END IF;
END $$;
