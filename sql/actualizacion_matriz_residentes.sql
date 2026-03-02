-- ==============================================================================
-- 1. NUEVA FUNCIÓN: Obtener matriz pre-llenada con convocados
-- ==============================================================================
CREATE OR REPLACE FUNCTION rpc_obtener_convocados_matriz(anio_filtro INT)
RETURNS TABLE (
    id_cap INT,
    id_agente INT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH caps AS (
        SELECT c.id_cap, c.id_dia, c.id_turno, c.grupo
        FROM capacitaciones c
        JOIN dias d ON c.id_dia = d.id_dia
        WHERE EXTRACT(YEAR FROM d.fecha) = anio_filtro
    ),
    plani AS (
        SELECT p.id_plani, p.id_dia, p.id_turno, p.grupo
        FROM planificacion p
        JOIN dias d ON p.id_dia = d.id_dia
        WHERE EXTRACT(YEAR FROM d.fecha) = anio_filtro
    ),
    convs AS (
        SELECT p.id_dia, p.id_turno, p.grupo, c.id_agente
        FROM convocatoria c
        JOIN plani p ON c.id_plani = p.id_plani
    )
    SELECT 
        c.id_cap,
        dp.id_agente
    FROM caps c
    CROSS JOIN datos_personales dp
    LEFT JOIN capacitaciones_participantes cp ON c.id_cap = cp.id_cap AND dp.id_agente = cp.id_agente
    WHERE dp.activo = true AND dp.cohorte = anio_filtro
      AND COALESCE(cp.asistio, 
                 EXISTS(SELECT 1 FROM convs v WHERE v.id_dia = c.id_dia AND v.id_turno = c.id_turno AND (v.grupo = c.grupo OR (v.grupo IS NULL AND c.grupo IS NULL)) AND v.id_agente = dp.id_agente)
          ) = true;
END;
$$;

-- ==============================================================================
-- 2. MODIFICACIÓN: Guardar matriz almacenando ausentes
-- ==============================================================================
CREATE OR REPLACE FUNCTION rpc_guardar_participantes_grupo(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_cap INT;
    item JSONB;
    v_inserted INT := 0;
BEGIN
    v_id_cap := (payload->>'id_cap')::INT;

    IF v_id_cap IS NULL THEN
         RETURN jsonb_build_object('success', false, 'message', 'Falta id_cap');
    END IF;

    FOR item IN SELECT * FROM jsonb_array_elements(payload->'participantes')
    LOOP
        INSERT INTO capacitaciones_participantes (id_cap, id_agente, asistio)
        VALUES (v_id_cap, (item->>'id_agente')::INT, COALESCE((item->>'asistio')::BOOLEAN, FALSE))
        ON CONFLICT (id_cap, id_agente) 
        DO UPDATE SET asistio = EXCLUDED.asistio;
        
        v_inserted := v_inserted + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'message', format('Actualizados %s residentes en la cap %s', v_inserted, v_id_cap)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'message', SQLERRM
    );
END;
$$;
