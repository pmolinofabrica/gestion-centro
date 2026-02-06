-- ============================================================================
-- MÓDULO: ASIGNACIÓN DE RESIDENTES A DISPOSITIVOS
-- Versión Limpia basada en Schema Real de Supabase
-- ============================================================================

-- ============================================================================
-- TABLA 1: calendario_dispositivos (El Menú)
-- Define qué dispositivos están disponibles en cada fecha/turno
-- ============================================================================

CREATE TABLE calendario_dispositivos (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    id_turno INTEGER NOT NULL,
    id_dispositivo INTEGER NOT NULL,
    cupo_objetivo INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_cal_turno FOREIGN KEY (id_turno) 
        REFERENCES turnos(id_turno) ON DELETE RESTRICT,
    CONSTRAINT fk_cal_dispositivo FOREIGN KEY (id_dispositivo) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    
    -- Un dispositivo solo puede estar una vez por fecha/turno
    CONSTRAINT uq_calendario UNIQUE (fecha, id_turno, id_dispositivo)
);

-- Índices para calendario_dispositivos
CREATE INDEX idx_cal_fecha ON calendario_dispositivos(fecha);
CREATE INDEX idx_cal_turno ON calendario_dispositivos(id_turno);
CREATE INDEX idx_cal_dispositivo ON calendario_dispositivos(id_dispositivo);
CREATE INDEX idx_cal_fecha_turno ON calendario_dispositivos(fecha, id_turno);

COMMENT ON TABLE calendario_dispositivos IS 'Menú: qué dispositivos abren en cada fecha/turno';
COMMENT ON COLUMN calendario_dispositivos.cupo_objetivo IS 'Cantidad de residentes objetivo para este dispositivo';

-- ============================================================================
-- TABLA 2: asignaciones (El Registro)
-- Registra qué residente fue asignado a qué dispositivo
-- ============================================================================

CREATE TABLE asignaciones (
    id SERIAL PRIMARY KEY,
    id_agente INTEGER NOT NULL,
    id_dispositivo INTEGER NOT NULL,
    fecha DATE NOT NULL,
    id_turno INTEGER NOT NULL,
    es_doble_turno BOOLEAN DEFAULT FALSE,
    es_capacitacion_servicio BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys (usando nombres reales del schema)
    CONSTRAINT fk_asig_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_dispositivo FOREIGN KEY (id_dispositivo) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_turno FOREIGN KEY (id_turno) 
        REFERENCES turnos(id_turno) ON DELETE RESTRICT,
    
    -- Un agente solo puede tener una asignación por fecha/turno
    CONSTRAINT uq_asignacion UNIQUE (id_agente, fecha, id_turno)
);

-- Índices para asignaciones
CREATE INDEX idx_asig_agente ON asignaciones(id_agente);
CREATE INDEX idx_asig_fecha ON asignaciones(fecha);
CREATE INDEX idx_asig_dispositivo ON asignaciones(id_dispositivo);
CREATE INDEX idx_asig_turno ON asignaciones(id_turno);
CREATE INDEX idx_asig_fecha_turno ON asignaciones(fecha, id_turno);
CREATE INDEX idx_asig_doble_turno ON asignaciones(es_doble_turno) 
    WHERE es_doble_turno = TRUE;

COMMENT ON TABLE asignaciones IS 'Registro de asignaciones de residentes a dispositivos';
COMMENT ON COLUMN asignaciones.id_agente IS 'FK a datos_personales.id_agente';
COMMENT ON COLUMN asignaciones.es_doble_turno IS 'TRUE si el residente ya tiene otro turno ese día';
COMMENT ON COLUMN asignaciones.es_capacitacion_servicio IS 'TRUE si el residente no tiene capacitación formal (aprende en servicio)';

-- ============================================================================
-- ALTER TABLE: Agregar columna es_capacitacion_servicio (si la tabla ya existe)
-- Ejecutar solo si la tabla asignaciones ya fue creada previamente
-- ============================================================================

-- ALTER TABLE asignaciones 
--     ADD COLUMN IF NOT EXISTS es_capacitacion_servicio BOOLEAN DEFAULT FALSE;

-- CREATE INDEX IF NOT EXISTS idx_asig_cap_servicio ON asignaciones(es_capacitacion_servicio) 
--     WHERE es_capacitacion_servicio = TRUE;
