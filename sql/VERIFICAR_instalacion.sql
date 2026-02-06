-- ============================================================================
-- VERIFICACIÓN: Comprobar que FASE 1 y FASE 2 están correctamente instaladas
-- ============================================================================

-- Test 1: Verificar tablas creadas
SELECT 
    'TABLAS' as tipo,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) >= 19 THEN '✅ OK'
        ELSE '❌ FALTAN ' || (19 - COUNT(*)) || ' TABLAS'
    END as estado
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

-- Test 2: Verificar triggers creados
SELECT 
    'TRIGGERS' as tipo,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) >= 3 THEN '✅ OK'
        ELSE '❌ FALTAN ' || (3 - COUNT(*)) || ' TRIGGERS'
    END as estado
FROM pg_trigger 
WHERE tgname IN (
    'trg_plani_auto_horarios',
    'trg_prevent_duplicate_vigente',
    'trg_auto_requiere_certificado'
);

-- Test 3: Verificar funciones creadas
SELECT 
    'FUNCIONES' as tipo,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) >= 3 THEN '✅ OK'
        ELSE '❌ FALTAN ' || (3 - COUNT(*)) || ' FUNCIONES'
    END as estado
FROM pg_proc 
WHERE proname IN (
    'fn_plani_auto_horarios',
    'fn_prevent_duplicate_vigente',
    'fn_auto_requiere_certificado'
);

-- Test 4: Verificar datos iniciales - configuración
SELECT 
    'CONFIG' as tipo,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) >= 8 THEN '✅ OK'
        ELSE '❌ FALTAN ' || (8 - COUNT(*)) || ' CONFIGS'
    END as estado
FROM configuracion;

-- Test 5: Verificar datos iniciales - turnos
SELECT 
    'TURNOS' as tipo,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) >= 7 THEN '✅ OK'
        ELSE '❌ FALTAN ' || (7 - COUNT(*)) || ' TURNOS'
    END as estado
FROM turnos;

-- Test 6: Detalle de triggers instalados
SELECT 
    tgname as trigger_nombre,
    tgrelid::regclass as tabla,
    CASE tgtype & 2
        WHEN 2 THEN 'BEFORE'
        ELSE 'AFTER'
    END as momento,
    CASE tgtype & 4
        WHEN 4 THEN 'INSERT'
        ELSE 'UPDATE'
    END as evento
FROM pg_trigger 
WHERE tgname LIKE 'trg_%'
AND tgisinternal = FALSE
ORDER BY tgname;

-- Test 7: Verificar tipos de turno instalados
SELECT tipo_turno, descripcion, 
       hora_inicio_default, 
       hora_fin_default, 
       cant_horas_default
FROM turnos
ORDER BY 
    CASE tipo_turno
        WHEN 'mañana' THEN 1
        WHEN 'tarde' THEN 2
        WHEN 'intermedio' THEN 3
        WHEN 'capacitacion' THEN 4
        WHEN 'apertura_publico_corto' THEN 5
        WHEN 'apertura_publico_largo' THEN 6
        WHEN 'descanso' THEN 7
    END;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

SELECT 
    '🎯 SISTEMA LISTO' as mensaje,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') as tablas,
    (SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'trg_%' AND tgisinternal = FALSE) as triggers,
    (SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'fn_%') as funciones,
    (SELECT COUNT(*) FROM configuracion) as configs,
    (SELECT COUNT(*) FROM turnos) as turnos_catalogados;
