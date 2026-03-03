-- Query 3: Verificar que los joins funcionan (el problema real)
SELECT 
    c.id_convocatoria,
    c.fecha_convocatoria,
    c.id_turno,
    c.id_agente,
    c.estado
FROM convocatoria c
WHERE fecha_convocatoria >= '2026-01-01' 
  AND fecha_convocatoria <= '2026-01-31'
  AND c.estado = 'vigente'
LIMIT 10;
