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
