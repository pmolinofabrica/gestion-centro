-- ============================================================================
-- MÓDULO: ASIGNACIONES DE RESIDENTES A DISPOSITIVOS
-- Tabla para registrar la asignación de residentes a dispositivos/turnos
-- ============================================================================

CREATE TABLE asignaciones (
    id SERIAL PRIMARY KEY,
    residente_id INTEGER NOT NULL,
    dispositivo_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    id_turno INTEGER NOT NULL,
    es_doble_turno BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_asig_residente FOREIGN KEY (residente_id) 
        REFERENCES datos_personales(id_agente) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_dispositivo FOREIGN KEY (dispositivo_id) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_turno FOREIGN KEY (id_turno) 
        REFERENCES turnos(id_turno) ON DELETE RESTRICT,
    
    -- Constraint: Un residente no puede tener dos asignaciones al mismo turno/día
    CONSTRAINT uq_asignacion UNIQUE (residente_id, fecha, id_turno)
);

-- ============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================================================

-- Búsqueda por residente (ver todas las asignaciones de un residente)
CREATE INDEX idx_asig_residente ON asignaciones(residente_id);

-- Búsqueda por fecha (ver todas las asignaciones de un día)
CREATE INDEX idx_asig_fecha ON asignaciones(fecha);

-- Búsqueda por dispositivo (ver quiénes están asignados a un dispositivo)
CREATE INDEX idx_asig_dispositivo ON asignaciones(dispositivo_id);

-- Búsqueda por turno
CREATE INDEX idx_asig_turno ON asignaciones(id_turno);

-- Índice parcial para dobles turnos (análisis rápido)
CREATE INDEX idx_asig_doble_turno ON asignaciones(es_doble_turno) 
    WHERE es_doble_turno = TRUE;

-- Índice compuesto para consultas comunes: fecha + turno
CREATE INDEX idx_asig_fecha_turno ON asignaciones(fecha, id_turno);

-- ============================================================================
-- COMENTARIOS
-- ============================================================================

COMMENT ON TABLE asignaciones IS 'Registro de asignaciones de residentes a dispositivos por fecha y turno';
COMMENT ON COLUMN asignaciones.residente_id IS 'FK a datos_personales.id_agente';
COMMENT ON COLUMN asignaciones.dispositivo_id IS 'FK a dispositivos.id_dispositivo';
COMMENT ON COLUMN asignaciones.es_doble_turno IS 'TRUE si el residente ya tiene otro turno ese día';
