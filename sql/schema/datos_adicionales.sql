-- ============================================================================
-- TABLA: DATOS PERSONALES ADICIONALES (Extension 2026)
-- Propósito: Almacenar información extra del formulario de residentes que no
-- encaja en el esquema core de datos_personales.
-- Relación: 1 a 1 con datos_personales
-- ============================================================================

CREATE TABLE IF NOT EXISTS datos_personales_adicionales (
    id_agente BIGINT PRIMARY KEY REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    referencia_emergencia TEXT,
    nombre_preferido TEXT,
    pronombres TEXT,
    formacion_extra TEXT,
    info_extra TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_datos_adicionales_agente ON datos_personales_adicionales(id_agente);

-- Trigger para updated_at (opcional, si existe la función standard)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'moddatetime') THEN
        CREATE TRIGGER handle_updated_at BEFORE UPDATE ON datos_personales_adicionales
        FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
    END IF;
END $$;

COMMENT ON TABLE datos_personales_adicionales IS 'Extension de datos_personales para info social/extra (2026)';
