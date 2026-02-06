-- ============================================================================
-- FIX PERMISOS - Habilitar acceso a las Vistas
-- IMPORTANTE: Ejecutar esto para que la API pueda leer las nuevas vistas
-- ============================================================================

-- 1. Permisos para VISTA 1: Convocatoria del Mes Activo
GRANT SELECT ON vista_convocatoria_mes_activo TO anon, authenticated, service_role;

-- 2. Permisos para VISTA 2: Convocatoria Filtrable
GRANT SELECT ON vista_convocatoria_completa TO anon, authenticated, service_role;

-- 3. Permisos para VISTA 3: Dashboard KPIs
GRANT SELECT ON vista_dashboard_kpis TO anon, authenticated, service_role;

-- 4. Permisos para VISTA 4: Saldos
GRANT SELECT ON vista_saldo_horas_resumen TO anon, authenticated, service_role;

-- 5. Permisos para VISTA 5: Planificación
GRANT SELECT ON vista_planificacion_anio TO anon, authenticated, service_role;

-- VERIFICACIÓN (Opcional)
-- Debería no dar error ahora
-- SELECT * FROM vista_dashboard_kpis LIMIT 1;
