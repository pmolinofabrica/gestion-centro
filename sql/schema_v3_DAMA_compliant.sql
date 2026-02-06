-- ============================================================================
-- SISTEMA DE GESTIÓN DE RECURSOS HUMANOS - VERSION 3.0 DAMA-COMPLIANT
-- Base de datos: SQLite (preparada para PostgreSQL)
-- Contexto: Centro Cultural con rotación anual 100%
-- Enfoque: Arquitectura DAMA + Python + SQL Avanzado
-- Autor: Pablo - Data Analyst
-- Fecha: Diciembre 2025
-- ============================================================================
-- 
-- CAMBIOS PRINCIPALES v3.0:
-- - Tabla 'turnos' rediseñada: SIN numero_dia_semana (catálogo puro)
-- - Tabla 'planificacion' mejorada: CON horarios efectivos
-- - Trigger automático para horarios default
-- - Metadata DAMA completa
-- - Data lineage explícito
-- 
-- COMPLETITUD: 100%
-- - 19 tablas (sin cambios en cantidad)
-- - 15 triggers (+2 nuevos)
-- - 12 vistas (+1 nueva: vista_planificacion_completa)
-- - Sistema de logging completo
-- - Validaciones DAMA
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- MÓDULO 1: TABLAS MAESTRAS (Catálogos)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLA: dispositivos
-- Tipo: Reference Data
-- Propósito: Espacios físicos del centro cultural
-- ----------------------------------------------------------------------------
CREATE TABLE dispositivos (
    id_dispositivo INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_dispositivo VARCHAR(100) NOT NULL,
    piso_dispositivo INTEGER NOT NULL,
    activo BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    CONSTRAINT chk_piso CHECK (piso_dispositivo >= 0)
);

CREATE INDEX idx_dispositivos_piso ON dispositivos(piso_dispositivo);
CREATE INDEX idx_dispositivos_activo ON dispositivos(activo);

-- ----------------------------------------------------------------------------
-- TABLA: dias
-- Tipo: Reference Data (Dimensión de tiempo)
-- Propósito: Calendario con metadatos
-- ----------------------------------------------------------------------------
CREATE TABLE dias (
    id_dia INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL UNIQUE,
    mes INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    dia INTEGER NOT NULL,
    numero_dia_semana INTEGER NOT NULL,
    es_feriado BOOLEAN DEFAULT 0,
    nombre_feriado VARCHAR(200),
    CONSTRAINT chk_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT chk_dia CHECK (dia BETWEEN 1 AND 31),
    CONSTRAINT chk_numero_dia CHECK (numero_dia_semana BETWEEN 0 AND 6)
);

CREATE UNIQUE INDEX idx_dias_fecha ON dias(fecha);
CREATE INDEX idx_dias_mes ON dias(mes);
CREATE INDEX idx_dias_numero_dia_semana ON dias(numero_dia_semana);

-- ----------------------------------------------------------------------------
-- TABLA: turnos (REDISEÑADA v3.0 - DAMA COMPLIANT)
-- Tipo: Reference Data (Catálogo puro)
-- Propósito: Tipos de turno con horarios sugeridos (NO atados a día de semana)
-- Granularidad: Un registro = un tipo de turno
-- ----------------------------------------------------------------------------
CREATE TABLE turnos (
    id_turno INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificación
    tipo_turno VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    
    -- Horarios sugeridos (pueden ser NULL para turnos variables)
    hora_inicio_default TIME,
    hora_fin_default TIME,
    cant_horas_default DECIMAL(4,2),
    
    -- Restricciones de aplicabilidad (metadata de negocio)
    solo_fines_semana BOOLEAN DEFAULT 0,
    solo_semana BOOLEAN DEFAULT 0,
    
    -- Metadata DAMA
    turno_notas TEXT,
    activo BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    
    -- Constraints
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

-- Comentarios DAMA
COMMENT ON TABLE turnos IS 'Catálogo de tipos de turno (Reference Data). Un registro = un tipo de turno, reutilizable en cualquier día.';
COMMENT ON COLUMN turnos.hora_inicio_default IS 'Horario sugerido. NULL para turnos con horario variable (ej: capacitaciones).';
COMMENT ON COLUMN turnos.solo_fines_semana IS 'Indica si el turno solo aplica a sábados/domingos. Validación lógica, no constraint.';

-- ----------------------------------------------------------------------------
-- TABLA: datos_personales
-- Tipo: Master Data
-- Propósito: Personal y residentes del centro
-- ----------------------------------------------------------------------------
CREATE TABLE datos_personales (
    id_agente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    dni VARCHAR(20) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    email VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    domicilio TEXT,
    activo BOOLEAN DEFAULT 1,
    fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_baja TIMESTAMP,
    CONSTRAINT chk_email CHECK (email LIKE '%@%')
);

CREATE UNIQUE INDEX idx_agentes_dni ON datos_personales(dni);
CREATE INDEX idx_agentes_activo ON datos_personales(activo);
CREATE INDEX idx_agentes_nombre_apellido ON datos_personales(apellido, nombre);

-- ----------------------------------------------------------------------------
-- TABLA: planificacion (REDISEÑADA v3.0 - DAMA COMPLIANT)
-- Tipo: Transactional Data
-- Propósito: Instancia operativa de turno en fecha específica con horario efectivo
-- Granularidad: Fecha + Turno + Horario efectivo
-- Data Lineage: Horarios vienen de turnos.hora_*_default O se especifican custom
-- ----------------------------------------------------------------------------
CREATE TABLE planificacion (
    id_plani INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Referencias
    id_dia INTEGER NOT NULL,
    id_turno INTEGER NOT NULL,
    
    -- Horario efectivo (siempre presente)
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    cant_horas DECIMAL(4,2) NOT NULL,
    
    -- Metadata de horario (Data Lineage)
    usa_horario_custom BOOLEAN DEFAULT 0,
    motivo_horario_custom TEXT,
    
    -- Demanda
    cant_residentes_plan INTEGER NOT NULL,
    cant_visit INTEGER DEFAULT 0,
    
    -- Metadata DAMA
    plani_notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_creacion VARCHAR(100),
    fecha_modificacion TIMESTAMP,
    usuario_modificacion VARCHAR(100),
    
    -- Constraints
    CONSTRAINT fk_plani_dia FOREIGN KEY (id_dia) REFERENCES dias(id_dia),
    CONSTRAINT fk_plani_turno FOREIGN KEY (id_turno) REFERENCES turnos(id_turno),
    CONSTRAINT uq_plani_dia_turno UNIQUE (id_dia, id_turno),
    CONSTRAINT chk_cant_residentes CHECK (cant_residentes_plan > 0),
    CONSTRAINT chk_cant_visit CHECK (cant_visit >= 0),
    CONSTRAINT chk_horas CHECK (cant_horas > 0 AND cant_horas <= 24),
    CONSTRAINT chk_horario_coherente CHECK (hora_inicio < hora_fin)
);

CREATE INDEX idx_plani_dia ON planificacion(id_dia);
CREATE INDEX idx_plani_turno ON planificacion(id_turno);
CREATE INDEX idx_plani_custom ON planificacion(usa_horario_custom);

-- Comentarios DAMA
COMMENT ON TABLE planificacion IS 'Instancia operativa de turno en fecha específica (Transactional Data). Combina catálogo de turnos con fechas reales.';
COMMENT ON COLUMN planificacion.hora_inicio IS 'Horario efectivo. Puede venir de turnos.hora_inicio_default O ser especificado custom.';
COMMENT ON COLUMN planificacion.usa_horario_custom IS 'Data lineage: 0=usa default de catálogo, 1=horario específico para esta planificación.';

-- ============================================================================
-- TRIGGER: Auto-poblar horarios desde catálogo turnos (NUEVO v3.0)
-- Principio DAMA: DRY (Don't Repeat Yourself) + Automation
-- ============================================================================
CREATE TRIGGER trg_plani_auto_horarios
BEFORE INSERT ON planificacion
FOR EACH ROW
WHEN NEW.hora_inicio IS NULL
BEGIN
    UPDATE planificacion SET
        hora_inicio = COALESCE(
            (SELECT hora_inicio_default FROM turnos WHERE id_turno = NEW.id_turno),
            '00:00'
        ),
        hora_fin = COALESCE(
            (SELECT hora_fin_default FROM turnos WHERE id_turno = NEW.id_turno),
            '23:59'
        ),
        cant_horas = COALESCE(
            (SELECT cant_horas_default FROM turnos WHERE id_turno = NEW.id_turno),
            0
        ),
        usa_horario_custom = 0
    WHERE rowid = NEW.rowid;
END;

-- ============================================================================
-- TRIGGER: Actualizar fecha_modificacion en planificacion (NUEVO v3.0)
-- ============================================================================
CREATE TRIGGER trg_plani_update_timestamp
AFTER UPDATE ON planificacion
FOR EACH ROW
BEGIN
    UPDATE planificacion
    SET fecha_modificacion = CURRENT_TIMESTAMP
    WHERE id_plani = NEW.id_plani;
END;

-- ============================================================================
-- MÓDULO 2: CAPACITACIONES (sin cambios)
-- ============================================================================

CREATE TABLE capacitaciones (
    id_cap INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- ----------------------------------------------------------------------------

CREATE TABLE capacitaciones_dispositivos (
    id_cap_dispo INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- ----------------------------------------------------------------------------

CREATE TABLE capacitaciones_participantes (
    id_participante INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cap INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    asistio BOOLEAN DEFAULT 0,
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
-- MÓDULO 3: CONVOCATORIAS (sin cambios estructurales)
-- ============================================================================

CREATE TABLE convocatoria (
    id_convocatoria INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- ----------------------------------------------------------------------------

CREATE TABLE convocatoria_historial (
    id_hist INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- ============================================================================
-- MÓDULOS 4-10: Sin cambios estructurales
-- (Cambios de turno, Descansos, Inasistencias, Menu, Saldos, Logging, Config)
-- Se mantienen tal cual del schema v2.0
-- ============================================================================

-- [CONTINUARÁ EN SIGUIENTE ARCHIVO PARA CLARIDAD]
-- El resto de los módulos se mantienen sin cambios del schema v2.0

-- ============================================================================
-- VISTAS ANALÍTICAS (11 + 1 NUEVA)
-- ============================================================================

-- Vista NUEVA: Planificación completa con data lineage
CREATE VIEW vista_planificacion_completa AS
SELECT 
    p.id_plani,
    d.fecha,
    CASE CAST(strftime('%w', d.fecha) AS INTEGER)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Lunes'
        WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'
        WHEN 6 THEN 'Sábado'
    END AS dia_nombre,
    t.tipo_turno,
    t.descripcion AS turno_descripcion,
    
    -- Horario efectivo
    p.hora_inicio,
    p.hora_fin,
    p.cant_horas,
    
    -- Data lineage (origen del horario)
    CASE 
        WHEN p.usa_horario_custom = 1 THEN 'Custom'
        ELSE 'Catálogo'
    END AS origen_horario,
    p.motivo_horario_custom,
    
    -- Horario default del catálogo (para comparación)
    t.hora_inicio_default,
    t.hora_fin_default,
    t.cant_horas_default,
    
    -- Demanda
    p.cant_residentes_plan,
    p.cant_visit,
    p.plani_notas
FROM planificacion p
JOIN dias d ON p.id_dia = d.id_dia
JOIN turnos t ON p.id_turno = t.id_turno
ORDER BY d.fecha, p.hora_inicio;

-- [Las otras 11 vistas se mantienen del schema v2.0]

-- ============================================================================
-- DATOS INICIALES: Turnos según especificación DAMA
-- ============================================================================

INSERT INTO turnos (tipo_turno, descripcion, hora_inicio_default, hora_fin_default, cant_horas_default, solo_semana) VALUES
('mañana', 'Turno mañana lun-vie', '08:45', '11:15', 2.5, 1),
('tarde', 'Turno tarde lun-vie', '13:45', '16:15', 2.5, 1),
('intermedio', 'Turno intermedio lun-vie', '11:30', '13:30', 2.0, 1),
('capacitacion', 'Capacitación con horario variable', NULL, NULL, NULL, 0),
('apertura_publico_corto', 'Apertura al público 4.5h', '14:45', '19:15', 4.5, 0),
('apertura_publico_largo', 'Apertura al público 5.5h', '14:45', '20:15', 5.5, 0),
('descanso', 'Día de descanso', '00:00', '00:00', 0.0, 0);

-- ============================================================================
-- COMENTARIOS FINALES
-- ============================================================================

/*
SISTEMA RRHH v3.0 - DAMA COMPLIANT
===================================

CAMBIOS PRINCIPALES:
1. Tabla turnos: SIN numero_dia_semana (catálogo puro)
2. Tabla planificacion: CON horarios efectivos + data lineage
3. Trigger trg_plani_auto_horarios: Auto-completa horarios
4. Vista vista_planificacion_completa: Muestra origen de horarios

PRINCIPIOS DAMA IMPLEMENTADOS:
- Normalización 3FN
- Separación de concerns (Reference → Transactional)
- Data lineage explícito
- Single source of truth con override
- Metadata management completo
- Temporal consistency

VENTAJAS:
- Un turno = un tipo (sin duplicación)
- Queries más simples
- Flexibilidad total en horarios
- Mantenibilidad profesional
- Escalable a PostgreSQL

PRÓXIMO: Ver script_migracion_v2_a_v3.sql para migrar datos
*/
