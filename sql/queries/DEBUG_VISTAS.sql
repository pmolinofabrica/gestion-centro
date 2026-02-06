-- ============================================================================
-- DIAGNÓSTICO DE VISTAS - Ejecutar en SQL Editor de Supabase
-- Usar para verificar por qué las vistas no devuelven datos
-- ============================================================================

-- 1. VERIFICAR QUE LAS VISTAS EXISTEN
SELECT 
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_name LIKE 'vista_%'
ORDER BY table_name;

-- 2. VERIFICAR DATOS EN vista_convocatoria_completa PARA MES 10/2025
SELECT 
    COUNT(*) as total_registros,
    MIN(fecha_turno) as fecha_min,
    MAX(fecha_turno) as fecha_max
FROM vista_convocatoria_completa
WHERE anio = 2025 AND mes = 10;

-- 3. SI EL ANTERIOR DA 0, VERIFICAR DIRECTAMENTE EN TABLAS BASE
-- ¿Hay convocatorias en general?
SELECT COUNT(*) as total_convocatorias FROM convocatoria;

-- ¿Hay planificación con días en octubre 2025?
SELECT COUNT(*) as planificacion_oct_2025
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
WHERE EXTRACT(YEAR FROM d.fecha) = 2025 
  AND EXTRACT(MONTH FROM d.fecha) = 10;

-- 4. VERIFICAR SI HAY CONVOCATORIAS CON ESTADO 'cumplida' (necesario para saldos)
SELECT estado, COUNT(*) as cantidad
FROM convocatoria
GROUP BY estado
ORDER BY cantidad DESC;

-- 5. VERIFICAR vista_dashboard_kpis
SELECT * FROM vista_dashboard_kpis LIMIT 5;

-- 6. VERIFICAR vista_saldo_horas_resumen (solo cuenta cumplidas)
SELECT COUNT(*) as registros_saldos FROM vista_saldo_horas_resumen;

-- Si da 0, probablemente no hay convocatorias con estado = 'cumplida'

-- 7. DIAGNÓSTICO COMPLETO DE JOINS
-- Esto muestra si hay datos pero no se están juntando correctamente
SELECT 
    'convocatoria' as tabla, COUNT(*) as registros FROM convocatoria
UNION ALL
SELECT 'planificacion', COUNT(*) FROM planificacion
UNION ALL
SELECT 'dias', COUNT(*) FROM dias
UNION ALL
SELECT 'datos_personales', COUNT(*) FROM datos_personales
UNION ALL
SELECT 'turnos', COUNT(*) FROM turnos;

-- 8. VERIFICAR SI LOS JOINS FUNCIONAN
-- Si esto da datos, las vistas deberían funcionar
SELECT 
    c.id_convocatoria,
    c.id_agente,
    p.id_plani,
    d.fecha,
    t.tipo_turno
FROM convocatoria c
JOIN planificacion p ON c.id_plani = p.id_plani
JOIN dias d ON p.id_dia = d.id_dia
JOIN turnos t ON c.id_turno = t.id_turno
JOIN datos_personales dp ON c.id_agente = dp.id_agente
LIMIT 5;
