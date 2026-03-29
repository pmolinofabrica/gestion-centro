-- ============================================================================
-- MIGRACIÓN SQL: Limpieza y Reconstrucción del Ecosistema de Saldos (App Next.js)
-- ============================================================================

-- 1. LIMPIEZA DE ECOSISTEMA LEGACY
DROP VIEW IF EXISTS vista_saldos_actuales;
DROP VIEW IF EXISTS vista_saldo_horas_live;
DROP VIEW IF EXISTS vista_saldo_horas_resumen;
DROP VIEW IF EXISTS vista_saldos_resumen;
DROP FUNCTION IF EXISTS func_saldo_insert_convocatoria() CASCADE;
DROP FUNCTION IF EXISTS func_saldo_update_convocatoria() CASCADE;
DROP FUNCTION IF EXISTS func_saldo_delete_convocatoria() CASCADE;

-- 2. MODIFICACIÓN DE LA TABLA SALDOS
ALTER TABLE saldos ADD COLUMN IF NOT EXISTS objetivo_mensual_48 NUMERIC DEFAULT 0;
ALTER TABLE saldos ADD COLUMN IF NOT EXISTS objetivo_mensual_12w NUMERIC DEFAULT 0;
ALTER TABLE saldos ADD COLUMN IF NOT EXISTS objetivo_anual_48 NUMERIC DEFAULT 0;
ALTER TABLE saldos ADD COLUMN IF NOT EXISTS objetivo_anual_12w NUMERIC DEFAULT 0;

-- 3. FUNCIÓN RPC PARA CALCULAR SALDOS A DEMANDA (Para Next.js)
CREATE OR REPLACE FUNCTION rpc_calcular_saldos_mes(p_anio INTEGER, p_mes INTEGER)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_semanas_mes NUMERIC;
BEGIN
    -- Calcular la cantidad de semanas exactas en el mes
    v_semanas_mes := EXTRACT(DAY FROM (date_trunc('month', make_date(p_anio, p_mes, 1)) + interval '1 month' - interval '1 day'))::NUMERIC / 7.0;

    -- UPSERT agrupando desde convocatoria
    WITH horas_calculadas AS (
        SELECT
            c.id_agente,
            SUM(t.cant_horas) AS total_horas_mes
        FROM convocatoria c
        JOIN planificacion p ON c.id_plani = p.id_plani
        JOIN dias d ON p.id_dia = d.id_dia
        JOIN turnos t ON p.id_turno = t.id_turno
        WHERE d.anio = p_anio
          AND d.mes = p_mes
          AND c.estado IN ('vigente', 'cumplida')
        GROUP BY c.id_agente
    )
    INSERT INTO saldos (
        id_agente, mes, anio, horas_mes,
        objetivo_mensual_48, objetivo_mensual_12w, fecha_actualizacion
    )
    SELECT
        dp.id_agente,
        p_mes,
        p_anio,
        COALESCE(hc.total_horas_mes, 0),
        48.0,
        (12.0 * v_semanas_mes),
        CURRENT_TIMESTAMP
    FROM datos_personales dp
    LEFT JOIN horas_calculadas hc ON dp.id_agente = hc.id_agente
    WHERE dp.activo = true
    ON CONFLICT (id_agente, mes, anio) DO UPDATE SET
        horas_mes = EXCLUDED.horas_mes,
        objetivo_mensual_48 = EXCLUDED.objetivo_mensual_48,
        objetivo_mensual_12w = EXCLUDED.objetivo_mensual_12w,
        fecha_actualizacion = EXCLUDED.fecha_actualizacion;

    -- Actualizar acumulados anuales (YTD: Year To Date)
    -- Sumamos solo los meses hasta el mes que estamos calculando
    WITH acumulado_anual AS (
        SELECT id_agente, SUM(horas_mes) AS t_horas, SUM(objetivo_mensual_48) AS t_o48, SUM(objetivo_mensual_12w) AS t_o12w
        FROM saldos
        WHERE anio = p_anio AND mes <= p_mes
        GROUP BY id_agente
    )
    UPDATE saldos s SET
        horas_anuales = aa.t_horas,
        objetivo_anual_48 = aa.t_o48,
        objetivo_anual_12w = aa.t_o12w
    FROM acumulado_anual aa
    WHERE s.id_agente = aa.id_agente AND s.anio = p_anio AND s.mes = p_mes;
END;
$$;

-- 4. VISTA ANALÍTICA PARA LOOKER STUDIO / FRONTEND NEXT.JS (DAMA COMPLIANT)
-- Se corrigen las categorías para que sean mutuamente excluyentes (evitar el doble conteo)
CREATE OR REPLACE VIEW vista_dashboard_saldos AS
WITH horas_desglosadas AS (
    SELECT
        c.id_agente,
        d.anio,
        d.mes,
        SUM(CASE WHEN d.numero_dia_semana NOT IN (0, 6) AND t.tipo_turno = 'mañana' THEN t.cant_horas ELSE 0 END) AS horas_manana_semana,
        SUM(CASE WHEN d.numero_dia_semana NOT IN (0, 6) AND t.tipo_turno = 'tarde' THEN t.cant_horas ELSE 0 END) AS horas_tarde_semana,
        SUM(CASE WHEN d.numero_dia_semana IN (0, 6) THEN t.cant_horas ELSE 0 END) AS horas_finde,
        SUM(CASE WHEN d.numero_dia_semana NOT IN (0, 6) AND t.tipo_turno NOT IN ('mañana', 'tarde') THEN t.cant_horas ELSE 0 END) AS horas_otros_semana
    FROM convocatoria c
    JOIN planificacion p ON c.id_plani = p.id_plani
    JOIN dias d ON p.id_dia = d.id_dia
    JOIN turnos t ON p.id_turno = t.id_turno
    WHERE c.estado IN ('vigente', 'cumplida')
    GROUP BY c.id_agente, d.anio, d.mes
)
SELECT
    s.anio,
    s.mes,
    s.id_agente,
    dp.apellido || ', ' || dp.nombre AS residente,
    dp.dni,
    s.horas_mes AS total_horas_convocadas,
    s.objetivo_mensual_48,
    s.objetivo_mensual_12w,
    (s.horas_mes - s.objetivo_mensual_48) AS diferencia_saldo_48,
    (s.horas_mes - s.objetivo_mensual_12w) AS diferencia_saldo_12w,
    s.horas_anuales AS acumulado_anual_horas,
    s.objetivo_anual_48 AS acumulado_anual_obj_48,
    s.objetivo_anual_12w AS acumulado_anual_obj_12w,
    COALESCE(hd.horas_manana_semana, 0) AS horas_manana,
    COALESCE(hd.horas_tarde_semana, 0) AS horas_tarde,
    COALESCE(hd.horas_finde, 0) AS horas_finde,
    COALESCE(hd.horas_otros_semana, 0) AS horas_otros
FROM saldos s
JOIN datos_personales dp ON s.id_agente = dp.id_agente
LEFT JOIN horas_desglosadas hd
  ON s.id_agente = hd.id_agente
 AND s.anio = hd.anio
 AND s.mes = hd.mes;

-- 5. PERMISOS
GRANT EXECUTE ON FUNCTION rpc_calcular_saldos_mes(INTEGER, INTEGER) TO anon, authenticated, service_role;
GRANT SELECT ON vista_dashboard_saldos TO anon, authenticated, service_role;
