-- ============================================================================
-- SQL: Migración 02 - Grupos de Escuelas (Por Día)
-- ============================================================================
-- Objetivo: Crear estructura para asignar a los residentes a grupos de 
-- "Mañana" o "Tarde" los Jueves y Viernes (cuando asisten escuelas).
-- Esta estructura es independiente de la tabla de disponibilidad base.
-- ============================================================================

-- --------------------------------------------------------
-- 1. CREACIÓN DE TABLA MATRIZ
-- --------------------------------------------------------
CREATE TABLE public.agentes_grupos_dias (
    id_agente INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    grupo VARCHAR(50) NOT NULL,
    
    -- Restricciones
    CONSTRAINT pk_agentes_grupos_dias PRIMARY KEY (id_agente, dia_semana),
    CONSTRAINT fk_agd_agente FOREIGN KEY (id_agente) REFERENCES public.datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_dia_semana CHECK (dia_semana BETWEEN 1 AND 7), -- ISO 8601: 1=Lunes, 7=Domingo
    CONSTRAINT chk_grupo CHECK (grupo IN ('manana', 'tarde'))
);

-- Comentarios explicativos
COMMENT ON TABLE public.agentes_grupos_dias IS 'Mapa de pertenencia a grupos de escuela clasificados por día de la semana.';
COMMENT ON COLUMN public.agentes_grupos_dias.dia_semana IS 'Basado en ISODOW de Postgres: 1=Lunes, 4=Jueves, 5=Viernes, 7=Domingo.';

-- --------------------------------------------------------
-- 2. SEGURIDAD Y PERMISOS (Cumpliendo estándares locales)
-- --------------------------------------------------------
-- A. Activar RLS por defecto (Linter Compliance)
ALTER TABLE public.agentes_grupos_dias ENABLE ROW LEVEL SECURITY;

-- B. Otorgar permisos al API de Supabase para poder leer/escribir desde Front o GAS si fuera necesario
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.agentes_grupos_dias TO anon, authenticated, service_role;

-- --------------------------------------------------------
-- 3. CREACIÓN DE VISTA DE AUDITORÍA Y PLANIFICACIÓN
-- --------------------------------------------------------
-- Destruimos si existe previamente
DROP VIEW IF EXISTS public.vista_planificacion_escuelas;

CREATE VIEW public.vista_planificacion_escuelas AS
SELECT 
    c.id_convocatoria,
    c.fecha_convocatoria,
    EXTRACT(ISODOW FROM c.fecha_convocatoria)::INTEGER as dia_semana,
    dp.id_agente,
    dp.nombre,
    dp.apellido,
    t.tipo_turno,
    t.descripcion as descripcion_turno,
    COALESCE(agd.grupo, 'sin_asignar') as grupo_escuela,
    -- Validación Visual: Marca si hay incoherencias entre el turno asignado y su grupo de escuela
    CASE 
        WHEN agd.grupo = 'manana' AND lower(t.descripcion) LIKE '%tarde%' THEN 'ALERTA: Grupo Mañana en Turno Tarde'
        WHEN agd.grupo = 'tarde' AND lower(t.descripcion) LIKE '%mañana%' THEN 'ALERTA: Grupo Tarde en Turno Mañana'
        WHEN agd.grupo IS NULL THEN 'Sin grupo asignado ese día'
        ELSE 'OK'
    END as estado_coherencia
FROM public.convocatoria c
JOIN public.datos_personales dp ON c.id_agente = dp.id_agente
LEFT JOIN public.turnos t ON c.id_turno = t.id_turno
LEFT JOIN public.agentes_grupos_dias agd 
    ON c.id_agente = agd.id_agente 
    AND EXTRACT(ISODOW FROM c.fecha_convocatoria)::INTEGER = agd.dia_semana
WHERE 
    -- Filtramos preventivamente para los días que típicamente importan para escuelas (4=Jueves, 5=Viernes)
    EXTRACT(ISODOW FROM c.fecha_convocatoria) IN (4, 5)
    -- Solo miramos el tablero de convocatorias activas (no turnos caídos o históricos)
    AND c.estado IN ('vigente', 'confirmada');

-- A. Asignar creador Invoker (Linter Compliance)
ALTER VIEW public.vista_planificacion_escuelas SET (security_invoker = true);

-- B. Dar permisos de lectura a la Vista
GRANT SELECT ON TABLE public.vista_planificacion_escuelas TO anon, authenticated, service_role;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
