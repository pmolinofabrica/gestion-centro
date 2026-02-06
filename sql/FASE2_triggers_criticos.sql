-- ============================================================================
-- SISTEMA DE GESTIÓN DE RECURSOS HUMANOS - POSTGRESQL v3.0
-- ESTRATEGIA HÍBRIDA - FASE 2: TRIGGERS CRÍTICOS
-- ============================================================================
-- 
-- REQUISITO: Ejecutar DESPUÉS de FASE1_schema_base_limpio.sql
-- 
-- Este archivo agrega los 3 TRIGGERS CRÍTICOS:
-- 1. trg_plani_auto_horarios     - Auto-completa horarios desde catálogo
-- 2. trg_prevent_duplicate_vigente - Previene convocatorias duplicadas
-- 3. trg_auto_requiere_certificado - Auto-marca certificado requerido
-- 
-- Estos triggers son ESENCIALES para el funcionamiento básico del sistema.
-- Los triggers secundarios (saldos, historial, etc) pueden agregarse después.
-- 
-- Autor: Pablo - Data Analyst
-- Fecha: Diciembre 2025
-- ============================================================================

-- ============================================================================
-- TRIGGER 1: AUTO-COMPLETAR HORARIOS EN PLANIFICACIÓN
-- ============================================================================
-- Propósito: Cuando se crea una planificación sin horarios especificados,
--            los completa automáticamente desde el catálogo de turnos
-- Tabla: planificacion
-- Cuándo: BEFORE INSERT
-- Condición: hora_inicio IS NULL
-- ============================================================================

-- Función del trigger
CREATE OR REPLACE FUNCTION fn_plani_auto_horarios()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo actuar si NO hay horarios especificados
    IF NEW.hora_inicio IS NULL THEN
        -- Obtener horarios del catálogo de turnos
        SELECT 
            COALESCE(hora_inicio_default, '00:00'::TIME),
            COALESCE(hora_fin_default, '23:59'::TIME),
            COALESCE(cant_horas_default, 0)
        INTO 
            NEW.hora_inicio,
            NEW.hora_fin,
            NEW.cant_horas
        FROM turnos
        WHERE id_turno = NEW.id_turno;
        
        -- Marcar que usa horarios del catálogo (no custom)
        NEW.usa_horario_custom := FALSE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
CREATE TRIGGER trg_plani_auto_horarios
    BEFORE INSERT ON planificacion
    FOR EACH ROW
    WHEN (NEW.hora_inicio IS NULL)
    EXECUTE FUNCTION fn_plani_auto_horarios();

COMMENT ON FUNCTION fn_plani_auto_horarios() IS 'Auto-completa horarios de planificación desde catálogo de turnos';
COMMENT ON TRIGGER trg_plani_auto_horarios ON planificacion IS 'Trigger crítico: completa horarios automáticamente si no se especifican';

-- ============================================================================
-- TRIGGER 2: PREVENIR CONVOCATORIAS DUPLICADAS VIGENTES
-- ============================================================================
-- Propósito: Impide que un agente tenga múltiples convocatorias vigentes
--            para la misma fecha (evita doble booking)
-- Tabla: convocatoria
-- Cuándo: BEFORE INSERT
-- Condición: estado = 'vigente'
-- ============================================================================

-- Función del trigger
CREATE OR REPLACE FUNCTION fn_prevent_duplicate_vigente()
RETURNS TRIGGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Solo validar si el estado es 'vigente'
    IF NEW.estado = 'vigente' THEN
        -- Contar convocatorias vigentes existentes para mismo agente/fecha
        SELECT COUNT(*)
        INTO v_count
        FROM convocatoria
        WHERE id_agente = NEW.id_agente
          AND fecha_convocatoria = NEW.fecha_convocatoria
          AND estado = 'vigente';
        
        -- Si ya existe una, abortar con error
        IF v_count > 0 THEN
            RAISE EXCEPTION 'ERROR: El agente ya tiene una convocatoria vigente para la fecha %', 
                NEW.fecha_convocatoria;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
CREATE TRIGGER trg_prevent_duplicate_vigente
    BEFORE INSERT ON convocatoria
    FOR EACH ROW
    WHEN (NEW.estado = 'vigente')
    EXECUTE FUNCTION fn_prevent_duplicate_vigente();

COMMENT ON FUNCTION fn_prevent_duplicate_vigente() IS 'Previene convocatorias duplicadas vigentes para mismo agente/fecha';
COMMENT ON TRIGGER trg_prevent_duplicate_vigente ON convocatoria IS 'Trigger crítico: previene doble booking de agentes';

-- ============================================================================
-- TRIGGER 3: AUTO-MARCAR SI REQUIERE CERTIFICADO
-- ============================================================================
-- Propósito: Cuando se registra una inasistencia, determina automáticamente
--            si requiere certificado según el motivo
-- Tabla: inasistencias
-- Cuándo: BEFORE INSERT
-- Condición: requiere_certificado IS NULL
-- Lógica: medico/estudio/otro_justificada → requiere_certificado = TRUE
--         imprevisto/injustificada → requiere_certificado = FALSE
-- ============================================================================

-- Función del trigger
CREATE OR REPLACE FUNCTION fn_auto_requiere_certificado()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo actuar si requiere_certificado no está especificado
    IF NEW.requiere_certificado IS NULL THEN
        -- Determinar según motivo
        IF NEW.motivo IN ('medico', 'estudio', 'otro_justificada') THEN
            NEW.requiere_certificado := TRUE;
            -- Mantener estado pendiente (requiere certificado)
        ELSE
            NEW.requiere_certificado := FALSE;
            -- Si no requiere certificado, marcar como injustificada
            NEW.estado := 'injustificada';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
CREATE TRIGGER trg_auto_requiere_certificado
    BEFORE INSERT ON inasistencias
    FOR EACH ROW
    WHEN (NEW.requiere_certificado IS NULL)
    EXECUTE FUNCTION fn_auto_requiere_certificado();

COMMENT ON FUNCTION fn_auto_requiere_certificado() IS 'Auto-determina si inasistencia requiere certificado según motivo';
COMMENT ON TRIGGER trg_auto_requiere_certificado ON inasistencias IS 'Trigger crítico: marca automáticamente si se requiere certificado';

-- ============================================================================
-- TESTS DE VALIDACIÓN (Ejecutar después de crear triggers)
-- ============================================================================

-- TEST 1: Verificar que los triggers fueron creados correctamente
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Contar triggers creados
    SELECT COUNT(*)
    INTO v_count
    FROM pg_trigger
    WHERE tgname IN (
        'trg_plani_auto_horarios',
        'trg_prevent_duplicate_vigente',
        'trg_auto_requiere_certificado'
    );
    
    IF v_count = 3 THEN
        RAISE NOTICE '✅ TEST 1 PASADO: 3 triggers críticos creados correctamente';
    ELSE
        RAISE WARNING '⚠️ TEST 1 FALLADO: Solo se crearon % de 3 triggers', v_count;
    END IF;
END $$;

-- TEST 2: Verificar que las funciones fueron creadas
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM pg_proc
    WHERE proname IN (
        'fn_plani_auto_horarios',
        'fn_prevent_duplicate_vigente',
        'fn_auto_requiere_certificado'
    );
    
    IF v_count = 3 THEN
        RAISE NOTICE '✅ TEST 2 PASADO: 3 funciones de trigger creadas correctamente';
    ELSE
        RAISE WARNING '⚠️ TEST 2 FALLADO: Solo se crearon % de 3 funciones', v_count;
    END IF;
END $$;

-- ============================================================================
-- TESTS FUNCIONALES (Comentados - descomentar para ejecutar)
-- ============================================================================

/*
-- TEST 3: Probar trigger de auto-horarios
-- Requisitos: Debe existir al menos un día y un turno con horarios default

DO $$
DECLARE
    v_id_dia INTEGER;
    v_id_turno INTEGER;
    v_id_plani INTEGER;
    v_hora_inicio TIME;
    v_usa_custom BOOLEAN;
BEGIN
    -- Obtener un día
    SELECT id_dia INTO v_id_dia FROM dias LIMIT 1;
    
    -- Obtener un turno con horarios default
    SELECT id_turno INTO v_id_turno 
    FROM turnos 
    WHERE hora_inicio_default IS NOT NULL 
    LIMIT 1;
    
    -- Crear planificación SIN especificar horarios
    INSERT INTO planificacion (id_dia, id_turno, cant_residentes_plan)
    VALUES (v_id_dia, v_id_turno, 3)
    RETURNING id_plani, hora_inicio, usa_horario_custom
    INTO v_id_plani, v_hora_inicio, v_usa_custom;
    
    -- Verificar que el trigger completó los horarios
    IF v_hora_inicio IS NOT NULL AND v_usa_custom = FALSE THEN
        RAISE NOTICE '✅ TEST 3 PASADO: Trigger auto-completó horarios correctamente';
    ELSE
        RAISE WARNING '⚠️ TEST 3 FALLADO: Trigger no completó horarios';
    END IF;
    
    -- Limpiar
    DELETE FROM planificacion WHERE id_plani = v_id_plani;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '⚠️ TEST 3 ERROR: %', SQLERRM;
END $$;

-- TEST 4: Probar prevención de duplicados
-- Requisitos: Debe existir un agente y una planificación

DO $$
DECLARE
    v_id_agente INTEGER;
    v_id_plani INTEGER;
    v_id_turno INTEGER;
    v_fecha DATE;
    v_error_caught BOOLEAN := FALSE;
BEGIN
    -- Obtener datos
    SELECT id_agente INTO v_id_agente FROM datos_personales LIMIT 1;
    SELECT id_plani, id_turno, fecha_convocatoria 
    INTO v_id_plani, v_id_turno, v_fecha
    FROM planificacion p
    JOIN dias d ON p.id_dia = d.id_dia
    LIMIT 1;
    
    -- Crear primera convocatoria vigente
    INSERT INTO convocatoria (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
    VALUES (v_id_plani, v_id_agente, v_id_turno, v_fecha, 'vigente');
    
    -- Intentar crear duplicado (debe fallar)
    BEGIN
        INSERT INTO convocatoria (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
        VALUES (v_id_plani, v_id_agente, v_id_turno, v_fecha, 'vigente');
    EXCEPTION
        WHEN OTHERS THEN
            v_error_caught := TRUE;
    END;
    
    -- Verificar
    IF v_error_caught THEN
        RAISE NOTICE '✅ TEST 4 PASADO: Trigger previno correctamente el duplicado';
    ELSE
        RAISE WARNING '⚠️ TEST 4 FALLADO: Trigger permitió duplicado';
    END IF;
    
    -- Limpiar
    DELETE FROM convocatoria 
    WHERE id_agente = v_id_agente AND fecha_convocatoria = v_fecha;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '⚠️ TEST 4 ERROR: %', SQLERRM;
END $$;

-- TEST 5: Probar auto-requiere certificado
-- Requisitos: Debe existir un agente

DO $$
DECLARE
    v_id_agente INTEGER;
    v_id_inasis INTEGER;
    v_requiere BOOLEAN;
    v_estado VARCHAR(20);
BEGIN
    -- Obtener agente
    SELECT id_agente INTO v_id_agente FROM datos_personales LIMIT 1;
    
    -- TEST 5A: Motivo 'medico' debe requerir certificado
    INSERT INTO inasistencias (id_agente, fecha_inasistencia, motivo)
    VALUES (v_id_agente, CURRENT_DATE, 'medico')
    RETURNING id_inasistencia, requiere_certificado, estado
    INTO v_id_inasis, v_requiere, v_estado;
    
    IF v_requiere = TRUE AND v_estado = 'pendiente' THEN
        RAISE NOTICE '✅ TEST 5A PASADO: Motivo medico requiere certificado correctamente';
    ELSE
        RAISE WARNING '⚠️ TEST 5A FALLADO: requiere=%, estado=%', v_requiere, v_estado;
    END IF;
    
    DELETE FROM inasistencias WHERE id_inasistencia = v_id_inasis;
    
    -- TEST 5B: Motivo 'imprevisto' NO debe requerir certificado
    INSERT INTO inasistencias (id_agente, fecha_inasistencia, motivo)
    VALUES (v_id_agente, CURRENT_DATE + 1, 'imprevisto')
    RETURNING id_inasistencia, requiere_certificado, estado
    INTO v_id_inasis, v_requiere, v_estado;
    
    IF v_requiere = FALSE AND v_estado = 'injustificada' THEN
        RAISE NOTICE '✅ TEST 5B PASADO: Motivo imprevisto no requiere certificado';
    ELSE
        RAISE WARNING '⚠️ TEST 5B FALLADO: requiere=%, estado=%', v_requiere, v_estado;
    END IF;
    
    DELETE FROM inasistencias WHERE id_inasistencia = v_id_inasis;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '⚠️ TEST 5 ERROR: %', SQLERRM;
END $$;
*/

-- ============================================================================
-- RESUMEN DE TRIGGERS INSTALADOS
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════════════════════════════════╗';
    RAISE NOTICE '║           FASE 2: TRIGGERS CRÍTICOS INSTALADOS                     ║';
    RAISE NOTICE '╚════════════════════════════════════════════════════════════════════╝';
    RAISE NOTICE '';
    RAISE NOTICE '✅ 1. trg_plani_auto_horarios';
    RAISE NOTICE '   → Auto-completa hora_inicio, hora_fin, cant_horas desde turnos';
    RAISE NOTICE '   → Tabla: planificacion';
    RAISE NOTICE '   → Cuándo: BEFORE INSERT (si hora_inicio IS NULL)';
    RAISE NOTICE '';
    RAISE NOTICE '✅ 2. trg_prevent_duplicate_vigente';
    RAISE NOTICE '   → Previene convocatorias duplicadas vigentes';
    RAISE NOTICE '   → Tabla: convocatoria';
    RAISE NOTICE '   → Cuándo: BEFORE INSERT (si estado = vigente)';
    RAISE NOTICE '';
    RAISE NOTICE '✅ 3. trg_auto_requiere_certificado';
    RAISE NOTICE '   → Auto-marca si inasistencia requiere certificado';
    RAISE NOTICE '   → Tabla: inasistencias';
    RAISE NOTICE '   → Cuándo: BEFORE INSERT (si requiere_certificado IS NULL)';
    RAISE NOTICE '';
    RAISE NOTICE '📋 PRÓXIMOS PASOS:';
    RAISE NOTICE '   1. Descomentar y ejecutar tests funcionales (línea 195)';
    RAISE NOTICE '   2. Cargar datos de prueba';
    RAISE NOTICE '   3. Validar funcionamiento con casos reales';
    RAISE NOTICE '   4. (Opcional) Agregar triggers secundarios en FASE 3';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- TRIGGERS SECUNDARIOS (FASE 3 - OPCIONAL)
-- ============================================================================
/*
Los siguientes triggers pueden agregarse después si se necesitan:

TRIGGER                           │ Propósito                                  │ Prioridad
──────────────────────────────────┼────────────────────────────────────────────┼──────────
trg_update_fecha_modificacion     │ Auto-actualiza timestamp al modificar      │ Media
trg_registrar_historial_cambio    │ Registra cambios en historial              │ Media
trg_saldo_insert_convocatoria     │ Recalcula saldos al crear convocatoria     │ Alta*
trg_saldo_update_convocatoria     │ Recalcula saldos al actualizar             │ Alta*
trg_saldo_delete_convocatoria     │ Recalcula saldos al eliminar               │ Alta*
trg_asignar_descanso_aprobado     │ Crea convocatoria al aprobar descanso      │ Baja
trg_update_requiere_certificado   │ Actualiza certificado al cambiar motivo    │ Baja
trg_certificado_aprobado          │ Marca inasistencia como justificada        │ Media
trg_certificado_rechazado         │ Evalúa otros certificados                  │ Media
trg_detectar_patron_error         │ Detecta patrones de errores recurrentes   │ Baja
trg_error_resuelto                │ Actualiza timestamp de resolución          │ Baja

* Los triggers de saldos son importantes pero requieren más testing.
  Pueden implementarse manualmente en Python inicialmente.
*/

-- ============================================================================
-- FIN FASE 2: TRIGGERS CRÍTICOS
-- ============================================================================
