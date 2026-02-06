-- ============================================================================
-- MÓDULO IMPORTACIÓN CALENDARIO (ELT Architecture)
-- ============================================================================

-- 1. Tabla Staging (Buzón de entrada)
CREATE TABLE IF NOT EXISTS stg_calendario_import (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    id_turno INTEGER NOT NULL,
    config_raw TEXT NOT NULL, -- Ej: "1:2, 5, 8:3"
    usuario_carga TEXT, -- Opcional, para auditoría
    procesado BOOLEAN DEFAULT FALSE,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para desempeño
CREATE INDEX IF NOT EXISTS idx_stg_procesado ON stg_calendario_import(procesado);

-- 2. Función de Procesamiento (Parser SQL)
CREATE OR REPLACE FUNCTION procesar_importacion_calendario()
RETURNS TRIGGER AS $$
DECLARE
    r_dispositivo RECORD;
    v_item TEXT;
    v_parts TEXT[];
    v_id_disp INTEGER;
    v_cupo INTEGER;
BEGIN
    -- Solo procesar si es nuevo insert
    IF TG_OP = 'INSERT' THEN
        
        BEGIN
            -- 1. Limpiar asignaciones previas para esa fecha/turno (Opcional: decide política de reemplazo)
            -- Por seguridad, podriamos borrar lo que choque, o simplemente insertar/actualizar.
            -- Asumiremos que es carga aditiva o correctiva con UPSERT.
            
            -- 2. Parsear el string separado por comas
            FOREACH v_item IN ARRAY string_to_array(NEW.config_raw, ',')
            LOOP
                v_item := trim(v_item);
                IF v_item = '' THEN CONTINUE; END IF;
                
                -- Detectar formato "ID:Cupo" o solo "ID"
                IF position(':' in v_item) > 0 THEN
                    v_parts := string_to_array(v_item, ':');
                    v_id_disp := v_parts[1]::INTEGER;
                    v_cupo := v_parts[2]::INTEGER;
                ELSE
                    v_id_disp := v_item::INTEGER;
                    v_cupo := 1; -- Default
                END IF;
                
                -- 3. Validar existencia del dispositivo
                IF NOT EXISTS (SELECT 1 FROM dispositivos WHERE id_dispositivo = v_id_disp) THEN
                    RAISE EXCEPTION 'Dispositivo ID % no existe', v_id_disp;
                END IF;
                
                -- 4. Upsert en tabla real
                INSERT INTO calendario_dispositivos (fecha, id_turno, id_dispositivo, cupo_objetivo)
                VALUES (NEW.fecha, NEW.id_turno, v_id_disp, v_cupo)
                ON CONFLICT (fecha, id_turno, id_dispositivo) 
                DO UPDATE SET cupo_objetivo = EXCLUDED.cupo_objetivo;
                
            END LOOP;
            
            -- Marcar como procesado OK
            UPDATE stg_calendario_import 
            SET procesado = TRUE, error = NULL
            WHERE id = NEW.id;
            
        EXCEPTION WHEN OTHERS THEN
            -- Capturar error y guardarlo en la tabla staging
            UPDATE stg_calendario_import 
            SET procesado = FALSE, error = SQLERRM
            WHERE id = NEW.id;
        END;
        
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Trigger
DROP TRIGGER IF EXISTS trg_procesar_importacion ON stg_calendario_import;
CREATE TRIGGER trg_procesar_importacion
AFTER INSERT ON stg_calendario_import
FOR EACH ROW
EXECUTE FUNCTION procesar_importacion_calendario();

-- 4. Grants necesarios (Importante para que GAS pueda escribir)
GRANT ALL ON TABLE stg_calendario_import TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE stg_calendario_import_id_seq TO anon, authenticated, service_role;
