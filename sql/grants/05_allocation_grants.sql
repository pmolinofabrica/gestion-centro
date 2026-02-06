-- ============================================================================
-- GRANTS: MÓDULO DE ASIGNACIÓN (Allocation)
-- Permisos necesarios para que la API de Supabase (y Google Apps Script)
-- pueda interactuar con las nuevas tablas.
-- ============================================================================

-- 1. Permisos para tabla calendario_dispositivos
GRANT ALL ON TABLE "public"."calendario_dispositivos" TO "anon";
GRANT ALL ON TABLE "public"."calendario_dispositivos" TO "authenticated";
GRANT ALL ON TABLE "public"."calendario_dispositivos" TO "service_role";

GRANT USAGE, SELECT ON SEQUENCE "public"."calendario_dispositivos_id_seq" TO "anon";
GRANT USAGE, SELECT ON SEQUENCE "public"."calendario_dispositivos_id_seq" TO "authenticated";
GRANT USAGE, SELECT ON SEQUENCE "public"."calendario_dispositivos_id_seq" TO "service_role";


-- 2. Permisos para tabla asignaciones
GRANT ALL ON TABLE "public"."asignaciones" TO "anon";
GRANT ALL ON TABLE "public"."asignaciones" TO "authenticated";
GRANT ALL ON TABLE "public"."asignaciones" TO "service_role";

GRANT USAGE, SELECT ON SEQUENCE "public"."asignaciones_id_seq" TO "anon";
GRANT USAGE, SELECT ON SEQUENCE "public"."asignaciones_id_seq" TO "authenticated";
GRANT USAGE, SELECT ON SEQUENCE "public"."asignaciones_id_seq" TO "service_role";


-- 3. (Opcional) Si usas RLS, necesitas políticas explícitas.
-- Por ahora, asumimos que RLS está desactivado o se confía en los GRANTS anteriores si RLS no está activo.
-- Si activas RLS: ALTER TABLE asignaciones ENABLE ROW LEVEL SECURITY;
-- Y luego crear policies.

-- NOTA: Estos comandos deben ejecutarse en el SQL Editor de Supabase.
