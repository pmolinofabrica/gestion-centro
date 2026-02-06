-- QUERY SIMPLE: Ver todas las convocatorias con sus fechas
SELECT 
    id_convocatoria,
    fecha_convocatoria,
    EXTRACT(YEAR FROM fecha_convocatoria) as año,
    estado,
    id_agente,
    id_turno
FROM convocatoria
ORDER BY fecha_convocatoria DESC
LIMIT 20;

-- CONTEO POR AÑO Y MES
SELECT 
    EXTRACT(YEAR FROM fecha_convocatoria) as año,
    EXTRACT(MONTH FROM fecha_convocatoria) as mes,
    COUNT(*) as total
FROM convocatoria
GROUP BY año, mes
ORDER BY año DESC, mes DESC;
