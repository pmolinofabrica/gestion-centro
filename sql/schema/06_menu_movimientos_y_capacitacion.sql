-- ============================================================================
-- SQL DAMA PARA MOVIMIENTOS Y CAPACITACIÓN EN SERVICIO
-- ============================================================================

-- 1. Asegurar la columna en asignaciones (El Plan)
ALTER TABLE asignaciones 
    ADD COLUMN IF NOT EXISTS es_capacitacion_servicio BOOLEAN DEFAULT FALSE;

-- 2. Expandir la tabla menu para registrar la ejecución real (Movimientos / Data Lineage)
ALTER TABLE menu
    ADD COLUMN IF NOT EXISTS estado_ejecucion VARCHAR(30) DEFAULT 'planificado',
    ADD COLUMN IF NOT EXISTS id_dispositivo_origen INTEGER,
    ADD COLUMN IF NOT EXISTS dispositivo_cerrado BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS es_capacitacion_servicio BOOLEAN DEFAULT FALSE;

-- Asegurar restricciones de consistencia
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_estado_ejecucion') THEN
        ALTER TABLE menu ADD CONSTRAINT chk_estado_ejecucion 
            CHECK (estado_ejecucion IN ('planificado', 'ausente_aviso', 'ausente_imprevisto', 'reasignado_decision', 'reasignado_necesidad', 'cubierto'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_menu_dispositivo_origen') THEN
        ALTER TABLE menu ADD CONSTRAINT fk_menu_dispositivo_origen 
            FOREIGN KEY (id_dispositivo_origen) REFERENCES dispositivos(id_dispositivo) ON DELETE SET NULL;
    END IF;
END $$;


-- 3. Crear función de trigger para registrar la capacitación en servicio
CREATE OR REPLACE FUNCTION fn_registrar_capacitacion_servicio()
RETURNS TRIGGER AS $$
DECLARE
    v_id_cap INTEGER;
BEGIN
    -- Solo actuar si es_capacitacion_servicio pasó a TRUE
    IF NEW.es_capacitacion_servicio = TRUE AND (TG_OP = 'INSERT' OR OLD.es_capacitacion_servicio = FALSE) THEN
        
        -- Obtener el id_cap asociado al dispositivo
        SELECT id_cap INTO v_id_cap
        FROM capacitaciones_dispositivos
        WHERE id_dispositivo = NEW.id_dispositivo
        LIMIT 1;

        -- Si el dispositivo requiere una capacitación formal, se evalúa el registro
        IF v_id_cap IS NOT NULL THEN
            -- Verificación Defensiva: ¿Ya tiene el agente esta capacitación cargada?
            IF NOT EXISTS (
                SELECT 1 FROM capacitaciones_participantes 
                WHERE id_cap = v_id_cap AND id_agente = NEW.id_agente
            ) THEN
                -- No la tiene -> Se hace el INSERT "Aprobado por Servicio"
                INSERT INTO capacitaciones_participantes (
                    id_cap, 
                    id_agente, 
                    asistio, 
                    observaciones
                ) VALUES (
                    v_id_cap, 
                    NEW.id_agente, 
                    TRUE, 
                    'Acreditación automática por capacitación en servicio (Trigger: ' || TG_TABLE_NAME || ')'
                );
            ELSE
                -- Ya la tiene -> Solo actualizamos la observación y marcamos asistio
                UPDATE capacitaciones_participantes
                SET asistio = TRUE,
                    observaciones = COALESCE(observaciones, '') || ' | Re-acreditado en servicio.'
                WHERE id_cap = v_id_cap AND id_agente = NEW.id_agente;
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Aplicar los triggers a ambas tablas (Planificación y Ejecución)
DROP TRIGGER IF EXISTS trg_cap_servicio_asignaciones ON asignaciones;
CREATE TRIGGER trg_cap_servicio_asignaciones
AFTER INSERT OR UPDATE ON asignaciones
FOR EACH ROW
EXECUTE FUNCTION fn_registrar_capacitacion_servicio();

DROP TRIGGER IF EXISTS trg_cap_servicio_menu ON menu;
CREATE TRIGGER trg_cap_servicio_menu
AFTER INSERT OR UPDATE ON menu
FOR EACH ROW
EXECUTE FUNCTION fn_registrar_capacitacion_servicio();
