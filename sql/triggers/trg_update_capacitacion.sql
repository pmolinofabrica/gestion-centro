CREATE OR REPLACE FUNCTION actualizar_capacitacion_desde_planificacion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Solo actuar si hubieron cambios en las claves que unen ambas tablas (fecha, turno o grupo)
    IF (OLD.id_dia != NEW.id_dia OR OLD.id_turno != NEW.id_turno OR OLD.grupo IS DISTINCT FROM NEW.grupo) THEN
        UPDATE capacitaciones 
        SET id_dia = NEW.id_dia,
            id_turno = NEW.id_turno,
            grupo = NEW.grupo
        WHERE id_dia = OLD.id_dia 
          AND id_turno = OLD.id_turno 
          AND (grupo = OLD.grupo OR (grupo IS NULL AND OLD.grupo IS NULL));
    END IF;
    
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_planificacion_a_capacitaciones ON planificacion;

CREATE TRIGGER trg_update_planificacion_a_capacitaciones
AFTER UPDATE ON planificacion
FOR EACH ROW
EXECUTE FUNCTION actualizar_capacitacion_desde_planificacion();
