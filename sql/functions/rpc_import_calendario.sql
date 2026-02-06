-- ============================================================================
-- RPC: IMPORTAR CALENDARIO (Bulk Upsert)
-- Recibe un JSON array con objetos {fecha, id_turno, config_raw (string) }
-- Desempaqueta y realiza upserts masivos en una sola transacción.
-- ============================================================================

CREATE OR REPLACE FUNCTION rpc_importar_calendario(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER -- Ejecuta con permisos del creador (postgres), bypass RLS si es necesario para escritura masiva
AS $$
DECLARE
    r_item JSONB;
    v_fecha DATE;
    v_id_turno INTEGER;
    v_config_raw TEXT;
    
    -- Variables para parsing
    v_sub_item TEXT;
    v_parts TEXT[];
    v_id_disp INTEGER;
    v_cupo INTEGER;
    
    v_inserted_count INTEGER := 0;
    v_errors TEXT := '';
BEGIN
    -- Validar que sea un array
    IF payload IS NULL OR jsonb_typeof(payload) != 'array' THEN
        RETURN jsonb_build_object('success', false, 'error', 'El payload debe ser un JSON Array');
    END IF;

    -- Iterar sobre cada elemento del array (Bulk Processing)
    FOR r_item IN SELECT * FROM jsonb_array_elements(payload)
    LOOP
        BEGIN
            v_fecha := (r_item->>'fecha')::DATE;
            v_id_turno := (r_item->>'id_turno')::INTEGER;
            v_config_raw := r_item->>'config_raw';
            
            -- Validación básica
            IF v_fecha IS NULL OR v_id_turno IS NULL OR v_config_raw IS NULL THEN
                CONTINUE; -- Saltar registros inválidos
            END IF;

            -- Lógica de Desempaquetado (Similar al Trigger anterior)
            -- config_raw formato: "1:2, 5, 8:3"
            
            FOREACH v_sub_item IN ARRAY string_to_array(v_config_raw, ',')
            LOOP
                v_sub_item := trim(v_sub_item);
                IF v_sub_item = '' THEN CONTINUE; END IF;
                
                -- Parse "ID:Cupo"
                IF position(':' in v_sub_item) > 0 THEN
                    v_parts := string_to_array(v_sub_item, ':');
                    v_id_disp := v_parts[1]::INTEGER;
                    v_cupo := v_parts[2]::INTEGER;
                ELSE
                    v_id_disp := v_sub_item::INTEGER;
                    v_cupo := 1; -- Default
                END IF;

                -- Insert / Upsert directo a la tabla final
                -- Asumimos que los IDs de dispositivo ya existen. Si no, fallará y capturamos error.
                INSERT INTO calendario_dispositivos (fecha, id_turno, id_dispositivo, cupo_objetivo)
                VALUES (v_fecha, v_id_turno, v_id_disp, v_cupo)
                ON CONFLICT (fecha, id_turno, id_dispositivo) 
                DO UPDATE SET cupo_objetivo = EXCLUDED.cupo_objetivo;
                
                v_inserted_count := v_inserted_count + 1;
            END LOOP;

        EXCEPTION WHEN OTHERS THEN
            v_errors := v_errors || 'Error en ' || v_fecha || '-' || v_id_turno || ': ' || SQLERRM || '; ';
        END;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'inserted_items', v_inserted_count,
        'errors', v_errors
    );
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION rpc_importar_calendario(JSONB) TO anon, authenticated, service_role;
