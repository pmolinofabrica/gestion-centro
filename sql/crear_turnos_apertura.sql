-- ============================================================================
-- CREAR TURNOS 'APERTURA_PUBLICO' PARA LUNES-VIERNES
-- ============================================================================
-- 
-- Problema: Los turnos 'apertura_publico' solo existen para sábados (día 6)
-- Solución: Crear el mismo tipo de turno para lun-vie
-- Impacto: Permite cargar +718 convocatorias adicionales
--
-- Ejecutar: sqlite3 data/gestion_rrhh.db < crear_turnos_apertura.sql
-- ============================================================================

-- Verificar estado actual
SELECT 
    numero_dia_semana,
    CASE numero_dia_semana
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Lunes'
        WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'
        WHEN 6 THEN 'Sábado'
    END as dia_nombre,
    COUNT(*) as cantidad_turnos
FROM turnos
WHERE tipo_turno = 'apertura_publico'
GROUP BY numero_dia_semana
ORDER BY numero_dia_semana;

-- Agregar turnos apertura_publico para lun-vie
INSERT INTO turnos (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas, activo)
VALUES
  (1, 'apertura_publico', '10:00', '14:00', 4.0, 1),  -- Lunes
  (2, 'apertura_publico', '10:00', '14:00', 4.0, 1),  -- Martes
  (3, 'apertura_publico', '10:00', '14:00', 4.0, 1),  -- Miércoles
  (4, 'apertura_publico', '10:00', '14:00', 4.0, 1),  -- Jueves
  (5, 'apertura_publico', '10:00', '14:00', 4.0, 1);  -- Viernes

-- Verificar que se crearon
SELECT 
    numero_dia_semana,
    CASE numero_dia_semana
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Lunes'
        WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'
        WHEN 6 THEN 'Sábado'
    END as dia_nombre,
    tipo_turno,
    hora_inicio,
    hora_fin,
    cant_horas
FROM turnos
WHERE tipo_turno = 'apertura_publico'
ORDER BY numero_dia_semana;

-- Resumen
SELECT 
    '✅ Turnos apertura_publico creados para lun-vie' as resultado,
    COUNT(*) as total_turnos_apertura
FROM turnos
WHERE tipo_turno = 'apertura_publico';
