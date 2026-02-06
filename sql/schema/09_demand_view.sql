-- Vista para exponer la demanda planificada (Personas requeridas)
-- Une DIAS + PLANIFICACION para que GAS pueda consultar por fecha simple.

CREATE OR REPLACE VIEW vista_demanda_planificada AS
SELECT 
    d.fecha,
    p.id_turno,
    t.tipo_turno as nombre_turno,
    p.cant_residentes_plan as cantidad_personas,
    p.plani_notas as notas
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
JOIN turnos t ON p.id_turno = t.id_turno;

-- Grants para que GAS pueda leerla
GRANT SELECT ON vista_demanda_planificada TO anon, authenticated, service_role;
