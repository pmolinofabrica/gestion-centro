-- ============================================================================
-- VISTAS DE OPTIMIZACIÓN - VERSIÓN CORREGIDA
-- FIX: Removido filtro estado='cumplida', ahora usa solo turno_cancelado
-- Ejecutar en SQL Editor de Supabase
-- ============================================================================

-- ============================================================================
-- VISTA 1: Convocatoria del Mes Activo
-- SIN CAMBIOS (no filtraba por estado)
-- ============================================================================

DROP VIEW IF EXISTS vista_convocatoria_mes_activo;

CREATE VIEW vista_convocatoria_mes_activo AS
SELECT 
    c.id_convocatoria,
    c.id_plani,
    c.id_agente,
    dp.apellido || ', ' || dp.nombre AS agente,
    dp.dni,
    d.fecha AS fecha_turno,
    EXTRACT(YEAR FROM d.fecha)::int AS anio,
    EXTRACT(MONTH FROM d.fecha)::int AS mes,
    t.tipo_turno,
    t.id_turno,
    c.estado,
    c.turno_cancelado,
    c.motivo_cambio,
    p.cant_horas
FROM convocatoria c
JOIN planificacion p ON c.id_plani = p.id_plani
JOIN dias d ON p.id_dia = d.id_dia
JOIN datos_personales dp ON c.id_agente = dp.id_agente
JOIN turnos t ON c.id_turno = t.id_turno
WHERE d.fecha >= date_trunc('month', CURRENT_DATE)
  AND d.fecha < date_trunc('month', CURRENT_DATE) + interval '1 month';

-- ============================================================================
-- VISTA 2: Convocatoria Completa (para filtrar por mes/año)
-- SIN CAMBIOS (no filtraba por estado)
-- ============================================================================

DROP VIEW IF EXISTS vista_convocatoria_completa;

CREATE VIEW vista_convocatoria_completa AS
SELECT 
    c.id_convocatoria,
    c.id_plani,
    c.id_agente,
    dp.apellido || ', ' || dp.nombre AS agente,
    dp.dni,
    d.fecha AS fecha_turno,
    EXTRACT(YEAR FROM d.fecha)::int AS anio,
    EXTRACT(MONTH FROM d.fecha)::int AS mes,
    t.tipo_turno,
    t.id_turno,
    c.estado,
    c.turno_cancelado,
    c.motivo_cambio,
    p.cant_horas
FROM convocatoria c
JOIN planificacion p ON c.id_plani = p.id_plani
JOIN dias d ON p.id_dia = d.id_dia
JOIN datos_personales dp ON c.id_agente = dp.id_agente
JOIN turnos t ON c.id_turno = t.id_turno;

-- ============================================================================
-- VISTA 3: Dashboard KPIs Pre-calculados
-- FIX: Cuenta TODAS las convocatorias, solo excluye turno_cancelado=true
-- ============================================================================

DROP VIEW IF EXISTS vista_dashboard_kpis;

CREATE VIEW vista_dashboard_kpis AS
SELECT 
    EXTRACT(YEAR FROM d.fecha)::int AS anio,
    EXTRACT(MONTH FROM d.fecha)::int AS mes,
    COUNT(DISTINCT p.id_plani) AS turnos_planificados,
    SUM(p.cant_residentes_plan) AS residentes_requeridos,
    -- Turnos cubiertos: convocatorias NO canceladas
    COUNT(DISTINCT c.id_convocatoria) FILTER (
        WHERE c.turno_cancelado IS NULL OR c.turno_cancelado = false
    ) AS turnos_cubiertos,
    SUM(p.cant_horas * p.cant_residentes_plan) AS horas_planificadas,
    -- Horas cumplidas: solo de turnos NO cancelados
    SUM(p.cant_horas) FILTER (
        WHERE c.turno_cancelado IS NULL OR c.turno_cancelado = false
    ) AS horas_cumplidas,
    ROUND(
        COUNT(c.id_convocatoria) FILTER (
            WHERE c.turno_cancelado IS NULL OR c.turno_cancelado = false
        )::numeric / 
        NULLIF(SUM(p.cant_residentes_plan), 0) * 100, 
        1
    ) AS porcentaje_cobertura
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
LEFT JOIN convocatoria c ON c.id_plani = p.id_plani
GROUP BY EXTRACT(YEAR FROM d.fecha), EXTRACT(MONTH FROM d.fecha)
ORDER BY anio DESC, mes DESC;

-- ============================================================================
-- VISTA 4: Saldos en Vivo 
-- FIX: Removido estado='cumplida', ahora solo excluye turno_cancelado=true
-- ============================================================================

DROP VIEW IF EXISTS vista_saldo_horas_resumen;

CREATE VIEW vista_saldo_horas_resumen AS
SELECT 
    c.id_agente,
    dp.apellido || ', ' || dp.nombre AS agente,
    dp.cohorte,
    EXTRACT(YEAR FROM d.fecha)::int AS anio,
    EXTRACT(MONTH FROM d.fecha)::int AS mes,
    COUNT(*) AS turnos_cumplidos,
    SUM(p.cant_horas) AS horas_mes
FROM convocatoria c
JOIN planificacion p ON c.id_plani = p.id_plani
JOIN dias d ON p.id_dia = d.id_dia
JOIN datos_personales dp ON c.id_agente = dp.id_agente
-- SOLO EXCLUIMOS CANCELADOS, no filtramos por estado
WHERE c.turno_cancelado IS NULL OR c.turno_cancelado = false
GROUP BY 
    c.id_agente, 
    dp.apellido, dp.nombre, dp.cohorte,
    EXTRACT(YEAR FROM d.fecha), 
    EXTRACT(MONTH FROM d.fecha)
ORDER BY anio, mes, agente;

-- ============================================================================
-- VISTA 5: Planificación del Año (sin cambios)
-- ============================================================================

DROP VIEW IF EXISTS vista_planificacion_anio;

CREATE VIEW vista_planificacion_anio AS
SELECT 
    p.id_plani,
    p.id_dia,
    d.fecha,
    EXTRACT(YEAR FROM d.fecha)::int AS anio,
    EXTRACT(MONTH FROM d.fecha)::int AS mes,
    d.es_feriado,
    d.descripcion_feriado,
    p.id_turno,
    t.tipo_turno,
    p.cant_residentes_plan,
    p.cant_visit,
    p.hora_inicio,
    p.hora_fin,
    p.cant_horas
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
JOIN turnos t ON p.id_turno = t.id_turno;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    'vista_convocatoria_mes_activo' AS vista,
    (SELECT COUNT(*) FROM vista_convocatoria_mes_activo) AS registros
UNION ALL
SELECT 
    'vista_convocatoria_completa',
    (SELECT COUNT(*) FROM vista_convocatoria_completa)
UNION ALL
SELECT 
    'vista_dashboard_kpis',
    (SELECT COUNT(*) FROM vista_dashboard_kpis)
UNION ALL
SELECT 
    'vista_saldo_horas_resumen',
    (SELECT COUNT(*) FROM vista_saldo_horas_resumen)
UNION ALL
SELECT 
    'vista_planificacion_anio',
    (SELECT COUNT(*) FROM vista_planificacion_anio);
