-- SOLUCIÓN "0 RESULTADOS": Desactivar RLS temporalmente
-- Si Supabase tiene RLS (Row Level Security) activado por defecto, los Grants no alcanzan.
-- Se necesitan "Policies". Como es una app interna, podemos desactivar RLS en estas tablas.

-- 1. Tabla Calendario
ALTER TABLE calendario_dispositivos DISABLE ROW LEVEL SECURITY;

-- 2. Tabla Convocatoria
ALTER TABLE convocatoria DISABLE ROW LEVEL SECURITY;

-- 3. Tabla Turnos (si aplica)
ALTER TABLE turnos DISABLE ROW LEVEL SECURITY;

-- NOTA: Si prefieres mantener seguridad, deberias usar:
-- CREATE POLICY "Permitir todo" ON calendario_dispositivos FOR ALL USING (true);
