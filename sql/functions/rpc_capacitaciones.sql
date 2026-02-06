-- ==============================================================================
-- FASE 1: MIGRACION DE SCHEMA (planificacion → capacitaciones)
-- ==============================================================================

-- 1.1 Agregar columna 'grupo' a planificacion
ALTER TABLE planificacion 
ADD COLUMN IF NOT EXISTS grupo VARCHAR(10) DEFAULT NULL;

-- 1.2 Eliminar constraint UNIQUE antiguo (si existe)
ALTER TABLE planificacion 
DROP CONSTRAINT IF EXISTS uq_plani_dia_turno;

-- 1.3 Crear nuevo constraint UNIQUE con grupo
ALTER TABLE planificacion 
ADD CONSTRAINT uq_plani_dia_turno_grupo UNIQUE (id_dia, id_turno, grupo);

-- 1.4 Agregar columna 'id_turno' a capacitaciones para normalización
ALTER TABLE capacitaciones
ADD COLUMN IF NOT EXISTS id_turno INTEGER REFERENCES turnos(id_turno);

-- 1.5 Crear constraint UNIQUE en capacitaciones para evitar duplicados
ALTER TABLE capacitaciones 
ADD CONSTRAINT uq_capacitaciones_dia_turno_grupo UNIQUE (id_dia, id_turno, grupo);

-- 1.6 Eliminar vista que depende de columnas obsoletas
DROP VIEW IF EXISTS vista_agentes_capacitados;

-- 1.7 Eliminar columnas obsoletas de capacitaciones_participantes
ALTER TABLE capacitaciones_participantes
DROP COLUMN IF EXISTS aprobado,
DROP COLUMN IF EXISTS certificado,
DROP COLUMN IF EXISTS calificacion,
DROP COLUMN IF EXISTS fecha_inscripcion;

-- 1.8 Recrear vista_agentes_capacitados con schema actualizado
CREATE OR REPLACE VIEW vista_agentes_capacitados AS
SELECT 
    disp.id_dispositivo,
    disp.nombre_dispositivo,
    dp.id_agente,
    dp.nombre || ' ' || dp.apellido AS nombre_completo,
    cap.tema AS capacitacion,
    cap.grupo,
    cap_part.asistio,
    d.fecha AS fecha_capacitacion,
    CASE 
        WHEN cap_part.asistio = true THEN 'CAPACITADO'
        ELSE 'NO ASISTIÓ'
    END AS estado_capacitacion
FROM dispositivos disp
JOIN capacitaciones_dispositivos cap_disp ON disp.id_dispositivo = cap_disp.id_dispositivo
JOIN capacitaciones cap ON cap_disp.id_cap = cap.id_cap
JOIN capacitaciones_participantes cap_part ON cap.id_cap = cap_part.id_cap
JOIN datos_personales dp ON cap_part.id_agente = dp.id_agente
JOIN dias d ON cap.id_dia = d.id_dia
WHERE dp.activo = true
ORDER BY disp.nombre_dispositivo, dp.apellido;

-- ==============================================================================
-- FASE 1.2: TRIGGER PARA SINCRONIZACION AUTOMATICA
-- ==============================================================================

/**
 * Función trigger: Crear capacitación automáticamente desde planificacion
 * Se ejecuta cuando se inserta un registro en planificacion con grupo definido
 */
CREATE OR REPLACE FUNCTION crear_capacitacion_desde_planificacion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Solo actuar si el grupo está definido (indica que es una capacitación)
    IF NEW.grupo IS NOT NULL THEN
        INSERT INTO capacitaciones (id_dia, id_turno, grupo, coordinador_cap, tema)
        VALUES (
            NEW.id_dia, 
            NEW.id_turno, 
            NEW.grupo,
            1,  -- Coordinador por defecto (ajustar según necesidad)
            'Capacitación Interna'  -- Tema por defecto
        )
        ON CONFLICT (id_dia, id_turno, grupo) DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Crear el trigger
DROP TRIGGER IF EXISTS trg_planificacion_a_capacitaciones ON planificacion;

CREATE TRIGGER trg_planificacion_a_capacitaciones
AFTER INSERT ON planificacion
FOR EACH ROW
EXECUTE FUNCTION crear_capacitacion_desde_planificacion();

-- 1.9 Fase 2: Agregar tiempo en minutos a la relación dispositivos
ALTER TABLE capacitaciones_dispositivos
ADD COLUMN IF NOT EXISTS tiempo_minutos INTEGER DEFAULT 0;

-- ==============================================================================
-- FASE 1.3: FUNCIONES RPC (REMOTE PROCEDURE CALLS)
-- ==============================================================================

/**
 * rpc_guardar_matriz_dispositivos
 * Actualiza la asignación de dispositivos habilitados para una lista de capacitaciones.
 *
 * @param payload JSONB: Array de objetos { "id_cap": int, "id_dispositivo": int, "tiempo": int }
 *
 * Lógica:
 * - Itera sobre el array.
 * - Si tiempo > 0: Inserta/Actualiza en capacitaciones_dispositivos (UPSERT).
 * - Si tiempo <= 0: Elimina de capacitaciones_dispositivos.
 */
CREATE OR REPLACE FUNCTION rpc_guardar_matriz_dispositivos(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    item JSONB;
    v_count INT := 0;
    v_tiempo INT;
BEGIN
    FOR item IN SELECT * FROM jsonb_array_elements(payload)
    LOOP
        v_tiempo := COALESCE((item->>'tiempo')::INT, 0);

        IF v_tiempo > 0 THEN
            INSERT INTO capacitaciones_dispositivos (id_cap, id_dispositivo, tiempo_minutos)
            VALUES ((item->>'id_cap')::INT, (item->>'id_dispositivo')::INT, v_tiempo)
            ON CONFLICT (id_cap, id_dispositivo) 
            DO UPDATE SET tiempo_minutos = EXCLUDED.tiempo_minutos;
        ELSE
            DELETE FROM capacitaciones_dispositivos
            WHERE id_cap = (item->>'id_cap')::INT
              AND id_dispositivo = (item->>'id_dispositivo')::INT;
        END IF;
        
        v_count := v_count + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'message', format('Procesados %s registros en matriz dispositivos', v_count)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'message', SQLERRM
    );
END;
$$;

/**
 * rpc_guardar_participantes_grupo
 * Asigna residentes a una capacitación específica (Grupo).
 *
 * @param payload JSONB: Objeto { 
 *    "id_cap": int, 
 *    "grupo": string, 
 *    "participantes": [id_agente, id_agente...] 
 * }
 *
 * Lógica:
 * - Recibe ID de capacitación y el Grupo (A, B, C...).
 * - Recibe lista completa de IDs de agentes que deben estar en ese grupo.
 * - Estrategia "sync": Elimina asignaciones previas para ese id_cap + grupo, e inserta la nueva lista.
 */
CREATE OR REPLACE FUNCTION rpc_guardar_participantes_grupo(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_cap INT;
    v_grupo TEXT;
    v_id_agente INT;
    v_participantes JSONB;
    v_inserted INT := 0;
BEGIN
    v_id_cap := (payload->>'id_cap')::INT;
    v_grupo := payload->>'grupo';
    v_participantes := payload->'participantes';

    IF v_id_cap IS NULL OR v_grupo IS NULL THEN
         RETURN jsonb_build_object('success', false, 'message', 'Faltan parámetros id_cap o grupo');
    END IF;

    DELETE FROM capacitaciones_participantes
    WHERE id_cap = v_id_cap
      AND grupo = v_grupo;

    FOR v_id_agente IN SELECT * FROM jsonb_array_elements_text(v_participantes)
    LOOP
        INSERT INTO capacitaciones_participantes (id_cap, id_agente, grupo)
        VALUES (v_id_cap, v_id_agente, v_grupo)
        ON CONFLICT (id_cap, id_agente) 
        DO UPDATE SET grupo = EXCLUDED.grupo;
        
        v_inserted := v_inserted + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'message', format('Asignados %s residentes al Grupo %s', v_inserted, v_grupo)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'message', SQLERRM
    );
END;
$$;
