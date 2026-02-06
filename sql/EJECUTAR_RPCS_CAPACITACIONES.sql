-- ==============================================================================
-- SCRIPT DE EJECUCIÓN: RPCs de Capacitaciones
-- Ejecutar en Supabase SQL Editor
-- ==============================================================================

-- 1. RPC para guardar matriz de dispositivos
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

-- 2. RPC para guardar participantes (SIN columna grupo - no existe en tabla real)
CREATE OR REPLACE FUNCTION rpc_guardar_participantes_grupo(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_cap INT;
    v_id_agente INT;
    v_participantes JSONB;
    v_inserted INT := 0;
BEGIN
    v_id_cap := (payload->>'id_cap')::INT;
    v_participantes := payload->'participantes';

    IF v_id_cap IS NULL THEN
         RETURN jsonb_build_object('success', false, 'message', 'Falta parámetro id_cap');
    END IF;

    -- Eliminar asignaciones previas para esta capacitación
    DELETE FROM capacitaciones_participantes
    WHERE id_cap = v_id_cap;

    -- Insertar nuevos participantes
    FOR v_id_agente IN SELECT * FROM jsonb_array_elements_text(v_participantes)
    LOOP
        INSERT INTO capacitaciones_participantes (id_cap, id_agente)
        VALUES (v_id_cap, v_id_agente::INT)
        ON CONFLICT (id_cap, id_agente) DO NOTHING;
        
        v_inserted := v_inserted + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'message', format('Asignados %s residentes a capacitación %s', v_inserted, v_id_cap)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'message', SQLERRM
    );
END;
$$;

-- Verificar que las funciones se crearon correctamente
SELECT 
    routine_name, 
    routine_type,
    data_type as return_type
FROM information_schema.routines 
WHERE routine_schema = 'public' 
  AND routine_name LIKE 'rpc_%capacit%'
ORDER BY routine_name;
