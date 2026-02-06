-- Script para marcar Feriados Nacionales Fijos (Argentina) 2025-2026
-- Ejecutar después de populate_dias.sql

-- 2025
UPDATE dias SET es_feriado = true, nombre_feriado = 'Año Nuevo' WHERE fecha = '2025-01-01';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Carnaval' WHERE fecha IN ('2025-03-03', '2025-03-04');
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Memoria' WHERE fecha = '2025-03-24';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Viernes Santo' WHERE fecha = '2025-04-18';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día del Trabajador' WHERE fecha = '2025-05-01';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Revolución de Mayo' WHERE fecha = '2025-05-25';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Paso a la Inmortalidad de Güemes' WHERE fecha = '2025-06-17';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Bandera' WHERE fecha = '2025-06-20';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Independencia' WHERE fecha = '2025-07-09';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Paso a la Inmortalidad de San Martín' WHERE fecha = '2025-08-17';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día del Respeto a la Diversidad Cultural' WHERE fecha = '2025-10-12';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Soberanía Nacional' WHERE fecha = '2025-11-20';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Inmaculada Concepción' WHERE fecha = '2025-12-08';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Navidad' WHERE fecha = '2025-12-25';

-- 2026
UPDATE dias SET es_feriado = true, nombre_feriado = 'Año Nuevo' WHERE fecha = '2026-01-01';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Carnaval' WHERE fecha IN ('2026-02-16', '2026-02-17');
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Memoria' WHERE fecha = '2026-03-24';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Viernes Santo' WHERE fecha = '2026-04-03';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día del Trabajador' WHERE fecha = '2026-05-01';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Revolución de Mayo' WHERE fecha = '2026-05-25';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Bandera' WHERE fecha = '2026-06-20';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Día de la Independencia' WHERE fecha = '2026-07-09';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Inmaculada Concepción' WHERE fecha = '2026-12-08';
UPDATE dias SET es_feriado = true, nombre_feriado = 'Navidad' WHERE fecha = '2026-12-25';
