-- ============================================================================
-- MIGRACIÓN SQL: Simplificación de la tabla certificados
-- Propósito: Adaptar la tabla para el nuevo flujo de carga desde Google Forms.
-- Se eliminan columnas innecesarias y se agregan las requeridas (fecha_carga).
-- ============================================================================

-- 1. Eliminar la vista que depende de las columnas a eliminar
DROP VIEW IF EXISTS vista_certificados_completa;

-- 2. Modificar la tabla certificados

-- Añadir fecha_carga si no existe
ALTER TABLE certificados ADD COLUMN IF NOT EXISTS fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Eliminar las columnas que ya no nos interesan
ALTER TABLE certificados DROP COLUMN IF EXISTS fecha_entrega_certificado;
ALTER TABLE certificados DROP COLUMN IF EXISTS tipo_certificado;
ALTER TABLE certificados DROP COLUMN IF EXISTS estado_certificado;

-- Nota: Mantengo 'id_inasistencia' porque el trigger de Supabase podría usarlo,
-- pero el formulario nuevo insertará usando id_agente y fecha_inasistencia_justifica
-- y el trigger existente (que mencionaste) se encarga de cruzar los datos y vincularlos.

-- Agregar una restricción UNIQUE para evitar certificados duplicados por agente y día,
-- permitiendo que el UPSERT funcione correctamente en el script de GAS
ALTER TABLE certificados ADD CONSTRAINT uq_certificados_agente_fecha UNIQUE (id_agente, fecha_inasistencia_justifica);


-- 3. Recrear la vista con las columnas actualizadas
CREATE OR REPLACE VIEW vista_certificados_completa AS
SELECT
    c.id_certificado,
    c.id_inasistencia,
    c.id_agente,
    p.apellido || ', ' || p.nombre AS agente,
    p.dni,
    c.fecha_inasistencia_justifica,
    c.fecha_carga,
    c.observaciones
FROM certificados c
JOIN datos_personales p ON c.id_agente = p.id_agente;

-- 4. Reasignar permisos a la vista (por seguridad)
GRANT SELECT ON vista_certificados_completa TO anon, authenticated, service_role;
