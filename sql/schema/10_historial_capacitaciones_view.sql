-- ============================================================================
-- VISTA: HISTORIAL DE CAPACITACIONES (Plana)
-- Módulo: Capacitaciones (Lectura simplificada para Google Sheets)
-- ============================================================================

CREATE OR REPLACE VIEW vista_historial_capacitaciones AS
SELECT
    d.fecha AS fecha_capacitacion,
    disp.id_dispositivo,
    disp.nombre_dispositivo AS dispositivo_capacitado,
    dp.id_agente,
    (dp.apellido || ', ' || dp.nombre) AS residente_capacitado,
    CASE 
        WHEN cp.asistio = TRUE THEN 'Sí'
        WHEN cp.asistio = FALSE THEN 'No'
        ELSE 'Pendiente'
    END AS estado_asistencia
FROM capacitaciones c
JOIN dias d ON c.id_dia = d.id_dia
JOIN capacitaciones_dispositivos cd ON c.id_cap = cd.id_cap
JOIN dispositivos disp ON cd.id_dispositivo = disp.id_dispositivo
JOIN capacitaciones_participantes cp ON c.id_cap = cp.id_cap
JOIN datos_personales dp ON cp.id_agente = dp.id_agente
ORDER BY d.fecha DESC, disp.nombre_dispositivo, dp.apellido;

-- Grants
GRANT SELECT ON vista_historial_capacitaciones TO anon, authenticated, service_role;
