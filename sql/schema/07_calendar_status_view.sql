-- ============================================================================
-- VISTA ESTADO CALENDARIO (Planificación vs Realidad)
-- ============================================================================

CREATE OR REPLACE VIEW vista_estado_calendario AS
SELECT 
    d.fecha,
    p.id_turno,
    t.tipo_turno AS nombre_turno,
    COUNT(DISTINCT c.id_dispositivo) AS dispositivos_configurados,
    COUNT(DISTINCT a.id) AS personas_asignadas,
    CASE 
        WHEN COUNT(DISTINCT a.id) > 0 THEN 'ASIGNADO'
        WHEN COUNT(DISTINCT c.id_dispositivo) > 0 THEN 'CONFIGURADO'
        ELSE 'PENDIENTE' 
    END AS estado
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
JOIN turnos t ON p.id_turno = t.id_turno
LEFT JOIN calendario_dispositivos c ON d.fecha = c.fecha AND p.id_turno = c.id_turno
LEFT JOIN asignaciones a ON d.fecha = a.fecha AND p.id_turno = a.id_turno
GROUP BY d.fecha, p.id_turno, t.tipo_turno
ORDER BY d.fecha DESC, p.id_turno ASC;

-- Grants
GRANT SELECT ON vista_estado_calendario TO anon, authenticated, service_role;
