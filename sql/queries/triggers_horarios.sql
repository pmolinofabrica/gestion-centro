-- ============================================================================
-- AUTOMATIZACIÓN DE HORARIOS EN PLANIFICACIÓN
-- Propósito: Asignar horarios por defecto según el tipo de turno o respetar manuales
-- ============================================================================

CREATE OR REPLACE FUNCTION func_set_horario_planificacion()
RETURNS TRIGGER AS $$
DECLARE
    v_hora_inicio time;
    v_hora_fin time;
    v_cant_horas numeric;
BEGIN
    -- CASO 1: Si viene con horario manual (desde Sheets/App)
    IF NEW.hora_inicio IS NOT NULL OR NEW.hora_fin IS NOT NULL THEN
        NEW.usa_horario_custom := true;
        IF NEW.motivo_horario_custom IS NULL THEN
            NEW.motivo_horario_custom := 'Carga manual';
        END IF;
        
        -- Calcular cantidad de horas si no viene
        IF NEW.cant_horas IS NULL AND NEW.hora_inicio IS NOT NULL AND NEW.hora_fin IS NOT NULL THEN
            NEW.cant_horas := EXTRACT(EPOCH FROM (NEW.hora_fin - NEW.hora_inicio))/3600;
        END IF;
        
        RETURN NEW;
    END IF;

    -- CASO 2: Si viene sin horario (NULL), buscar default en turnos
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

-- Crear Trigger
DROP TRIGGER IF EXISTS trg_set_horario_planificacion ON planificacion;

CREATE TRIGGER trg_set_horario_planificacion
BEFORE INSERT OR UPDATE ON planificacion
FOR EACH ROW
EXECUTE FUNCTION func_set_horario_planificacion();

-- ============================================================================
-- FIX RETROACTIVO (Opcional: Ejecutar una vez para arreglar vacíos)
-- ============================================================================
-- UPDATE planificacion p
-- SET id_turno = id_turno -- Esto dispara el trigger
-- WHERE hora_inicio IS NULL;
