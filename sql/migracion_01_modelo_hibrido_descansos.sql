-- ============================================================================
-- MIGRACIÓN 01: Modelo Híbrido de Descansos
-- ============================================================================
-- Proyecto: Sistema RRHH - Centro Cultural
-- Autor: Pablo - Data Analyst
-- Fecha: 2025-12-11
-- Versión: 1.0 FINAL
--
-- OBJETIVO:
--   Permitir que la tabla convocatoria soporte descansos mediante id_turno NULL
--   Esto implementa el "Modelo Híbrido" donde:
--   - descansos: tabla de workflow (solicitud → aprobación)
--   - convocatoria con id_turno NULL: descanso operativo asignado
--
-- CAMBIOS:
--   1. convocatoria.id_turno: INTEGER NOT NULL → INTEGER (permite NULL)
--   2. convocatoria.id_plani: INTEGER NOT NULL → INTEGER (permite NULL)
--   3. Triggers de saldos: ignorar registros con id_turno NULL
--   4. Trigger de descansos: crear convocatoria con id_turno = NULL
--
-- IMPACTO:
--   - Datos existentes: preservados completamente
--   - Triggers de saldos: solo cuentan turnos (no descansos)
--   - Foreign Keys: temporalmente desactivadas durante migración
--
-- ROLLBACK:
--   Si algo falla, restaurar desde backup:
--   cp data/gestion_rrhh_PRE_MIGRACION.db data/gestion_rrhh.db
-- ============================================================================

-- Desactivar Foreign Keys temporalmente
PRAGMA foreign_keys = OFF;

-- Iniciar transacción
BEGIN TRANSACTION;

-- ============================================================================
-- FASE 1: PREPARACIÓN
-- ============================================================================

-- Eliminar todos los triggers relacionados con convocatoria
DROP TRIGGER IF EXISTS trg_prevent_duplicate_vigente;
DROP TRIGGER IF EXISTS trg_update_fecha_modificacion;
DROP TRIGGER IF EXISTS trg_registrar_historial_cambio;
DROP TRIGGER IF EXISTS trg_saldo_insert_convocatoria;
DROP TRIGGER IF EXISTS trg_saldo_update_convocatoria;
DROP TRIGGER IF EXISTS trg_saldo_delete_convocatoria;
DROP TRIGGER IF EXISTS trg_asignar_descanso_aprobado;

-- Eliminar índices existentes
DROP INDEX IF EXISTS idx_conv_plani;
DROP INDEX IF EXISTS idx_conv_agente;
DROP INDEX IF EXISTS idx_conv_fecha;
DROP INDEX IF EXISTS idx_conv_estado;
DROP INDEX IF EXISTS idx_conv_agente_fecha_estado;

-- ============================================================================
-- FASE 2: RECREAR TABLA CON SCHEMA CORRECTO
-- ============================================================================

CREATE TABLE convocatoria_new (
    id_convocatoria INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- CAMBIO 1: id_plani ahora permite NULL (para descansos sin planificación)
    id_plani INTEGER,
    
    id_agente INTEGER NOT NULL,
    
    -- CAMBIO 2: id_turno ahora permite NULL (NULL = descanso)
    id_turno INTEGER,
    
    fecha_convocatoria DATE NOT NULL,
    estado VARCHAR(20) DEFAULT 'vigente',
    
    -- Trazabilidad
    id_convocatoria_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    motivo_cambio TEXT,
    usuario_modificacion VARCHAR(100),
    
    -- Foreign Keys
    CONSTRAINT fk_conv_plani FOREIGN KEY (id_plani) 
        REFERENCES planificacion(id_plani),
    CONSTRAINT fk_conv_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE RESTRICT,
    CONSTRAINT fk_conv_turno FOREIGN KEY (id_turno) 
        REFERENCES turnos(id_turno),
    CONSTRAINT fk_conv_origen FOREIGN KEY (id_convocatoria_origen) 
        REFERENCES convocatoria(id_convocatoria),
    
    -- Constraint de estado
    CONSTRAINT chk_estado_conv CHECK (
        estado IN ('vigente', 'historica', 'cancelada', 'cumplida', 'con_inasistencia')
    )
);

-- ============================================================================
-- FASE 3: MIGRAR DATOS
-- ============================================================================

INSERT INTO convocatoria_new (
    id_convocatoria,
    id_plani,
    id_agente,
    id_turno,
    fecha_convocatoria,
    estado,
    id_convocatoria_origen,
    fecha_registro,
    fecha_modificacion,
    motivo_cambio,
    usuario_modificacion
)
SELECT 
    id_convocatoria,
    id_plani,
    id_agente,
    id_turno,
    fecha_convocatoria,
    estado,
    id_convocatoria_origen,
    fecha_registro,
    fecha_modificacion,
    motivo_cambio,
    usuario_modificacion
FROM convocatoria;

-- Verificar que se copiaron todos los datos
-- (El script abortará si los counts no coinciden)
SELECT CASE
    WHEN (SELECT COUNT(*) FROM convocatoria) != (SELECT COUNT(*) FROM convocatoria_new)
    THEN RAISE(ABORT, 'ERROR: No se copiaron todos los registros')
END;

-- ============================================================================
-- FASE 4: REEMPLAZAR TABLA
-- ============================================================================

DROP TABLE convocatoria;
ALTER TABLE convocatoria_new RENAME TO convocatoria;

-- ============================================================================
-- FASE 5: RECREAR ÍNDICES
-- ============================================================================

CREATE INDEX idx_conv_plani ON convocatoria(id_plani);
CREATE INDEX idx_conv_agente ON convocatoria(id_agente);
CREATE INDEX idx_conv_fecha ON convocatoria(fecha_convocatoria);
CREATE INDEX idx_conv_estado ON convocatoria(estado);
CREATE INDEX idx_conv_agente_fecha_estado ON convocatoria(id_agente, fecha_convocatoria, estado);
CREATE INDEX idx_conv_turno ON convocatoria(id_turno);

-- Índice parcial: solo convocatorias con turno (optimización)
CREATE INDEX idx_conv_con_turno ON convocatoria(id_turno) 
WHERE id_turno IS NOT NULL;

-- Índice parcial: solo descansos (optimización)
CREATE INDEX idx_conv_descansos ON convocatoria(id_agente, fecha_convocatoria) 
WHERE id_turno IS NULL;

-- ============================================================================
-- FASE 6: RECREAR TRIGGERS
-- ============================================================================

-- Trigger 1: Prevenir convocatorias duplicadas
CREATE TRIGGER trg_prevent_duplicate_vigente
BEFORE INSERT ON convocatoria
FOR EACH ROW
WHEN NEW.estado = 'vigente'
BEGIN
    SELECT CASE
        WHEN EXISTS (
            SELECT 1 FROM convocatoria
            WHERE id_agente = NEW.id_agente
            AND fecha_convocatoria = NEW.fecha_convocatoria
            AND estado = 'vigente'
        )
        THEN RAISE(ABORT, 'ERROR: El agente ya tiene una convocatoria vigente para esta fecha')
    END;
END;

-- Trigger 2: Auto-actualizar fecha de modificación
CREATE TRIGGER trg_update_fecha_modificacion
AFTER UPDATE ON convocatoria
FOR EACH ROW
WHEN OLD.estado != NEW.estado
BEGIN
    UPDATE convocatoria
    SET fecha_modificacion = CURRENT_TIMESTAMP
    WHERE id_convocatoria = NEW.id_convocatoria;
END;

-- Trigger 3: Registrar historial de cambios
CREATE TRIGGER trg_registrar_historial_cambio
AFTER UPDATE ON convocatoria
FOR EACH ROW
WHEN OLD.id_agente != NEW.id_agente OR OLD.estado != NEW.estado
BEGIN
    INSERT INTO convocatoria_historial (
        id_convocatoria,
        id_agente_anterior,
        id_agente_nuevo,
        tipo_cambio,
        motivo
    )
    VALUES (
        NEW.id_convocatoria,
        OLD.id_agente,
        NEW.id_agente,
        'reasignacion',
        NEW.motivo_cambio
    );
END;

-- Trigger 4: Actualizar saldos al insertar convocatoria
-- NOTA: Solo cuenta horas si id_turno IS NOT NULL (descansos = 0 horas)
CREATE TRIGGER trg_saldo_insert_convocatoria
AFTER INSERT ON convocatoria
FOR EACH ROW
WHEN NEW.estado IN ('confirmada', 'vigente', 'con_inasistencia') AND NEW.id_turno IS NOT NULL
BEGIN
    INSERT INTO saldos (id_agente, mes, anio, horas_mes, horas_anuales)
    VALUES (
        NEW.id_agente,
        CAST(strftime('%m', NEW.fecha_convocatoria) AS INTEGER),
        CAST(strftime('%Y', NEW.fecha_convocatoria) AS INTEGER),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
           AND c.id_turno IS NOT NULL
           AND strftime('%m', c.fecha_convocatoria) = strftime('%m', NEW.fecha_convocatoria)
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria)),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
           AND c.id_turno IS NOT NULL
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria))
    )
    ON CONFLICT(id_agente, mes, anio) DO UPDATE SET
        horas_mes = excluded.horas_mes,
        horas_anuales = excluded.horas_anuales,
        fecha_actualizacion = CURRENT_TIMESTAMP;
END;

-- Trigger 5: Actualizar saldos al cambiar estado
CREATE TRIGGER trg_saldo_update_convocatoria
AFTER UPDATE OF estado ON convocatoria
FOR EACH ROW
WHEN OLD.estado != NEW.estado AND NEW.id_turno IS NOT NULL
BEGIN
    INSERT INTO saldos (id_agente, mes, anio, horas_mes, horas_anuales)
    VALUES (
        NEW.id_agente,
        CAST(strftime('%m', NEW.fecha_convocatoria) AS INTEGER),
        CAST(strftime('%Y', NEW.fecha_convocatoria) AS INTEGER),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
           AND c.id_turno IS NOT NULL
           AND strftime('%m', c.fecha_convocatoria) = strftime('%m', NEW.fecha_convocatoria)
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria)),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
           AND c.id_turno IS NOT NULL
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria))
    )
    ON CONFLICT(id_agente, mes, anio) DO UPDATE SET
        horas_mes = excluded.horas_mes,
        horas_anuales = excluded.horas_anuales,
        fecha_actualizacion = CURRENT_TIMESTAMP;
END;

-- Trigger 6: Actualizar saldos al eliminar convocatoria
CREATE TRIGGER trg_saldo_delete_convocatoria
AFTER DELETE ON convocatoria
FOR EACH ROW
WHEN OLD.id_turno IS NOT NULL
BEGIN
    UPDATE saldos
    SET horas_mes = (
        SELECT COALESCE(SUM(t.cant_horas), 0)
        FROM convocatoria c
        JOIN turnos t ON t.id_turno = c.id_turno
        WHERE c.id_agente = OLD.id_agente
          AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
          AND c.id_turno IS NOT NULL
          AND strftime('%m', c.fecha_convocatoria) = strftime('%m', OLD.fecha_convocatoria)
          AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', OLD.fecha_convocatoria)
    ),
    horas_anuales = (
        SELECT COALESCE(SUM(t.cant_horas), 0)
        FROM convocatoria c
        JOIN turnos t ON t.id_turno = c.id_turno
        WHERE c.id_agente = OLD.id_agente
          AND c.estado IN ('confirmada', 'vigente', 'cumplida', 'con_inasistencia')
          AND c.id_turno IS NOT NULL
          AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', OLD.fecha_convocatoria)
    ),
    fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id_agente = OLD.id_agente
      AND mes = CAST(strftime('%m', OLD.fecha_convocatoria) AS INTEGER)
      AND anio = CAST(strftime('%Y', OLD.fecha_convocatoria) AS INTEGER);
END;

-- ============================================================================
-- FASE 7: DOCUMENTAR MIGRACIÓN
-- ============================================================================

INSERT INTO configuracion (clave, valor, descripcion, tipo_dato, fecha_modificacion)
VALUES 
(
    'migracion_01_modelo_hibrido', 
    datetime('now'), 
    'Migración 01: Modelo híbrido de descansos implementado', 
    'fecha', 
    CURRENT_TIMESTAMP
),
(
    'convocatoria_permite_null_turno', 
    'true', 
    'Tabla convocatoria.id_turno permite NULL (descansos)', 
    'booleano', 
    CURRENT_TIMESTAMP
)
ON CONFLICT(clave) DO UPDATE SET 
    valor = excluded.valor,
    fecha_modificacion = CURRENT_TIMESTAMP;

-- Finalizar transacción
COMMIT;

-- Reactivar Foreign Keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- FASE 8: TRIGGER DE DESCANSOS (fuera de transacción principal)
-- ============================================================================

-- Trigger 7: Auto-crear convocatoria al aprobar descanso
DROP TRIGGER IF EXISTS trg_asignar_descanso_aprobado;

CREATE TRIGGER trg_asignar_descanso_aprobado
AFTER UPDATE OF estado ON descansos
FOR EACH ROW
WHEN NEW.estado = 'asignado' AND OLD.estado != 'asignado'
BEGIN
    -- Crear convocatoria sin turno (id_turno = NULL marca el descanso)
    INSERT INTO convocatoria (
        id_plani,           -- NULL: sin planificación
        id_agente,
        id_turno,           -- NULL: marca como descanso
        fecha_convocatoria,
        estado,
        motivo_cambio,
        fecha_registro
    )
    VALUES (
        NULL,
        NEW.id_agente,
        NULL,
        NEW.dia_solicitado,
        'vigente',
        'Descanso aprobado - Solicitud #' || NEW.id_desc,
        CURRENT_TIMESTAMP
    );
    
    -- Actualizar fecha de respuesta en descansos
    UPDATE descansos
    SET fecha_respuesta = CURRENT_TIMESTAMP
    WHERE id_desc = NEW.id_desc;
END;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
-- Para verificar que todo funcionó:
--   SELECT sql FROM sqlite_master WHERE name='convocatoria';
--   SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='convocatoria';
--   SELECT * FROM configuracion WHERE clave LIKE '%migracion%';
-- ============================================================================
