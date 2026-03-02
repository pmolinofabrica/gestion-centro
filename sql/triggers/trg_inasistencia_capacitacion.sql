-- ============================================================================
-- TRIGGER: ACTUALIZAR ASISTENCIA POR INASISTENCIA
-- ============================================================================
-- Propósito: Cuando se registra una inasistencia, marcar automáticamente
--            asistio = FALSE en las capacitaciones de ese día.
-- Tabla: inasistencias
-- Cuándo: AFTER INSERT
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_update_asistencia_on_inasistencia()
RETURNS TRIGGER AS $$
DECLARE
    v_updated_count INTEGER;
BEGIN
    -- Buscar capacitaciones del agente en la fecha de la inasistencia
    -- y marcar asistio = FALSE
    
    WITH caps_del_dia AS (
        SELECT cp.id_participante
        FROM capacitaciones_participantes cp
        JOIN capacitaciones c ON cp.id_cap = c.id_cap
        JOIN dias d ON c.id_dia = d.id_dia
        WHERE cp.id_agente = NEW.id_agente
          AND d.fecha = NEW.fecha_inasistencia
    )
    UPDATE capacitaciones_participantes
    SET asistio = FALSE,
        observaciones = COALESCE(observaciones, '') || ' [Auto: Inasistencia ' || NEW.motivo || ']'
    WHERE id_participante IN (SELECT id_participante FROM caps_del_dia);
    
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    
    IF v_updated_count > 0 THEN
        RAISE NOTICE 'Se actualizaron % capacitaciones a No Asistió debido a inasistencia.', v_updated_count;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_asistencia_on_inasistencia ON inasistencias;

CREATE TRIGGER trg_update_asistencia_on_inasistencia
    AFTER INSERT ON inasistencias
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_asistencia_on_inasistencia();

COMMENT ON FUNCTION fn_update_asistencia_on_inasistencia() IS 'Marca asistio=FALSE en capacitaciones si se registra inasistencia el mismo día';
