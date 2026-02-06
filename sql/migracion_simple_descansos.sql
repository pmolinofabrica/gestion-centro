PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- 1. Eliminar triggers
DROP TRIGGER IF EXISTS trg_prevent_duplicate_vigente;
DROP TRIGGER IF EXISTS trg_update_fecha_modificacion;
DROP TRIGGER IF EXISTS trg_registrar_historial_cambio;
DROP TRIGGER IF EXISTS trg_saldo_insert_convocatoria;
DROP TRIGGER IF EXISTS trg_saldo_update_convocatoria;
DROP TRIGGER IF EXISTS trg_saldo_delete_convocatoria;
DROP TRIGGER IF EXISTS trg_asignar_descanso_aprobado;

-- 2. Eliminar índices
DROP INDEX IF EXISTS idx_conv_plani;
DROP INDEX IF EXISTS idx_conv_agente;
DROP INDEX IF EXISTS idx_conv_fecha;
DROP INDEX IF EXISTS idx_conv_estado;
DROP INDEX IF EXISTS idx_conv_agente_fecha_estado;

-- 3. Crear tabla nueva
CREATE TABLE convocatoria_new (
    id_convocatoria INTEGER PRIMARY KEY AUTOINCREMENT,
    id_plani INTEGER,
    id_agente INTEGER NOT NULL,
    id_turno INTEGER,
    fecha_convocatoria DATE NOT NULL,
    estado VARCHAR(20) DEFAULT 'vigente',
    id_convocatoria_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    motivo_cambio TEXT,
    usuario_modificacion VARCHAR(100),
    CONSTRAINT fk_conv_plani FOREIGN KEY (id_plani) REFERENCES planificacion(id_plani),
    CONSTRAINT fk_conv_agente FOREIGN KEY (id_agente) REFERENCES datos_personales(id_agente) ON DELETE RESTRICT,
    CONSTRAINT fk_conv_turno FOREIGN KEY (id_turno) REFERENCES turnos(id_turno),
    CONSTRAINT fk_conv_origen FOREIGN KEY (id_convocatoria_origen) REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT chk_estado_conv CHECK (estado IN ('vigente', 'historica', 'cancelada', 'cumplida', 'con_inasistencia'))
);

-- 4. Copiar datos
INSERT INTO convocatoria_new SELECT * FROM convocatoria;

-- 5. Reemplazar tabla
DROP TABLE convocatoria;
ALTER TABLE convocatoria_new RENAME TO convocatoria;

-- 6. Recrear índices
CREATE INDEX idx_conv_plani ON convocatoria(id_plani);
CREATE INDEX idx_conv_agente ON convocatoria(id_agente);
CREATE INDEX idx_conv_fecha ON convocatoria(fecha_convocatoria);
CREATE INDEX idx_conv_estado ON convocatoria(estado);
CREATE INDEX idx_conv_agente_fecha_estado ON convocatoria(id_agente, fecha_convocatoria, estado);
CREATE INDEX idx_conv_turno ON convocatoria(id_turno);

-- 7. Recrear triggers
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

CREATE TRIGGER trg_update_fecha_modificacion
AFTER UPDATE ON convocatoria
FOR EACH ROW
WHEN OLD.estado != NEW.estado
BEGIN
    UPDATE convocatoria
    SET fecha_modificacion = CURRENT_TIMESTAMP
    WHERE id_convocatoria = NEW.id_convocatoria;
END;

CREATE TRIGGER trg_registrar_historial_cambio
AFTER UPDATE ON convocatoria
FOR EACH ROW
WHEN OLD.id_agente != NEW.id_agente OR OLD.estado != NEW.estado
BEGIN
    INSERT INTO convocatoria_historial (
        id_convocatoria, id_agente_anterior, id_agente_nuevo,
        tipo_cambio, motivo
    )
    VALUES (
        NEW.id_convocatoria, OLD.id_agente, NEW.id_agente,
        'reasignacion', NEW.motivo_cambio
    );
END;

CREATE TRIGGER trg_saldo_insert_convocatoria
AFTER INSERT ON convocatoria
FOR EACH ROW
WHEN NEW.estado IN ('confirmada', 'vigente') AND NEW.id_turno IS NOT NULL
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
           AND c.estado IN ('confirmada', 'vigente', 'cumplida')
           AND c.id_turno IS NOT NULL
           AND strftime('%m', c.fecha_convocatoria) = strftime('%m', NEW.fecha_convocatoria)
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria)),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida')
           AND c.id_turno IS NOT NULL
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria))
    )
    ON CONFLICT(id_agente, mes, anio) DO UPDATE SET
        horas_mes = excluded.horas_mes,
        horas_anuales = excluded.horas_anuales,
        fecha_actualizacion = CURRENT_TIMESTAMP;
END;

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
           AND c.estado IN ('confirmada', 'vigente', 'cumplida')
           AND c.id_turno IS NOT NULL
           AND strftime('%m', c.fecha_convocatoria) = strftime('%m', NEW.fecha_convocatoria)
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria)),
        (SELECT COALESCE(SUM(t.cant_horas), 0)
         FROM convocatoria c
         JOIN turnos t ON t.id_turno = c.id_turno
         WHERE c.id_agente = NEW.id_agente
           AND c.estado IN ('confirmada', 'vigente', 'cumplida')
           AND c.id_turno IS NOT NULL
           AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', NEW.fecha_convocatoria))
    )
    ON CONFLICT(id_agente, mes, anio) DO UPDATE SET
        horas_mes = excluded.horas_mes,
        horas_anuales = excluded.horas_anuales,
        fecha_actualizacion = CURRENT_TIMESTAMP;
END;

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
          AND c.estado IN ('confirmada', 'vigente', 'cumplida')
          AND c.id_turno IS NOT NULL
          AND strftime('%m', c.fecha_convocatoria) = strftime('%m', OLD.fecha_convocatoria)
          AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', OLD.fecha_convocatoria)
    ),
    horas_anuales = (
        SELECT COALESCE(SUM(t.cant_horas), 0)
        FROM convocatoria c
        JOIN turnos t ON t.id_turno = c.id_turno
        WHERE c.id_agente = OLD.id_agente
          AND c.estado IN ('confirmada', 'vigente', 'cumplida')
          AND c.id_turno IS NOT NULL
          AND strftime('%Y', c.fecha_convocatoria) = strftime('%Y', OLD.fecha_convocatoria)
    ),
    fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id_agente = OLD.id_agente
      AND mes = CAST(strftime('%m', OLD.fecha_convocatoria) AS INTEGER)
      AND anio = CAST(strftime('%Y', OLD.fecha_convocatoria) AS INTEGER);
END;

COMMIT;

PRAGMA foreign_keys = ON;

CREATE TRIGGER trg_asignar_descanso_aprobado
AFTER UPDATE OF estado ON descansos
FOR EACH ROW
WHEN NEW.estado = 'asignado' AND OLD.estado != 'asignado'
BEGIN
    INSERT INTO convocatoria (
        id_plani, id_agente, id_turno, fecha_convocatoria, estado, motivo_cambio
    )
    VALUES (
        NULL, NEW.id_agente, NULL, NEW.dia_solicitado, 'vigente',
        'Descanso aprobado - Solicitud #' || NEW.id_desc
    );
    
    UPDATE descansos SET fecha_respuesta = CURRENT_TIMESTAMP WHERE id_desc = NEW.id_desc;
END;
