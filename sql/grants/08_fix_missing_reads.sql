-- Grants faltantes para lecturas criticas en GAS
-- IMPORTANTE: Ejecutar esto para que "Generar Plantilla" pueda pre-llenar datos

-- 1. Calendario Confirmado (Para ver cupos ya cargados)
GRANT SELECT ON TABLE calendario_dispositivos TO anon, authenticated, service_role;

-- 2. Convocatoria (Para ver "👥 Convocados")
GRANT SELECT ON TABLE convocatoria TO anon, authenticated, service_role;

-- 3. Turnos (Para leer nombres de turno si se requiere)
GRANT SELECT ON TABLE turnos TO anon, authenticated, service_role;

-- 4. Vista Estado (Para el botón "Ver Estado Planificado")
GRANT SELECT ON TABLE vista_estado_calendario TO anon, authenticated, service_role;

-- Asegurar secuencias si hay inserts directos (no stg)
GRANT USAGE, SELECT ON SEQUENCE calendario_dispositivos_id_seq TO anon, authenticated, service_role;
