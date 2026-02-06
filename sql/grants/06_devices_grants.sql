-- Grants para tabla dispositivos (Maestra)
-- Necesario para que el script pueda descargar la referencia

GRANT SELECT ON TABLE dispositivos TO anon, authenticated, service_role;

-- Si se requiere inserción (para Upload Dispositivos)
GRANT INSERT, UPDATE ON TABLE dispositivos TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE dispositivos_id_dispositivo_seq TO anon, authenticated, service_role;
