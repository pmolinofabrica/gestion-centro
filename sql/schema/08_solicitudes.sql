-- ============================================================================
-- SQL: Creación de tabla solicitudes (Turnero de Visitas)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.solicitudes (
  -- Identificador único
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  
  -- Datos del formulario
  marca_temporal TIMESTAMPTZ, 
  direccion_email TEXT, 
  
  -- Información Institucional
  tipo_institucion TEXT,
  nombre_institucion TEXT,
  provincia TEXT,
  departamento TEXT,
  agenda_amplia TEXT, 
  quien_coordina TEXT, 
  
  -- Coordinador de Viaje (si aplica)
  nombre_coordinador_viaje TEXT,
  nombre_empresa_organizacion TEXT,
  telefono_contacto_coordinador TEXT,
  email_contacto_coordinador TEXT,
  
  -- Referente del Grupo
  nombre_referente TEXT,
  cargo_institucion TEXT,
  telefono_referente TEXT, 
  telefono_institucion TEXT,
  email_referente TEXT,
  
  -- Preferencias de Visita
  mes_visita_preferido TEXT,
  dias_turnos_preferencia TEXT,
  disponibilidad_llamados TEXT,
  rango_etario TEXT, 
  cantidad_visitantes INTEGER,
  
  -- Requerimientos y Comentarios
  requerimientos_accesibilidad TEXT,
  comentarios_observaciones TEXT, 
  
  -- Campos de Sistema (Lógica del Turnero)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  estado_actual TEXT DEFAULT 'Pendiente',
  coeficiente_calculado NUMERIC(10, 2)
);

-- Comentario para identificar la tabla
COMMENT ON TABLE public.solicitudes IS 'Almacena las respuestas del formulario de solicitud de visitas grupales al Molino.';

-- SEGURIDAD Y PERMISOS
ALTER TABLE public.solicitudes ENABLE ROW LEVEL SECURITY;

-- Otorgar permisos al API de Supabase
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.solicitudes TO anon, authenticated, service_role;
