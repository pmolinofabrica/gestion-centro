-- ============================================================================
-- VISTAS: Modelo híbrido de descansos
-- ============================================================================

-- Vista 1: Asignaciones unificadas
DROP VIEW IF EXISTS vista_asignaciones_dia;

CREATE VIEW vista_asignaciones_dia AS
SELECT 
    c.id_convocatoria,
    c.id_agente,
    dp.nombre || ' ' || dp.apellido as nombre_completo,
    dp.email,
    c.fecha_convocatoria,
    d.numero_dia_semana,
    CASE d.numero_dia_semana
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Lunes'
        WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'
        WHEN 6 THEN 'Sábado'
    END AS dia_semana_nombre,
    CASE 
        WHEN c.id_turno IS NULL THEN 'DESCANSO'
        ELSE t.tipo_turno
    END as tipo_asignacion,
    COALESCE(t.hora_inicio, '--:--') as hora_inicio,
    COALESCE(t.hora_fin, '--:--') as hora_fin,
    COALESCE(t.cant_horas, 0.0) as horas,
    c.estado,
    CASE 
        WHEN c.id_turno IS NULL THEN 1
        ELSE 0
    END as es_descanso
FROM convocatoria c
JOIN datos_personales dp ON c.id_agente = dp.id_agente
JOIN dias d ON c.fecha_convocatoria = d.fecha
LEFT JOIN turnos t ON c.id_turno = t.id_turno
WHERE c.estado IN ('vigente', 'confirmada')
ORDER BY c.fecha_convocatoria, dp.apellido, t.hora_inicio;

-- Vista 2: Descansos completa
DROP VIEW IF EXISTS vista_descansos_completa;

CREATE VIEW vista_descansos_completa AS
SELECT 
    d.id_desc,
    d.id_agente,
    dp.nombre || ' ' || dp.apellido as nombre_completo,
    d.dia_solicitado,
    d.mes_solicitado,
    d.estado as estado_solicitud,
    d.fecha_solicitud,
    d.fecha_respuesta,
    d.observaciones,
    c.id_convocatoria,
    c.estado as estado_convocatoria,
    CASE 
        WHEN d.estado = 'asignado' AND c.id_convocatoria IS NOT NULL THEN 'Aprobado y asignado'
        WHEN d.estado = 'asignado' AND c.id_convocatoria IS NULL THEN 'Aprobado sin convocatoria'
        WHEN d.estado = 'pendiente' THEN 'Pendiente de aprobación'
        WHEN d.estado = 'no_asignado' THEN 'Rechazado'
        ELSE 'Estado desconocido'
    END as estado_completo
FROM descansos d
JOIN datos_personales dp ON d.id_agente = dp.id_agente
LEFT JOIN convocatoria c ON 
    c.id_agente = d.id_agente 
    AND c.fecha_convocatoria = d.dia_solicitado
    AND c.id_turno IS NULL
    AND c.estado = 'vigente'
ORDER BY d.fecha_solicitud DESC;

-- Vista 3: Planificación mensual
DROP VIEW IF EXISTS vista_planificacion_mensual;

CREATE VIEW vista_planificacion_mensual AS
SELECT 
    strftime('%Y-%m', c.fecha_convocatoria) as anio_mes,
    dp.id_agente,
    dp.nombre || ' ' || dp.apellido as nombre_completo,
    COUNT(CASE WHEN c.id_turno IS NOT NULL THEN 1 END) as turnos_trabajados,
    COUNT(CASE WHEN c.id_turno IS NULL THEN 1 END) as descansos,
    SUM(COALESCE(t.cant_horas, 0)) as total_horas_mes
FROM convocatoria c
JOIN datos_personales dp ON c.id_agente = dp.id_agente
LEFT JOIN turnos t ON c.id_turno = t.id_turno
WHERE c.estado IN ('vigente', 'confirmada', 'cumplida')
GROUP BY strftime('%Y-%m', c.fecha_convocatoria), dp.id_agente
ORDER BY anio_mes DESC, dp.apellido;
