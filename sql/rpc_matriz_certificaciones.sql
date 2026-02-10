-- ============================================================
-- RPC: Matriz de Certificaciones Agregada
-- ============================================================
-- Devuelve datos pre-agregados para evitar el límite de 1000 registros.
-- En lugar de devolver todas las filas, devuelve solo combinaciones únicas
-- de (dispositivo, agente) con la fecha más reciente.
-- ============================================================

DROP FUNCTION IF EXISTS rpc_obtener_matriz_certificaciones();

CREATE OR REPLACE FUNCTION rpc_obtener_matriz_certificaciones(anio_filtro INT DEFAULT NULL)
RETURNS TABLE (
    id_dispositivo INT,
    nombre_dispositivo VARCHAR,
    id_agente INT,
    nombre_completo TEXT,
    fecha_mas_reciente DATE,
    total_capacitaciones INT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        disp.id_dispositivo,
        disp.nombre_dispositivo,
        dp.id_agente,
        (dp.nombre || ' ' || dp.apellido) AS nombre_completo,
        MAX(d.fecha) AS fecha_mas_reciente,
        COUNT(*)::INT AS total_capacitaciones
    FROM dispositivos disp
    JOIN capacitaciones_dispositivos cap_disp ON disp.id_dispositivo = cap_disp.id_dispositivo
    JOIN capacitaciones cap ON cap_disp.id_cap = cap.id_cap
    JOIN capacitaciones_participantes cap_part ON cap.id_cap = cap_part.id_cap
    JOIN datos_personales dp ON cap_part.id_agente = dp.id_agente
    JOIN dias d ON cap.id_dia = d.id_dia
    WHERE dp.activo = true
      AND cap_part.asistio = true  -- Solo los que asistieron
      AND (anio_filtro IS NULL OR d.anio = anio_filtro) -- Filtro opcional por año
    GROUP BY 
        disp.id_dispositivo, 
        disp.nombre_dispositivo, 
        dp.id_agente, 
        dp.nombre, 
        dp.apellido
    ORDER BY disp.nombre_dispositivo, dp.apellido;
$$;

-- Otorgar permisos
GRANT EXECUTE ON FUNCTION rpc_obtener_matriz_certificaciones(int) TO anon, authenticated;

-- ============================================================
-- Verificación: Esta consulta debería devolver ~800 filas max
-- (23 dispositivos × 35 residentes = 805 combinaciones máximo)
-- ============================================================
-- SELECT count(*) FROM rpc_obtener_matriz_certificaciones();
