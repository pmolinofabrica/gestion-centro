-- ==============================================================================
-- PERMISOS Y SEGURIDAD (GRANTS) - ACTUALIZADO CON TIEMPO_MINUTOS
-- ==============================================================================

-- 1. Tabla Capacitaciones
GRANT ALL ON TABLE capacitaciones TO postgres, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE capacitaciones TO anon, authenticated;

-- 2. Tabla Capacitaciones Participantes
GRANT ALL ON TABLE capacitaciones_participantes TO postgres, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE capacitaciones_participantes TO anon, authenticated;

-- 3. Tabla Capacitaciones Dispositivos (incluye nueva columna tiempo_minutos)
GRANT ALL ON TABLE capacitaciones_dispositivos TO postgres, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE capacitaciones_dispositivos TO anon, authenticated;

-- Grants explícitos en columnas (por si RLS está activo)
GRANT SELECT (id_cap, id_dispositivo, tiempo_minutos) ON TABLE capacitaciones_dispositivos TO anon, authenticated;

-- 4. Tabla Dispositivos (necesaria para renderizar matriz)
GRANT SELECT ON TABLE dispositivos TO anon, authenticated;

-- 5. Tabla Datos Personales (residentes)
GRANT SELECT ON TABLE datos_personales TO anon, authenticated;

-- 6. Vista Agentes Capacitados (Solo Lectura)
GRANT SELECT ON TABLE vista_agentes_capacitados TO anon, authenticated;

-- 7. Secuencias (Vital para inserts si hay campos serial)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- 6. Permisos de Ejecución para RPCs
GRANT EXECUTE ON FUNCTION rpc_guardar_matriz_dispositivos(JSONB) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION rpc_guardar_participantes_grupo(JSONB) TO anon, authenticated;

-- 7. Verificar políticas RLS (si están activas, deben permitir acceso)
-- Si RLS está habilitado en capacitaciones_dispositivos, crear política permisiva:
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'capacitaciones_dispositivos' AND rowsecurity = true) THEN
        DROP POLICY IF EXISTS "Acceso total capacitaciones_dispositivos" ON capacitaciones_dispositivos;
        CREATE POLICY "Acceso total capacitaciones_dispositivos" ON capacitaciones_dispositivos FOR ALL USING (true);
    END IF;
END $$;
