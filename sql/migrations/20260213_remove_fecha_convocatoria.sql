-- Remove fecha_convocatoria column from convocatoria table
ALTER TABLE public.convocatoria DROP COLUMN IF EXISTS fecha_convocatoria;
