-- ============================================================
-- RPC: Matriz de Habilidades al Día (Operativa)
-- ============================================================
-- Devuelve SOLO las capacitaciones YA REALIZADAS (fecha <= hoy)
-- y con asistencia confirmada.
-- Útil para saber quién puede operar qué dispositivo HOY.
-- ============================================================

DROP FUNCTION IF EXISTS rpc_obtener_matriz_habilidades_hoy(INT);

CREATE OR REPLACE FUNCTION rpc_obtener_matriz_habilidades_hoy(anio_filtro INT DEFAULT NULL)
RETURNS TABLE (
    id_dispositivo INT,
    nombre_dispositivo VARCHAR,
    id_agente INT,
    nombre_completo TEXT,
    fecha_mas_reciente DATE
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        disp.id_dispositivo,
        disp.nombre_dispositivo,
        dp.id_agente,
        (dp.nombre || ' ' || dp.apellido) AS nombre_completo,
        MAX(d.fecha) AS fecha_mas_reciente
    FROM dispositivos disp
    JOIN capacitaciones_dispositivos cap_disp ON disp.id_dispositivo = cap_disp.id_dispositivo
    JOIN capacitaciones cap ON cap_disp.id_cap = cap.id_cap
    JOIN capacitaciones_participantes cap_part ON cap.id_cap = cap_part.id_cap
    JOIN datos_personales dp ON cap_part.id_agente = dp.id_agente
    JOIN dias d ON cap.id_dia = d.id_dia
    WHERE dp.activo = true
      AND cap_part.asistio = true
      AND d.fecha <= CURRENT_DATE -- SOLO PASADO/HOY
      AND (anio_filtro IS NULL OR d.anio = anio_filtro)
    GROUP BY 
        disp.id_dispositivo, 
        disp.nombre_dispositivo, 
        dp.id_agente, 
        dp.nombre, 
        dp.apellido
    ORDER BY disp.nombre_dispositivo, dp.apellido;
$$;

GRANT EXECUTE ON FUNCTION rpc_obtener_matriz_habilidades_hoy(int) TO anon, authenticated;
