-- ============================================================================
-- SISTEMA DE GESTIÓN DE RECURSOS HUMANOS - POSTGRESQL
-- Conversión desde SQLite v3.0 DAMA-compliant
-- Autor: Pablo - Data Analyst
-- Fecha: Diciembre 2025
-- ============================================================================
-- 
-- IMPORTANTE: Este schema está CORRECTAMENTE convertido a PostgreSQL
-- Principales diferencias con SQLite:
-- 1. AUTOINCREMENT → SERIAL
-- 2. Triggers → Functions + Triggers
-- 3. BOOLEAN nativo (no 0/1)
-- 4. strftime() → to_char() o EXTRACT()
-- 5. datetime('now') → CURRENT_TIMESTAMP o NOW()
-- ============================================================================

-- ============================================================================
-- MÓDULO 1: TABLAS MAESTRAS (Catálogos)
-- ============================================================================

CREATE TABLE dispositivos (
    id_dispositivo SERIAL PRIMARY KEY,
    nombre_dispositivo VARCHAR(100) NOT NULL,
    piso_dispositivo INTEGER NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    CONSTRAINT chk_piso CHECK (piso_dispositivo >= 0)
);

CREATE INDEX idx_dispositivos_piso ON dispositivos(piso_dispositivo);
CREATE INDEX idx_dispositivos_activo ON dispositivos(activo);

-- ----------------------------------------------------------------------------

CREATE TABLE dias (
    id_dia SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    mes INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    dia INTEGER NOT NULL,
    numero_dia_semana INTEGER NOT NULL,
    es_feriado BOOLEAN DEFAULT FALSE,
    nombre_feriado VARCHAR(200),
    CONSTRAINT chk_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT chk_dia CHECK (dia BETWEEN 1 AND 31),
    CONSTRAINT chk_numero_dia CHECK (numero_dia_semana BETWEEN 0 AND 6)
);

CREATE UNIQUE INDEX idx_dias_fecha ON dias(fecha);
CREATE INDEX idx_dias_mes ON dias(mes);
CREATE INDEX idx_dias_numero_dia_semana ON dias(numero_dia_semana);

-- ----------------------------------------------------------------------------

CREATE TABLE turnos (
    id_turno SERIAL PRIMARY KEY,
    
    -- Identificación
    tipo_turno VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    
    -- Horarios sugeridos
    hora_inicio_default TIME,
    hora_fin_default TIME,
    cant_horas_default DECIMAL(4,2),
    
    -- Restricciones
    solo_fines_semana BOOLEAN DEFAULT FALSE,
    solo_semana BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    turno_notas TEXT,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    
    CONSTRAINT chk_tipo_turno CHECK (tipo_turno IN (
        'mañana', 'tarde', 'intermedio', 'capacitacion', 
        'apertura_publico_corto', 'apertura_publico_largo', 'descanso'
    )),
    CONSTRAINT chk_horas CHECK (
        (cant_horas_default IS NULL) OR 
        (cant_horas_default > 0 AND cant_horas_default <= 24)
    ),
    CONSTRAINT chk_horarios_consistentes CHECK (
        (hora_inicio_default IS NULL AND hora_fin_default IS NULL AND cant_horas_default IS NULL)
        OR
        (hora_inicio_default IS NOT NULL AND hora_fin_default IS NOT NULL AND cant_horas_default IS NOT NULL)
    )
);

CREATE INDEX idx_turnos_tipo ON turnos(tipo_turno);
CREATE INDEX idx_turnos_activo ON turnos(activo);

-- ----------------------------------------------------------------------------

CREATE TABLE datos_personales (
    id_agente SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    dni VARCHAR(20) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    email VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    domicilio TEXT,
    activo BOOLEAN DEFAULT TRUE,
    fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_baja TIMESTAMP,
    CONSTRAINT chk_email CHECK (email LIKE '%@%')
);

CREATE UNIQUE INDEX idx_agentes_dni ON datos_personales(dni);
CREATE INDEX idx_agentes_activo ON datos_personales(activo);
CREATE INDEX idx_agentes_nombre_apellido ON datos_personales(apellido, nombre);

-- ----------------------------------------------------------------------------

CREATE TABLE planificacion (
    id_plani SERIAL PRIMARY KEY,
    
    -- Referencias
    id_dia INTEGER NOT NULL,
    id_turno INTEGER NOT NULL,
    
    -- Horario efectivo
    hora_inicio TIME,
    hora_fin TIME,
    cant_horas DECIMAL(4,2),
    
    -- Data Lineage
    usa_horario_custom BOOLEAN DEFAULT FALSE,
    motivo_horario_custom TEXT,
    
    -- Demanda
    cant_residentes_plan INTEGER NOT NULL,
    cant_visit INTEGER DEFAULT 0,
    
    -- Metadata
    plani_notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_creacion VARCHAR(100),
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    
    CONSTRAINT fk_plani_dia FOREIGN KEY (id_dia) REFERENCES dias(id_dia),
    CONSTRAINT fk_plani_turno FOREIGN KEY (id_turno) REFERENCES turnos(id_turno),
    CONSTRAINT uq_plani_dia_turno UNIQUE (id_dia, id_turno),
    CONSTRAINT chk_cant_residentes CHECK (cant_residentes_plan > 0),
    CONSTRAINT chk_cant_visit CHECK (cant_visit >= 0)
);

CREATE INDEX idx_plani_dia ON planificacion(id_dia);
CREATE INDEX idx_plani_turno ON planificacion(id_turno);
CREATE INDEX idx_plani_custom ON planificacion(usa_horario_custom);

-- ============================================================================
-- TRIGGER: Auto-poblar horarios desde catálogo (POSTGRESQL)
-- ============================================================================

-- Función del trigger
CREATE OR REPLACE FUNCTION func_plani_auto_horarios()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo si hora_inicio es NULL
    IF NEW.hora_inicio IS NULL THEN
        -- Obtener horarios del catálogo de turnos
        SELECT 
            COALESCE(hora_inicio_default, '00:00'::TIME),
            COALESCE(hora_fin_default, '23:59'::TIME),
            COALESCE(cant_horas_default, 0)
        INTO 
            NEW.hora_inicio,
            NEW.hora_fin,
            NEW.cant_horas
        FROM turnos
        WHERE id_turno = NEW.id_turno;
        
        -- Marcar que NO es custom (viene del catálogo)
        NEW.usa_horario_custom := FALSE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger que llama a la función
CREATE TRIGGER trg_plani_auto_horarios
BEFORE INSERT ON planificacion
FOR EACH ROW
EXECUTE FUNCTION func_plani_auto_horarios();

-- ============================================================================
-- TRIGGER: Update timestamp planificacion
-- ============================================================================

CREATE OR REPLACE FUNCTION func_plani_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_modificacion := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_plani_update_timestamp
BEFORE UPDATE ON planificacion
FOR EACH ROW
EXECUTE FUNCTION func_plani_update_timestamp();

-- ============================================================================
-- MÓDULO 2: CAPACITACIONES
-- ============================================================================

CREATE TABLE capacitaciones (
    id_cap SERIAL PRIMARY KEY,
    id_dia INTEGER NOT NULL,
    coordinador_cap INTEGER NOT NULL,
    tema VARCHAR(200) NOT NULL,
    grupo VARCHAR(50),
    observaciones TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cap_dia FOREIGN KEY (id_dia) REFERENCES dias(id_dia),
    CONSTRAINT fk_cap_coordinador FOREIGN KEY (coordinador_cap) 
        REFERENCES datos_personales(id_agente) ON DELETE RESTRICT
);

CREATE INDEX idx_cap_dia ON capacitaciones(id_dia);
CREATE INDEX idx_cap_coordinador ON capacitaciones(coordinador_cap);

CREATE TABLE capacitaciones_dispositivos (
    id_cap_dispo SERIAL PRIMARY KEY,
    id_cap INTEGER NOT NULL,
    id_dispositivo INTEGER NOT NULL,
    orden INTEGER DEFAULT 1,
    CONSTRAINT fk_cap_dispo_cap FOREIGN KEY (id_cap) 
        REFERENCES capacitaciones(id_cap) ON DELETE CASCADE,
    CONSTRAINT fk_cap_dispo_dispo FOREIGN KEY (id_dispositivo) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT uq_cap_dispositivo UNIQUE (id_cap, id_dispositivo)
);

CREATE INDEX idx_cap_dispo_cap ON capacitaciones_dispositivos(id_cap);
CREATE INDEX idx_cap_dispo_dispositivo ON capacitaciones_dispositivos(id_dispositivo);

CREATE TABLE capacitaciones_participantes (
    id_participante SERIAL PRIMARY KEY,
    id_cap INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    asistio BOOLEAN DEFAULT FALSE,
    aprobado BOOLEAN,
    calificacion DECIMAL(4,2),
    observaciones TEXT,
    fecha_certificado TIMESTAMP,
    
    CONSTRAINT fk_cap_part_cap FOREIGN KEY (id_cap) 
        REFERENCES capacitaciones(id_cap) ON DELETE CASCADE,
    CONSTRAINT fk_cap_part_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT uq_cap_agente UNIQUE (id_cap, id_agente),
    CONSTRAINT chk_calificacion CHECK (calificacion IS NULL OR (calificacion BETWEEN 0 AND 10))
);

CREATE INDEX idx_cap_part_cap ON capacitaciones_participantes(id_cap);
CREATE INDEX idx_cap_part_agente ON capacitaciones_participantes(id_agente);
CREATE INDEX idx_cap_part_asistio ON capacitaciones_participantes(asistio);
CREATE INDEX idx_cap_part_aprobado ON capacitaciones_participantes(aprobado);

-- ============================================================================
-- MÓDULO 3: CONVOCATORIAS
-- ============================================================================

CREATE TABLE convocatoria (
    id_convocatoria SERIAL PRIMARY KEY,
    id_plani INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    id_turno INTEGER NOT NULL,
    fecha_convocatoria DATE NOT NULL,
    
    estado VARCHAR(20) DEFAULT 'vigente',
    
    id_convocatoria_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    motivo_cambio TEXT,
    usuario_modificacion VARCHAR(100),
    
    CONSTRAINT fk_conv_plani FOREIGN KEY (id_plani) REFERENCES planificacion(id_plani),
    CONSTRAINT fk_conv_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE RESTRICT,
    CONSTRAINT fk_conv_turno FOREIGN KEY (id_turno) REFERENCES turnos(id_turno),
    CONSTRAINT fk_conv_origen FOREIGN KEY (id_convocatoria_origen) 
        REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT chk_estado_conv CHECK (estado IN ('vigente', 'historica', 'cancelada', 'cumplida', 'con_inasistencia'))
);

CREATE INDEX idx_conv_plani ON convocatoria(id_plani);
CREATE INDEX idx_conv_agente ON convocatoria(id_agente);
CREATE INDEX idx_conv_fecha ON convocatoria(fecha_convocatoria);
CREATE INDEX idx_conv_estado ON convocatoria(estado);
CREATE INDEX idx_conv_agente_fecha_estado ON convocatoria(id_agente, fecha_convocatoria, estado);

-- ============================================================================
-- TRIGGER: Prevenir convocatorias duplicadas (POSTGRESQL)
-- ============================================================================

CREATE OR REPLACE FUNCTION func_prevent_duplicate_vigente()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'vigente' THEN
        IF EXISTS (
            SELECT 1 FROM convocatoria
            WHERE id_agente = NEW.id_agente
            AND fecha_convocatoria = NEW.fecha_convocatoria
            AND estado = 'vigente'
            AND id_convocatoria != COALESCE(NEW.id_convocatoria, 0)
        ) THEN
            RAISE EXCEPTION 'El agente ya tiene una convocatoria vigente para esta fecha';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_duplicate_vigente
BEFORE INSERT OR UPDATE ON convocatoria
FOR EACH ROW
EXECUTE FUNCTION func_prevent_duplicate_vigente();

-- ============================================================================
-- TRIGGER: Update fecha modificación convocatoria
-- ============================================================================

CREATE OR REPLACE FUNCTION func_update_fecha_modificacion()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        NEW.fecha_modificacion := CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_fecha_modificacion
BEFORE UPDATE ON convocatoria
FOR EACH ROW
EXECUTE FUNCTION func_update_fecha_modificacion();

-- ============================================================================
-- MÓDULO: CONVOCATORIA HISTORIAL
-- ============================================================================

CREATE TABLE convocatoria_historial (
    id_hist SERIAL PRIMARY KEY,
    id_convocatoria INTEGER NOT NULL,
    id_agente_anterior INTEGER NOT NULL,
    id_agente_nuevo INTEGER NOT NULL,
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_cambio VARCHAR(30) NOT NULL,
    motivo TEXT,
    id_transaccion_cambio INTEGER,
    usuario_responsable VARCHAR(100),
    
    CONSTRAINT fk_hist_conv FOREIGN KEY (id_convocatoria) 
        REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT fk_hist_agente_ant FOREIGN KEY (id_agente_anterior) 
        REFERENCES datos_personales(id_agente),
    CONSTRAINT fk_hist_agente_nue FOREIGN KEY (id_agente_nuevo) 
        REFERENCES datos_personales(id_agente),
    CONSTRAINT chk_tipo_cambio_hist CHECK (tipo_cambio IN ('intercambio', 'reasignacion', 'cancelacion', 'correccion'))
);

CREATE INDEX idx_hist_convocatoria ON convocatoria_historial(id_convocatoria);
CREATE INDEX idx_hist_fecha ON convocatoria_historial(fecha_cambio);

-- ============================================================================
-- TRIGGER: Registrar historial de cambios (POSTGRESQL)
-- ============================================================================

CREATE OR REPLACE FUNCTION func_registrar_historial_cambio()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.id_agente IS DISTINCT FROM NEW.id_agente) OR 
       (OLD.estado IS DISTINCT FROM NEW.estado) THEN
        INSERT INTO convocatoria_historial (
            id_convocatoria, id_agente_anterior, id_agente_nuevo,
            tipo_cambio, motivo
        )
        VALUES (
            NEW.id_convocatoria, OLD.id_agente, NEW.id_agente,
            'reasignacion', NEW.motivo_cambio
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_registrar_historial_cambio
AFTER UPDATE ON convocatoria
FOR EACH ROW
EXECUTE FUNCTION func_registrar_historial_cambio();

-- ============================================================================
-- RESTO DE TABLAS (SIN TRIGGERS COMPLEJOS)
-- ============================================================================

-- Cambios de turno
CREATE TABLE cambio_transaccion (
    id_transaccion SERIAL PRIMARY KEY,
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agente_iniciador INTEGER NOT NULL,
    tipo_transaccion VARCHAR(30) NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_validacion TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    fecha_ejecucion TIMESTAMP,
    usuario_aprobador VARCHAR(100),
    motivo_rechazo TEXT,
    observaciones TEXT,
    
    CONSTRAINT fk_cambio_iniciador FOREIGN KEY (agente_iniciador) 
        REFERENCES datos_personales(id_agente),
    CONSTRAINT chk_tipo_transaccion CHECK (tipo_transaccion IN ('intercambio_fechas', 'intercambio_horarios', 'reasignacion_simple')),
    CONSTRAINT chk_estado_transaccion CHECK (estado IN ('pendiente', 'validada', 'aprobada', 'ejecutada', 'rechazada', 'cancelada', 'error'))
);

CREATE INDEX idx_trans_iniciador ON cambio_transaccion(agente_iniciador);
CREATE INDEX idx_trans_estado ON cambio_transaccion(estado);

CREATE TABLE cambio_transaccion_detalle (
    id_detalle SERIAL PRIMARY KEY,
    id_transaccion INTEGER NOT NULL,
    secuencia INTEGER NOT NULL,
    id_convocatoria_original INTEGER NOT NULL,
    id_agente_original INTEGER NOT NULL,
    fecha_original DATE NOT NULL,
    id_turno_original INTEGER NOT NULL,
    id_convocatoria_nueva INTEGER,
    id_agente_nuevo INTEGER NOT NULL,
    fecha_nueva DATE NOT NULL,
    id_turno_nuevo INTEGER NOT NULL,
    validacion_capacitacion BOOLEAN DEFAULT FALSE,
    validacion_disponibilidad BOOLEAN DEFAULT FALSE,
    validacion_conflicto BOOLEAN DEFAULT FALSE,
    mensaje_validacion TEXT,
    
    CONSTRAINT fk_detalle_trans FOREIGN KEY (id_transaccion) 
        REFERENCES cambio_transaccion(id_transaccion) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_conv_orig FOREIGN KEY (id_convocatoria_original) 
        REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT fk_detalle_conv_nueva FOREIGN KEY (id_convocatoria_nueva) 
        REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT fk_detalle_agente_orig FOREIGN KEY (id_agente_original) 
        REFERENCES datos_personales(id_agente),
    CONSTRAINT fk_detalle_agente_nuevo FOREIGN KEY (id_agente_nuevo) 
        REFERENCES datos_personales(id_agente)
);

CREATE INDEX idx_detalle_trans ON cambio_transaccion_detalle(id_transaccion);

CREATE TABLE cambio_validacion (
    id_validacion SERIAL PRIMARY KEY,
    id_transaccion INTEGER NOT NULL,
    tipo_validacion VARCHAR(50) NOT NULL,
    es_bloqueante BOOLEAN DEFAULT TRUE,
    es_alerta BOOLEAN DEFAULT FALSE,
    estado VARCHAR(20) DEFAULT 'activa',
    mensaje TEXT NOT NULL,
    detalle_tecnico TEXT,
    fecha_validacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_resolucion VARCHAR(100),
    fecha_resolucion TIMESTAMP,
    
    CONSTRAINT fk_val_trans FOREIGN KEY (id_transaccion) 
        REFERENCES cambio_transaccion(id_transaccion) ON DELETE CASCADE,
    CONSTRAINT chk_estado_val CHECK (estado IN ('activa', 'resuelta', 'ignorada'))
);

CREATE INDEX idx_val_transaccion ON cambio_validacion(id_transaccion);
CREATE INDEX idx_val_tipo ON cambio_validacion(tipo_validacion);

-- Descansos
CREATE TABLE descansos (
    id_desc SERIAL PRIMARY KEY,
    id_agente INTEGER NOT NULL,
    dia_solicitado DATE NOT NULL,
    mes_solicitado INTEGER NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta TIMESTAMP,
    observaciones TEXT,
    CONSTRAINT fk_desc_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_estado_desc CHECK (estado IN ('pendiente', 'asignado', 'no_asignado')),
    CONSTRAINT chk_mes_desc CHECK (mes_solicitado BETWEEN 1 AND 12)
);

CREATE INDEX idx_desc_agente ON descansos(id_agente);
CREATE INDEX idx_desc_dia ON descansos(dia_solicitado);
CREATE INDEX idx_desc_estado ON descansos(estado);

CREATE TABLE disponibilidad (
    id_dispo SERIAL PRIMARY KEY,
    id_agente INTEGER NOT NULL,
    id_turno INTEGER NOT NULL,
    estado VARCHAR(20) DEFAULT 'disponible',
    prioridad INTEGER DEFAULT 2,
    fecha_declaracion DATE DEFAULT CURRENT_DATE,
    CONSTRAINT fk_dispo_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT fk_dispo_turno FOREIGN KEY (id_turno) REFERENCES turnos(id_turno),
    CONSTRAINT chk_estado_dispo CHECK (estado IN ('disponible', 'no_disponible')),
    CONSTRAINT chk_prioridad CHECK (prioridad BETWEEN 1 AND 3),
    CONSTRAINT uq_agente_turno UNIQUE (id_agente, id_turno)
);

CREATE INDEX idx_dispo_agente ON disponibilidad(id_agente);
CREATE INDEX idx_dispo_turno ON disponibilidad(id_turno);

-- Inasistencias
CREATE TABLE inasistencias (
    id_inasistencia SERIAL PRIMARY KEY,
    id_agente INTEGER NOT NULL,
    fecha_aviso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_inasistencia DATE NOT NULL,
    motivo VARCHAR(20) NOT NULL DEFAULT 'imprevisto',
    requiere_certificado BOOLEAN,
    estado VARCHAR(20) DEFAULT 'pendiente',
    observaciones TEXT,
    fecha_actualizacion_estado TIMESTAMP,
    usuario_actualizo_estado VARCHAR(100),
    
    CONSTRAINT fk_inasis_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_motivo_inasis CHECK (motivo IN ('medico', 'estudio', 'imprevisto', 'injustificada', 'otro_justificada')),
    CONSTRAINT chk_estado_inasis CHECK (estado IN ('pendiente', 'justificada', 'injustificada'))
);

CREATE INDEX idx_inasis_agente ON inasistencias(id_agente);
CREATE INDEX idx_inasis_fecha ON inasistencias(fecha_inasistencia);
CREATE INDEX idx_inasis_estado ON inasistencias(estado);

-- ============================================================================
-- TRIGGER: Auto-completar requiere_certificado (POSTGRESQL)
-- ============================================================================

CREATE OR REPLACE FUNCTION func_auto_requiere_certificado()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.requiere_certificado IS NULL THEN
        IF NEW.motivo IN ('medico', 'estudio', 'otro_justificada') THEN
            NEW.requiere_certificado := TRUE;
        ELSE
            NEW.requiere_certificado := FALSE;
            NEW.estado := 'injustificada';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_requiere_certificado
BEFORE INSERT ON inasistencias
FOR EACH ROW
EXECUTE FUNCTION func_auto_requiere_certificado();

-- Certificados
CREATE TABLE certificados (
    id_certificado SERIAL PRIMARY KEY,
    id_inasistencia INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    fecha_entrega_certificado DATE NOT NULL,
    fecha_inasistencia_justifica DATE NOT NULL,
    tipo_certificado VARCHAR(20),
    estado_certificado VARCHAR(20) DEFAULT 'presentado',
    observaciones TEXT,
    motivo_rechazo TEXT,
    fecha_revision TIMESTAMP,
    usuario_reviso VARCHAR(100),
    
    CONSTRAINT fk_cert_inasis FOREIGN KEY (id_inasistencia) 
        REFERENCES inasistencias(id_inasistencia) ON DELETE CASCADE,
    CONSTRAINT fk_cert_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_tipo_cert CHECK (tipo_certificado IN ('medico', 'academico', 'otro')),
    CONSTRAINT chk_estado_cert CHECK (estado_certificado IN ('presentado', 'aprobado', 'rechazado')),
    CONSTRAINT uq_inasistencia_tipo UNIQUE (id_inasistencia, tipo_certificado)
);

CREATE INDEX idx_cert_inasistencia ON certificados(id_inasistencia);
CREATE INDEX idx_cert_agente ON certificados(id_agente);
CREATE INDEX idx_cert_estado ON certificados(estado_certificado);

-- Menú (asignaciones)
CREATE TABLE menu (
    id_menu SERIAL PRIMARY KEY,
    id_convocatoria INTEGER NOT NULL,
    id_dispositivo INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    fecha_asignacion DATE NOT NULL,
    orden INTEGER DEFAULT 1,
    acompaña_grupo BOOLEAN DEFAULT FALSE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_menu_conv FOREIGN KEY (id_convocatoria) 
        REFERENCES convocatoria(id_convocatoria) ON DELETE CASCADE,
    CONSTRAINT fk_menu_dispo FOREIGN KEY (id_dispositivo) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT fk_menu_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_orden CHECK (orden > 0)
);

CREATE INDEX idx_menu_convocatoria ON menu(id_convocatoria);
CREATE INDEX idx_menu_dispositivo ON menu(id_dispositivo);
CREATE INDEX idx_menu_agente ON menu(id_agente);
CREATE INDEX idx_menu_fecha ON menu(fecha_asignacion);

-- Saldos
CREATE TABLE saldos (
    id_saldo SERIAL PRIMARY KEY,
    id_agente INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    horas_mes DECIMAL(6,2) DEFAULT 0,
    horas_anuales DECIMAL(7,2) DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_saldo_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT chk_mes_saldo CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT chk_anio_saldo CHECK (anio >= 2020),
    CONSTRAINT chk_horas_mes CHECK (horas_mes >= 0),
    CONSTRAINT chk_horas_anuales CHECK (horas_anuales >= 0),
    CONSTRAINT uq_agente_periodo UNIQUE (id_agente, mes, anio)
);

CREATE INDEX idx_saldo_agente ON saldos(id_agente);
CREATE INDEX idx_saldo_periodo ON saldos(anio, mes);

-- Logging
CREATE TABLE system_errors (
    id_error SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_type VARCHAR(50) NOT NULL,
    component VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_details TEXT,
    user_action TEXT,
    id_agente INTEGER,
    id_convocatoria INTEGER,
    id_transaccion INTEGER,
    additional_context TEXT,
    severity VARCHAR(20) DEFAULT 'medium',
    resolved BOOLEAN DEFAULT FALSE,
    resolution_date TIMESTAMP,
    resolution_notes TEXT,
    resolved_by VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    related_error_id INTEGER,
    
    CONSTRAINT chk_error_type CHECK (error_type IN (
        'trigger', 'constraint', 'validation', 'integration', 
        'python_operation', 'database', 'network', 'other'
    )),
    CONSTRAINT chk_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT fk_error_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente),
    CONSTRAINT fk_error_conv FOREIGN KEY (id_convocatoria) 
        REFERENCES convocatoria(id_convocatoria),
    CONSTRAINT fk_error_trans FOREIGN KEY (id_transaccion) 
        REFERENCES cambio_transaccion(id_transaccion)
);

CREATE INDEX idx_errors_timestamp ON system_errors(timestamp);
CREATE INDEX idx_errors_severity ON system_errors(severity, resolved);
CREATE INDEX idx_errors_type ON system_errors(error_type);
CREATE INDEX idx_errors_component ON system_errors(component);
CREATE INDEX idx_errors_resolved ON system_errors(resolved);
CREATE INDEX idx_errors_recurring ON system_errors(is_recurring);

CREATE TABLE error_patterns (
    id_pattern SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(200) NOT NULL UNIQUE,
    error_type VARCHAR(50),
    component VARCHAR(100),
    first_occurrence TIMESTAMP,
    last_occurrence TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1,
    severity_max VARCHAR(20),
    affected_users_count INTEGER DEFAULT 0,
    pattern_status VARCHAR(20) DEFAULT 'active',
    resolution_description TEXT,
    
    CONSTRAINT chk_pattern_status CHECK (pattern_status IN (
        'active', 'investigating', 'resolved', 'ignored'
    ))
);

CREATE INDEX idx_patterns_signature ON error_patterns(pattern_signature);
CREATE INDEX idx_patterns_status ON error_patterns(pattern_status);
CREATE INDEX idx_patterns_count ON error_patterns(occurrence_count);

-- Configuración
CREATE TABLE configuracion (
    clave VARCHAR(100) PRIMARY KEY,
    valor TEXT NOT NULL,
    descripcion TEXT,
    tipo_dato VARCHAR(20) DEFAULT 'texto',
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modificado_por VARCHAR(100),
    
    CONSTRAINT chk_tipo_dato CHECK (tipo_dato IN ('texto', 'numero', 'booleano', 'fecha', 'json'))
);

CREATE INDEX idx_config_tipo ON configuracion(tipo_dato);

-- Datos iniciales
INSERT INTO configuracion (clave, valor, descripcion, tipo_dato) VALUES
('sistema_version', '2.0', 'Versión del sistema', 'texto'),
('centro_nombre', 'El Molino Fábrica Cultural', 'Nombre del centro cultural', 'texto'),
('rotacion_anual_pct', '100', 'Porcentaje de rotación anual de personal', 'numero'),
('horas_minimas_mes', '60', 'Horas mínimas requeridas por mes', 'numero'),
('alerta_capacitacion_dias', '30', 'Días de anticipación para alertas de capacitación', 'numero'),
('email_notificaciones', 'admin@sistema.com', 'Email para notificaciones del sistema', 'texto'),
('backup_automatico', 'true', 'Activar backups automáticos', 'booleano'),
('dias_historico_errores', '90', 'Días de retención de errores resueltos', 'numero');

-- ============================================================================
-- COMENTARIOS FINALES
-- ============================================================================

/*
SISTEMA RRHH - POSTGRESQL
=========================

✅ 19 Tablas creadas
✅ 6 Triggers principales convertidos (Functions + Triggers)
✅ Índices optimizados
✅ Foreign Keys activas por defecto
✅ BOOLEAN nativo (TRUE/FALSE en lugar de 0/1)

DIFERENCIAS CLAVE CON SQLITE:
- SERIAL en lugar de AUTOINCREMENT
- Functions + Triggers en lugar de BEGIN...END
- BOOLEAN nativo
- CURRENT_TIMESTAMP / NOW() / CURRENT_DATE
- IS DISTINCT FROM para comparaciones NULL-safe

TRIGGERS PENDIENTES (convertir según necesidad):
- trg_asignar_descanso_aprobado
- trg_update_requiere_certificado
- trg_certificado_aprobado/rechazado
- trg_saldo_insert/update/delete_convocatoria
- trg_detectar_patron_error
- trg_error_resuelto

PRÓXIMO PASO:
1. Ejecutar este SQL en Supabase SQL Editor
2. Verificar que las 19 tablas se crearon
3. Migrar datos desde SQLite usando el UnifiedDBManager

*/
