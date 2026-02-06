-- ============================================================================
-- DIAGNÓSTICO COMPLETO: ESTRUCTURA Y DATOS DE PLANIFICACIÓN
-- Ejecuta este script en el SQL Editor de Supabase
-- ============================================================================

-- 1. ESTRUCTURA DE TABLAS CLAVE
SELECT 
    'ESTRUCTURA: convocatoria' as info,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'convocatoria' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 
    'ESTRUCTURA: planificacion' as info,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'planificacion' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 
    'ESTRUCTURA: dias' as info,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'dias' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 
    'ESTRUCTURA: turnos' as info,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'turnos' AND table_schema = 'public'
ORDER BY ordinal_position;

-- ============================================================================
-- 2. CONTEO DE REGISTROS POR AÑO
-- ============================================================================

SELECT 
    'REGISTROS EN CONVOCATORIA POR AÑO' as info,
    EXTRACT(YEAR FROM fecha_convocatoria) as año,
    COUNT(*) as total_registros,
    COUNT(DISTINCT id_agente) as residentes_unicos,
    COUNT(DISTINCT fecha_convocatoria) as fechas_distintas
FROM convocatoria
GROUP BY EXTRACT(YEAR FROM fecha_convocatoria)
ORDER BY año DESC;

-- ============================================================================
-- 3. MUESTRA DE DATOS 2025 (Primera convocatoria)
-- ============================================================================

SELECT 
    'MUESTRA CONVOCATORIA 2025' as info,
    c.id_convocatoria,
    c.fecha_convocatoria,
    c.id_turno,
    c.id_agente,
    c.estado,
    dp.nombre,
    dp.apellido
FROM convocatoria c
LEFT JOIN datos_personales dp ON c.id_agente = dp.id_agente
WHERE EXTRACT(YEAR FROM fecha_convocatoria) = 2025
  AND c.estado = 'vigente'
ORDER BY c.fecha_convocatoria
LIMIT 10;

-- ============================================================================
-- 4. VERIFICAR RELACIONES (FK a turnos)
-- ============================================================================

SELECT 
    'FK: convocatoria -> turnos' as info,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name as columna_origen,
    ccu.table_name as tabla_destino,
    ccu.column_name as columna_destino
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_name = 'convocatoria'
  AND kcu.column_name = 'id_turno';

-- ============================================================================
-- 5. DATOS COMPLETOS DE UNA CONVOCATORIA (con joins manuales)
-- ============================================================================

SELECT 
    'DATOS COMPLETOS CONVOCATORIA' as info,
    c.id_convocatoria,
    c.fecha_convocatoria,
    c.id_turno,
    t.tipo_turno,
    t.hora_inicio,
    t.hora_fin,
    dp.nombre || ' ' || dp.apellido as residente,
    c.estado
FROM convocatoria c
LEFT JOIN turnos t ON c.id_turno = t.id_turno
LEFT JOIN datos_personales dp ON c.id_agente = dp.id_agente
WHERE EXTRACT(YEAR FROM fecha_convocatoria) = 2025
  AND c.estado = 'vigente'
ORDER BY c.fecha_convocatoria DESC
LIMIT 5;

-- ============================================================================
-- 6. VERIFICAR FORMATO DE FECHAS
-- ============================================================================

SELECT 
    'FORMATO FECHAS' as info,
    fecha_convocatoria,
    fecha_convocatoria::text as fecha_como_texto,
    EXTRACT(YEAR FROM fecha_convocatoria) as año_extraido
FROM convocatoria
WHERE EXTRACT(YEAR FROM fecha_convocatoria) = 2025
LIMIT 5;
