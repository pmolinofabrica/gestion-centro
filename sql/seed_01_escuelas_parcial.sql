-- ============================================================================
-- SQL: Seed de Prueba - Grupos Escuelas
-- ============================================================================
INSERT INTO public.agentes_grupos_dias (id_agente, dia_semana, grupo)
VALUES
    (86, 4, 'manana'),
    (74, 4, 'manana'),
    (102, 4, 'manana'),
    (93, 4, 'manana'),
    (88, 4, 'manana'),
    (104, 4, 'manana'),
    (77, 4, 'manana'),
    (101, 4, 'manana'),
    (90, 4, 'manana'),
    (95, 4, 'manana'),
    (91, 4, 'manana'),
    (75, 4, 'tarde'),
    (82, 4, 'tarde'),
    (80, 4, 'tarde'),
    (70, 4, 'tarde'),
    (76, 4, 'tarde'),
    (84, 4, 'tarde'),
    (78, 4, 'tarde'),
    (96, 4, 'tarde'),
    (86, 5, 'manana'),
    (74, 5, 'manana'),
    (102, 5, 'manana'),
    (75, 5, 'manana'),
    (82, 5, 'manana'),
    (88, 5, 'manana'),
    (104, 5, 'manana'),
    (70, 5, 'manana'),
    (84, 5, 'manana'),
    (105, 5, 'manana'),
    (90, 5, 'manana'),
    (95, 5, 'manana'),
    (91, 5, 'manana'),
    (80, 5, 'tarde'),
    (76, 5, 'tarde'),
    (78, 5, 'tarde'),
    (96, 5, 'tarde')
ON CONFLICT (id_agente, dia_semana) 
DO UPDATE SET grupo = EXCLUDED.grupo;
