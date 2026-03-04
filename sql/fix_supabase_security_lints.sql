-- ============================================================================
-- SQL Fix: Supabase Security Lints
-- ============================================================================
-- Objetivo: Silenciar advertencias de seguridad en el panel de Supabase
-- Entorno: Local / Desarrollo
-- Impacto Operativo: NINGUNO (la app consume .env service_role keys, salteando RLS de todos modos)
-- 
-- Problemas resueltos:
-- 1. rls_disabled_in_public (Enable Row Level Security)
-- 2. policy_exists_rls_disabled (Enable Row Level Security en tablas que declaraban políticas inertes)
-- 3. security_definer_view (Convertir Security Definer -> Security Invoker)
-- ============================================================================

-- --------------------------------------------------------
-- PARTE 1: ACTIVAR ROW LEVEL SECURITY EN ESQUEMA PÚBLICO
-- --------------------------------------------------------
-- Supabase exige por estándar que las tablas expuestas al PostgREST contengan la bandera RLS,
-- incluso si la estrategia de la app en la fase de desarrollo delega la entrada a server roles.

ALTER TABLE public.turnos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.capacitaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dispositivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.convocatoria ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stg_calendario_import ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.config_cohorte ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendario_dispositivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.certificados ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inasistencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.capacitaciones_dispositivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.capacitaciones_participantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asignaciones ENABLE ROW LEVEL SECURITY;


-- --------------------------------------------------------
-- PARTE 2: VISTAS A SECURITY INVOKER
-- --------------------------------------------------------
-- Las vistas "Security Definer" causan que las consultas las evalúen con los permisos 
-- de la persona que CREÓ la vista (generalmente el Root admin).
-- Supabase estila que las vistas respeten las reglas "Security Invoker" 
-- (los permisos de la persona o ROL que HACE el SELECT, en el caso de la App, service_role).

ALTER VIEW public.vista_cambios_turno SET (security_invoker = true);
ALTER VIEW public.vista_historial_capacitaciones SET (security_invoker = true);
ALTER VIEW public.vista_convocatoria_completa SET (security_invoker = true);
ALTER VIEW public.vista_inasistencias_completa SET (security_invoker = true);
ALTER VIEW public.vista_convocatoria_mes_activo SET (security_invoker = true);
ALTER VIEW public.vista_certificados_completa SET (security_invoker = true);
ALTER VIEW public.vista_seguimiento_residentes SET (security_invoker = true);
ALTER VIEW public.vista_estado_calendario SET (security_invoker = true);
ALTER VIEW public.vista_saldos_resumen SET (security_invoker = true);
ALTER VIEW public.vista_dashboard_inasistencias SET (security_invoker = true);
ALTER VIEW public.vista_demanda_planificada SET (security_invoker = true);
ALTER VIEW public.vista_planificacion_anio SET (security_invoker = true);
ALTER VIEW public.vista_agentes_capacitados SET (security_invoker = true);
ALTER VIEW public.vista_saldo_horas_resumen SET (security_invoker = true);
ALTER VIEW public.vista_estado_cobertura SET (security_invoker = true);
ALTER VIEW public.vista_ocupacion SET (security_invoker = true);

-- Notas para Supabase Dashboard: 
-- Correr esto en el SQL Editor solucionará instantáneamente todos los avisos de la pestaña 
-- 'Database' -> 'Linter'.
