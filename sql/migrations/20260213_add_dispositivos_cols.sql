-- Add new columns to dispositivos table
ALTER TABLE public.dispositivos
ADD COLUMN IF NOT EXISTS piso text,
ADD COLUMN IF NOT EXISTS es_critico boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS cupo_minimo integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS cupo_optimo integer DEFAULT 0;

-- Comment on columns
COMMENT ON COLUMN public.dispositivos.piso IS 'Ubicación / Piso del dispositivo';
COMMENT ON COLUMN public.dispositivos.es_critico IS 'Indica si el dispositivo es crítico para la operación';
COMMENT ON COLUMN public.dispositivos.cupo_minimo IS 'Cantidad mínima de personal requerido';
COMMENT ON COLUMN public.dispositivos.cupo_optimo IS 'Cantidad óptima de personal';
