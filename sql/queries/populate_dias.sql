-- Script para poblar la tabla 'dias' con fechas para 2025 y 2026
-- Ejecutar en SQL Editor de Supabase

INSERT INTO public.dias (fecha, mes, semana, dia, numero_dia_semana, es_feriado, nombre_feriado, cuatrimestre, anio)
SELECT
	t.fecha::DATE,
	EXTRACT(MONTH FROM t.fecha) AS mes,
	EXTRACT(WEEK FROM t.fecha) AS semana,
	EXTRACT(DAY FROM t.fecha) AS dia,
	EXTRACT(ISODOW FROM t.fecha) AS numero_dia_semana, -- 1=Lunes, 7=Domingo
	false AS es_feriado, -- Se actualizará manualmente después
	NULL AS nombre_feriado,
	CASE 
		WHEN EXTRACT(MONTH FROM t.fecha) BETWEEN 1 AND 4 THEN 1
		WHEN EXTRACT(MONTH FROM t.fecha) BETWEEN 5 AND 8 THEN 2
		ELSE 3
	END AS cuatrimestre,
	EXTRACT(YEAR FROM t.fecha) AS anio
FROM generate_series('2025-01-01'::DATE, '2026-12-31'::DATE, '1 day') AS t(fecha)
ON CONFLICT (fecha) DO NOTHING;

-- Marcar Fines de Semana (Sábados y Domingos) como no laborales por defecto si se desea, 
-- aunque 'es_feriado' suele referirse a festivos nacionales.
-- Aquí solo insertamos la base. Los feriados específicos deben cargarse aparte.

-- Ejemplo para marcar un feriado:
-- UPDATE public.dias SET es_feriado = true, nombre_feriado = 'Año Nuevo' WHERE fecha = '2026-01-01';
