-- ==============================================================================
-- SCRIPT: Vista corregida de agentes capacitados
-- Ejecutar en Supabase SQL Editor
-- ==============================================================================

-- Recrear vista sin columna 'grupo' que no existe
DROP VIEW IF EXISTS vista_agentes_capacitados;

CREATE OR REPLACE VIEW vista_agentes_capacitados AS
SELECT 
    disp.id_dispositivo,
    disp.nombre_dispositivo,
    dp.id_agente,
    dp.nombre || ' ' || dp.apellido AS nombre_completo,
    cap.tema AS capacitacion,
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

-- Verificar que la vista funciona
SELECT * FROM vista_agentes_capacitados LIMIT 5;

-- RE-APLICAR PERMISO (Vital después de recrear la vista)
GRANT SELECT ON TABLE vista_agentes_capacitados TO anon, authenticated;
