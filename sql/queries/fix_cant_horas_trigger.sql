-- ============================================================================
-- FIX: RECALCULAR CANT_HORAS AL ACTUALIZAR HORARIOS
-- ============================================================================

-- Puesto que el trigger anterior solo calculaba si cant_horas era NULL,
-- necesitamos que recalcule SIEMPRE que cambien hora_inicio o hora_fin.

CREATE OR REPLACE FUNCTION func_set_horario_planificacion()
RETURNS TRIGGER AS $$
DECLARE
    v_hora_inicio time;
    v_hora_fin time;
    v_cant_horas numeric;
    v_should_recalculate boolean;
BEGIN
    -- Determinar si debemos recalcular
    -- 1. Si cant_horas es NULL (caso original)
    -- 2. O si cambiaron los horarios (caso actualización)
    v_should_recalculate := (NEW.cant_horas IS NULL) 
                            OR (NEW.hora_inicio IS DISTINCT FROM OLD.hora_inicio) 
                            OR (NEW.hora_fin IS DISTINCT FROM OLD.hora_fin);

    -- CASO 1: Si viene con horario manual (desde Sheets/App)
    IF NEW.hora_inicio IS NOT NULL OR NEW.hora_fin IS NOT NULL THEN
        NEW.usa_horario_custom := true;
        IF NEW.motivo_horario_custom IS NULL THEN
            NEW.motivo_horario_custom := 'Carga manual / Actualización';
        END IF;
        
        -- Calcular cantidad de horas si es necesario
        IF v_should_recalculate AND NEW.hora_inicio IS NOT NULL AND NEW.hora_fin IS NOT NULL THEN
            NEW.cant_horas := ROUND((EXTRACT(EPOCH FROM (NEW.hora_fin - NEW.hora_inicio))/3600)::numeric, 2);
        END IF;
        
        RETURN NEW;
    END IF;

    -- CASO 2: Si viene sin horario (NULL), buscar default en turnos
    -- Solo si no es un update parcial donde se borran los horarios explícitamente
    -- (Asumimos que si se borran, se quiere volver al default)
    SELECT hora_inicio, hora_fin, cant_horas
    INTO v_hora_inicio, v_hora_fin, v_cant_horas
    FROM turnos
    WHERE id_turno = NEW.id_turno;

    -- Asignar valores por defecto
    NEW.hora_inicio := v_hora_inicio;
    NEW.hora_fin := v_hora_fin;
    NEW.cant_horas := v_cant_horas;
    NEW.usa_horario_custom := false;
    NEW.motivo_horario_custom := NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Re-crear Trigger en PLANIFICACION
DROP TRIGGER IF EXISTS trg_set_horario_planificacion ON planificacion;

CREATE TRIGGER trg_set_horario_planificacion
BEFORE INSERT OR UPDATE ON planificacion
FOR EACH ROW
EXECUTE FUNCTION func_set_horario_planificacion();

-- ============================================================================
-- INTENTO DE APLICAR A CONVOCATORIA (Si corresponde)
-- ============================================================================
-- Verificamos si la tabla convocatoria tiene columnas de hora para aplicar lógica similar
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'convocatoria' AND column_name = 'hora_inicio'
    ) THEN
        -- Crear trigger para convocatoria si existen las columnas
        CREATE OR REPLACE FUNCTION func_set_horario_convocatoria()
        RETURNS TRIGGER AS $func$
        DECLARE
            v_should_recalculate boolean;
        BEGIN
            v_should_recalculate := (NEW.cant_horas IS NULL) 
                                    OR (NEW.hora_inicio IS DISTINCT FROM OLD.hora_inicio) 
                                    OR (NEW.hora_fin IS DISTINCT FROM OLD.hora_fin);

            IF NEW.hora_inicio IS NOT NULL AND NEW.hora_fin IS NOT NULL AND v_should_recalculate THEN
                 NEW.cant_horas := ROUND((EXTRACT(EPOCH FROM (NEW.hora_fin - NEW.hora_inicio))/3600)::numeric, 2);
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_set_horario_convocatoria ON convocatoria;
        
        CREATE TRIGGER trg_set_horario_convocatoria
        BEFORE INSERT OR UPDATE ON convocatoria
        FOR EACH ROW
        EXECUTE FUNCTION func_set_horario_convocatoria();
        
        RAISE NOTICE 'Trigger aplicado también a tabla CONVOCATORIA';
    ELSE
        RAISE NOTICE 'La tabla CONVOCATORIA no tiene columnas de hora, no se aplicó trigger extra.';
    END IF;
END $$;
