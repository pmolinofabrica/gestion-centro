-- INSTRUCCIONES: Copia y pega este script en el "SQL Editor" de tu Panel de Supabase
-- Devuelve un resumen de la estructura actual para validar la "Coordinación"

------- 1. LISTADO DE TABLAS Y REGISTROS -------
SELECT 
    t.table_name AS "Tabla", 
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) AS "Columnas",
    pg_size_pretty(pg_total_relation_size('"' || t.table_schema || '"."' || t.table_name || '"')) AS "Peso"
FROM information_schema.tables t
WHERE t.table_schema = 'public' 
ORDER BY t.table_name;

------- 2. TRIGGERS ACTIVOS (Lógica Automática) -------
SELECT 
    event_object_table AS "Tabla Afectada",
    trigger_name AS "Nombre Trigger",
    event_manipulation AS "Evento",
    action_timing AS "Momento",
    action_statement AS "Acción Ejecutada"
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, event_manipulation;

------- 3. RELACIONES (Foreign Keys) -------
SELECT
    tc.table_name AS "Tabla Origen",
    kcu.column_name AS "Columna Origen",
    ccu.table_name AS "Tabla Destino",
    ccu.column_name AS "Columna Destino"
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public'
ORDER BY tc.table_name;
