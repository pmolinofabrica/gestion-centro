-- ============================================================================
-- VISTAS PARA MÓDULO INASISTENCIAS Y CERTIFICADOS
-- Genera vistas optimizadas para consumo desde Google Sheets
-- ============================================================================

-- 1. Vista Inasistencias Completa
-- Útil para descargar historial y filtrar por mes
CREATE OR REPLACE VIEW vista_inasistencias_completa AS
SELECT 
    i.id_inasistencia,
    i.id_agente,
    p.apellido || ', ' || p.nombre AS agente,
    p.dni,
    i.fecha_inasistencia,
    EXTRACT(YEAR FROM i.fecha_inasistencia)::INTEGER AS anio,
    EXTRACT(MONTH FROM i.fecha_inasistencia)::INTEGER AS mes,
    i.motivo,
    i.estado,
    i.requiere_certificado,
    i.observaciones,
    i.fecha_aviso
FROM inasistencias i
JOIN datos_personales p ON i.id_agente = p.id_agente;

-- 2. Vista Certificados Completa
-- Útil para gestión de entrega de certificados
CREATE OR REPLACE VIEW vista_certificados_completa AS
SELECT 
    c.id_certificado,
    c.id_inasistencia,
    c.id_agente,
    p.apellido || ', ' || p.nombre AS agente,
    p.dni,
    c.fecha_entrega_certificado,
    c.fecha_inasistencia_justifica,
    c.tipo_certificado,
    c.estado_certificado,
    c.observaciones
FROM certificados c
JOIN datos_personales p ON c.id_agente = p.id_agente;

-- 3. Vista Resumen Inasistencias (Dashboard)
-- Conteo por motivo y estado para dashboard
CREATE OR REPLACE VIEW vista_dashboard_inasistencias AS
SELECT 
    EXTRACT(YEAR FROM fecha_inasistencia) AS anio,
    EXTRACT(MONTH FROM fecha_inasistencia) AS mes,
    motivo,
    estado,
    COUNT(*) as total
FROM inasistencias
GROUP BY 1, 2, 3, 4;

-- ============================================================================
-- PERMISOS (CRÍTICO PARA API SUPABASE)
-- ============================================================================

GRANT SELECT ON vista_inasistencias_completa TO anon, authenticated, service_role;
GRANT SELECT ON vista_certificados_completa TO anon, authenticated, service_role;
GRANT SELECT ON vista_dashboard_inasistencias TO anon, authenticated, service_role;

-- También asegurar permisos en tablas base para escritura (upsert)
GRANT ALL ON inasistencias TO anon, authenticated, service_role;
GRANT ALL ON certificados TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE inasistencias_id_inasistencia_seq TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE certificados_id_certificado_seq TO anon, authenticated, service_role;
