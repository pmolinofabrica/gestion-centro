-- ============================================================================
-- DAMA IMPLEMENTATION V1: Cohort Config & Improved Views
-- ============================================================================

-- 1. Create CONFIG_COHORTE Table
-- "Single Source of Truth" for yearly settings
CREATE TABLE IF NOT EXISTS public.config_cohorte (
    anio INTEGER PRIMARY KEY,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    horas_semanales_requeridas INTEGER DEFAULT 12,
    activo BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Insert defaults for 2025 and 2026
INSERT INTO public.config_cohorte (anio, fecha_inicio, fecha_fin, horas_semanales_requeridas, activo)
VALUES 
    (2025, '2025-02-15', '2025-12-31', 12, true),
    (2026, '2026-02-15', '2026-12-31', 12, false)
ON CONFLICT (anio) DO NOTHING;

-- ============================================================================
-- DATA MIGRATION: Fix fecha_alta for 2025 cohort residents
-- (Only needed once, safe to re-run)
-- ============================================================================
UPDATE datos_personales
SET fecha_alta = '2025-02-15'::date
WHERE cohorte = 2025 
  AND (fecha_alta IS NULL OR fecha_alta > '2025-12-31');

-- ============================================================================
-- 1b. Create TARDANZAS Table (Separate from Inasistencias)
-- Cycle-based tracking: resets every 6 tardanzas
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.tardanzas (
    id_tardanza SERIAL PRIMARY KEY,
    id_agente INT NOT NULL REFERENCES datos_personales(id_agente),
    id_convocatoria INT REFERENCES convocatoria(id_convocatoria), -- Turno afectado
    fecha DATE NOT NULL,
    minutos_atraso INT, -- Opcional: cuántos minutos tarde
    ciclo_numero INT DEFAULT 1, -- 1=primeras 6, 2=segundas 6, etc.
    posicion_en_ciclo INT DEFAULT 1, -- 1-6 dentro del ciclo
    accion_aplicada TEXT CHECK (accion_aplicada IN ('descuento_imprevisto', 'descuento_jornada', NULL)),
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_tardanzas_agente ON public.tardanzas(id_agente);
CREATE INDEX IF NOT EXISTS idx_tardanzas_fecha ON public.tardanzas(fecha);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.tardanzas TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.tardanzas_id_tardanza_seq TO anon, authenticated;

-- ============================================================================
-- 2. View: VISTA_SALDOS_RESUMEN
-- Calculates targets dynamically based on config_cohorte AND agent start/end dates
-- ============================================================================
-- ============================================================================

-- ============================================================================
-- 2. View: VISTA_SALDOS_RESUMEN
-- Calculates targets dynamically based on config_cohorte AND agent start/end dates
-- ============================================================================

DROP VIEW IF EXISTS public.vista_saldos_resumen;
CREATE OR REPLACE VIEW public.vista_saldos_resumen AS
WITH cohorte_info AS (
    SELECT * FROM public.config_cohorte WHERE activo = true LIMIT 1
),
agente_cronograma AS (
    -- Determine effective start/end dates for each agent within the cohort
    SELECT 
        dp.id_agente,
        dp.apellido,
        dp.nombre,
        dp.fecha_alta,
        dp.fecha_baja,
        ci.anio,
        ci.horas_semanales_requeridas,
        -- Valid Start: Later of Cohort Start or Agent Start
        GREATEST(ci.fecha_inicio, COALESCE(dp.fecha_alta, ci.fecha_inicio)) as fecha_inicio_efectiva,
        -- Valid End: Earlier of Cohort End or Agent End (if exists)
        LEAST(ci.fecha_fin, COALESCE(dp.fecha_baja, ci.fecha_fin)) as fecha_fin_efectiva
    FROM public.datos_personales dp
    CROSS JOIN cohorte_info ci
    WHERE dp.activo = true OR (dp.fecha_baja >= ci.fecha_inicio) -- Include inactive if they worked in this cohort
),
meses_calculo AS (
    -- Generate all months for the active year
    SELECT generate_series(1, 12) as mes
),
horas_trabajadas AS (
    SELECT 
        c.id_agente,
        EXTRACT(MONTH FROM d.fecha) as mes,
        EXTRACT(YEAR FROM d.fecha) as anio,
        SUM(p.cant_horas) as horas_cumplidas,
        COUNT(CASE WHEN c.turno_cancelado THEN 1 END) as turnos_cancelados
    FROM public.convocatoria c
    JOIN public.planificacion p ON c.id_plani = p.id_plani
    JOIN public.dias d ON p.id_dia = d.id_dia
    WHERE c.turno_cancelado IS FALSE
    GROUP BY c.id_agente, EXTRACT(MONTH FROM d.fecha), EXTRACT(YEAR FROM d.fecha)
),
inasistencias_count AS (
    SELECT
        id_agente,
        EXTRACT(MONTH FROM fecha_inasistencia) as mes,
        EXTRACT(YEAR FROM fecha_inasistencia) as anio,
        COUNT(*) as total_inasistencias
    FROM public.inasistencias
    GROUP BY id_agente, EXTRACT(MONTH FROM fecha_inasistencia), EXTRACT(YEAR FROM fecha_inasistencia)
)
SELECT 
    ac.id_agente,
    ac.apellido || ', ' || ac.nombre as agente,
    ac.anio,
    mc.mes,
    
    -- Metrics Monthly
    COALESCE(ht.horas_cumplidas, 0) as horas_cumplidas,
    COALESCE(ht.turnos_cancelados, 0) as turnos_cancelados,
    COALESCE(ic.total_inasistencias, 0) as inasistencias_mes,
    
    -- Target Monthly Calculation
    -- If month is outside effective range, target = 0
    -- Else, calculate days in that month overlap / 7 * weekly hours
    ROUND(
        CASE 
            WHEN MAKE_DATE(ac.anio::int, mc.mes::int, 1) > ac.fecha_fin_efectiva THEN 0
            WHEN (MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date < ac.fecha_inicio_efectiva THEN 0
            ELSE 
                ((LEAST((MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date, ac.fecha_fin_efectiva::date) - 
                  GREATEST(MAKE_DATE(ac.anio::int, mc.mes::int, 1)::date, ac.fecha_inicio_efectiva::date) + 1
                ) / 7.0) * ac.horas_semanales_requeridas
        END::numeric
    , 1) as horas_objetivo_mes,
    
    -- Monthly Balance
    (COALESCE(ht.horas_cumplidas, 0) - 
     ROUND(
        CASE 
            WHEN MAKE_DATE(ac.anio::int, mc.mes::int, 1) > ac.fecha_fin_efectiva THEN 0
            WHEN (MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date < ac.fecha_inicio_efectiva THEN 0
            ELSE 
                ((LEAST((MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date, ac.fecha_fin_efectiva::date) - 
                  GREATEST(MAKE_DATE(ac.anio::int, mc.mes::int, 1)::date, ac.fecha_inicio_efectiva::date) + 1
                ) / 7.0) * ac.horas_semanales_requeridas
        END::numeric
    , 1)) as saldo_mensual,

    -- Window Functions for Accumulates (Running Totals)
    SUM(COALESCE(ht.horas_cumplidas, 0)) OVER (PARTITION BY ac.id_agente ORDER BY mc.mes) as horas_cumplidas_acumuladas,
    
    SUM(ROUND(
        CASE 
            WHEN MAKE_DATE(ac.anio::int, mc.mes::int, 1) > ac.fecha_fin_efectiva THEN 0
            WHEN (MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date < ac.fecha_inicio_efectiva THEN 0
            ELSE 
                ((LEAST((MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date, ac.fecha_fin_efectiva::date) - 
                  GREATEST(MAKE_DATE(ac.anio::int, mc.mes::int, 1)::date, ac.fecha_inicio_efectiva::date) + 1
                ) / 7.0) * ac.horas_semanales_requeridas
        END::numeric, 1)) OVER (PARTITION BY ac.id_agente ORDER BY mc.mes) as horas_objetivo_acumuladas,

    (SUM(COALESCE(ht.horas_cumplidas, 0)) OVER (PARTITION BY ac.id_agente ORDER BY mc.mes) - 
     SUM(ROUND(
        CASE 
            WHEN MAKE_DATE(ac.anio::int, mc.mes::int, 1) > ac.fecha_fin_efectiva THEN 0
            WHEN (MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date < ac.fecha_inicio_efectiva THEN 0
            ELSE 
                ((LEAST((MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date, ac.fecha_fin_efectiva::date) - 
                  GREATEST(MAKE_DATE(ac.anio::int, mc.mes::int, 1)::date, ac.fecha_inicio_efectiva::date) + 1
                ) / 7.0) * ac.horas_semanales_requeridas
        END::numeric, 1)) OVER (PARTITION BY ac.id_agente ORDER BY mc.mes)) as saldo_acumulado

FROM agente_cronograma ac
CROSS JOIN meses_calculo mc
LEFT JOIN horas_trabajadas ht ON ac.id_agente = ht.id_agente AND ac.anio = ht.anio AND mc.mes::int = ht.mes
LEFT JOIN inasistencias_count ic ON ac.id_agente = ic.id_agente AND ac.anio = ic.anio AND mc.mes::int = ic.mes
-- Filter: Only show months within the effective period
WHERE MAKE_DATE(ac.anio::int, mc.mes::int, 1) <= ac.fecha_fin_efectiva
  AND (MAKE_DATE(ac.anio::int, mc.mes::int, 1) + INTERVAL '1 month' - INTERVAL '1 day')::date >= ac.fecha_inicio_efectiva
ORDER BY ac.id_agente, mc.mes;

-- ============================================================================
-- 3. View: VISTA_SEGUIMIENTO_RESIDENTES
-- Per Resident summary with dynamic turn types via JSON
-- ============================================================================

DROP VIEW IF EXISTS public.vista_dashboard_kpis;
DROP VIEW IF EXISTS public.vista_seguimiento_residentes;

CREATE OR REPLACE VIEW public.vista_seguimiento_residentes AS
WITH cohorte_info AS (SELECT * FROM public.config_cohorte WHERE activo = true LIMIT 1),
-- Base query: all non-cancelled convocatorias for the active year
convocatorias_base AS (
    SELECT 
        c.id_convocatoria,
        c.id_agente,
        EXTRACT(YEAR FROM d.fecha)::int as anio,
        EXTRACT(MONTH FROM d.fecha)::int as mes,
        p.cant_horas,
        COALESCE(t.tipo_turno, 'Sin Asignar') as tipo_turno
    FROM public.convocatoria c
    JOIN public.planificacion p ON c.id_plani = p.id_plani
    JOIN public.dias d ON p.id_dia = d.id_dia
    LEFT JOIN public.turnos t ON c.id_turno = t.id_turno
    WHERE c.turno_cancelado IS FALSE 
      AND EXTRACT(YEAR FROM d.fecha) = (SELECT anio FROM cohorte_info)
),
-- First aggregation: count by agent/month/tipo_turno
turnos_por_tipo AS (
    SELECT 
        id_agente, anio, mes, tipo_turno,
        COUNT(*) as cnt,
        SUM(cant_horas) as horas_tipo
    FROM convocatorias_base
    GROUP BY id_agente, anio, mes, tipo_turno
),
-- Second aggregation: create JSON and calculate totals FROM the counts
resumen_agrupado AS (
    SELECT 
        id_agente,
        anio,
        mes,
        -- Total turns = SUM of counts EXCLUDING descanso
        SUM(cnt) FILTER (WHERE tipo_turno NOT IN ('descanso', 'Descanso')) as turnos_totales,
        -- Total hours = SUM of hours EXCLUDING descanso
        SUM(horas_tipo) FILTER (WHERE tipo_turno NOT IN ('descanso', 'Descanso')) as horas_totales,
        -- JSON breakdown of ALL types (including descanso for visibility)
        jsonb_object_agg(tipo_turno, cnt) as tipos_turno_json
    FROM turnos_por_tipo
    GROUP BY id_agente, anio, mes
),
-- Inasistencias summary (NO tardanzas - those are in separate table now)
inasistencias_resumen AS (
    SELECT
        id_agente,
        EXTRACT(YEAR FROM fecha_inasistencia)::int as anio,
        EXTRACT(MONTH FROM fecha_inasistencia)::int as mes,
        COUNT(*) FILTER (WHERE motivo != 'tardanza') as total_inasis, -- Exclude legacy tardanzas
        COUNT(*) FILTER (WHERE motivo IN ('medico', 'enfermedad')) as inasis_salud,
        COUNT(*) FILTER (WHERE motivo = 'estudio') as inasis_estudio,
        COUNT(*) FILTER (WHERE motivo = 'imprevisto') as inasis_imprevisto
    FROM public.inasistencias
    GROUP BY id_agente, EXTRACT(YEAR FROM fecha_inasistencia), EXTRACT(MONTH FROM fecha_inasistencia)
),
-- Tardanzas from NEW separate table
tardanzas_resumen AS (
    SELECT
        id_agente,
        EXTRACT(YEAR FROM fecha)::int as anio,
        EXTRACT(MONTH FROM fecha)::int as mes,
        COUNT(*) as total_tardanzas,
        MAX(posicion_en_ciclo) as posicion_ciclo_actual -- Current position in cycle (1-6)
    FROM public.tardanzas
    GROUP BY id_agente, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha)
)
SELECT
    ra.anio,
    ra.mes,
    dp.id_agente,
    dp.apellido || ', ' || dp.nombre as agente,
    dp.dni,
    
    COALESCE(ra.turnos_totales, 0) as turnos_totales,
    COALESCE(ra.horas_totales, 0) as horas_totales,
    ra.tipos_turno_json,
    
    COALESCE(tr.total_tardanzas, 0) as tardanzas,
    COALESCE(ir.total_inasis, 0) as total_inasistencias,
    COALESCE(ir.inasis_salud, 0) as inasistencias_salud,
    COALESCE(ir.inasis_estudio, 0) as inasistencias_estudio,
    COALESCE(ir.inasis_imprevisto, 0) as inasistencias_imprevisto
    
FROM resumen_agrupado ra
JOIN public.datos_personales dp ON ra.id_agente = dp.id_agente
LEFT JOIN inasistencias_resumen ir ON ra.id_agente = ir.id_agente AND ra.anio = ir.anio AND ra.mes = ir.mes
LEFT JOIN tardanzas_resumen tr ON ra.id_agente = tr.id_agente AND ra.anio = tr.anio AND ra.mes = tr.mes
ORDER BY ra.anio DESC, ra.mes DESC, dp.apellido ASC;

-- ============================================================================
-- 4. View: VISTA_CAMBIOS_TURNO
-- Audit view for tracking turn changes (Option A: Cancel + New with Link)
-- ============================================================================

DROP VIEW IF EXISTS public.vista_cambios_turno;
CREATE OR REPLACE VIEW public.vista_cambios_turno AS
SELECT 
    c_nuevo.id_convocatoria as id_nuevo,
    c_nuevo.id_convocatoria_origen as id_original,
    
    -- Agente info
    dp.apellido || ', ' || dp.nombre as agente,
    dp.dni,
    
    -- Original turn info
    d_orig.fecha as fecha_original,
    t_orig.tipo_turno as turno_tipo_original,
    c_orig.estado as estado_original,
    
    -- New turn info
    d_nuevo.fecha as fecha_nueva,
    t_nuevo.tipo_turno as turno_tipo_nuevo,
    c_nuevo.estado as estado_nuevo,
    
    -- Audit fields
    c_nuevo.motivo_cambio,
    c_nuevo.fecha_registro,
    c_nuevo.usuario_modificacion
    
FROM public.convocatoria c_nuevo
JOIN public.convocatoria c_orig ON c_nuevo.id_convocatoria_origen = c_orig.id_convocatoria
JOIN public.datos_personales dp ON c_nuevo.id_agente = dp.id_agente
JOIN public.planificacion p_nuevo ON c_nuevo.id_plani = p_nuevo.id_plani
JOIN public.planificacion p_orig ON c_orig.id_plani = p_orig.id_plani
JOIN public.dias d_nuevo ON p_nuevo.id_dia = d_nuevo.id_dia
JOIN public.dias d_orig ON p_orig.id_dia = d_orig.id_dia
JOIN public.turnos t_nuevo ON c_nuevo.id_turno = t_nuevo.id_turno
JOIN public.turnos t_orig ON c_orig.id_turno = t_orig.id_turno
WHERE c_nuevo.id_convocatoria_origen IS NOT NULL
ORDER BY c_nuevo.fecha_registro DESC;

-- ============================================================================
-- 5. PERMISSIONS (Grants)
-- Standard Supabase permissions for new objects
-- ============================================================================

GRANT ALL ON public.config_cohorte TO postgres, service_role;
GRANT SELECT ON public.config_cohorte TO anon, authenticated;

GRANT SELECT ON public.vista_saldos_resumen TO anon, authenticated, service_role;
GRANT SELECT ON public.vista_seguimiento_residentes TO anon, authenticated, service_role;
GRANT SELECT ON public.vista_cambios_turno TO anon, authenticated, service_role;
