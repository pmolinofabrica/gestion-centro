-- Query 2: Ver muestra de datos 2026 con joins
SELECT 
    c.id_convocatoria,
    c.fecha_convocatoria,
    c.id_turno,
    c.id_agente,
    c.estado,
    dp.nombre,
    dp.apellido
FROM convocatoria c
LEFT JOIN datos_personales dp ON c.id_agente = dp.id_agente
WHERE EXTRACT(YEAR FROM fecha_convocatoria) = 2026
  AND c.estado = 'vigente'
ORDER BY c.fecha_convocatoria
LIMIT 20;
