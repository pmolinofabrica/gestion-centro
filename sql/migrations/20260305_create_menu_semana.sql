-- ============================================================================
-- SQL SCRIPT: CREACIÓN DE LA TABLA menu_semana
-- Autor: Pablo / AI Assistant
-- Descripción: Tabla espejo de "menu" con adaptaciones para Días de Semana 
--              (Múltiples turnos, tipos de organización y turnos rotativos).
-- ============================================================================

CREATE TABLE menu_semana (
    -- Preferimos dejar una id explícita aunque la PK lógica sea la tupla
    id_menu_semana SERIAL,
    
    -- Referencias Core
    id_convocatoria INTEGER NOT NULL,
    id_dispositivo INTEGER NOT NULL,
    id_agente INTEGER NOT NULL,
    fecha_asignacion DATE NOT NULL,
    id_turno INTEGER NOT NULL, 
    
    -- Organización Intradiaria
    orden INTEGER DEFAULT 1,
    acompaña_grupo BOOLEAN DEFAULT FALSE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Data Lineage y Ejecución
    estado_ejecucion VARCHAR(30) DEFAULT 'planificado',
    id_dispositivo_origen INTEGER,
    dispositivo_cerrado BOOLEAN DEFAULT FALSE,
    es_capacitacion_servicio BOOLEAN DEFAULT FALSE,
    
    -- Nuevos campos para la lógica de Semana
    tipo_organizacion VARCHAR(50) DEFAULT 'dispositivos fijos',
    numero_grupo INTEGER,
    
    -- LA LLAVE PRIMARIA EXIGIDA:
    CONSTRAINT pk_menu_semana PRIMARY KEY (id_menu_semana),
    CONSTRAINT uq_menu_semana_asignacion UNIQUE (id_agente, fecha_asignacion, id_turno, id_dispositivo),
    
    -- Claves Foráneas
    CONSTRAINT fk_menus_conv FOREIGN KEY (id_convocatoria) 
        REFERENCES convocatoria(id_convocatoria) ON DELETE CASCADE,
    CONSTRAINT fk_menus_dispo FOREIGN KEY (id_dispositivo) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT fk_menus_agente FOREIGN KEY (id_agente) 
        REFERENCES datos_personales(id_agente) ON DELETE CASCADE,
    CONSTRAINT fk_menus_turno FOREIGN KEY (id_turno) 
        REFERENCES turnos(id_turno) ON DELETE RESTRICT,
    CONSTRAINT fk_menus_dispo_origen FOREIGN KEY (id_dispositivo_origen) 
        REFERENCES dispositivos(id_dispositivo) ON DELETE SET NULL,
    
    -- Restricciones de Dominio
    CONSTRAINT chk_menus_orden CHECK (orden > 0),
    CONSTRAINT chk_menus_estado_ejecucion CHECK (
        estado_ejecucion IN (
            'planificado', 
            'ausente_aviso', 
            'ausente_imprevisto', 
            'reasignado_decision', 
            'reasignado_necesidad', 
            'cubierto'
        )
    ),
    CONSTRAINT chk_menus_tipo_org CHECK (
        tipo_organizacion IN (
            'dispositivos fijos', 
            'rotacion simple', 
            'rotacion completa'
        )
    )
    
    -- NOTA: Si en rotacion simple un agente se asigna a 3 dispositivos diferentes 
    -- en el mismo turno, la PK compuesta de arriba chocaría.
    -- (id_agente, fecha_asignacion, id_turno) impide 2 inserciones para el mismo turno.
    -- ¿Verificar en el plan si esto es válido?
);

CREATE INDEX idx_menu_sem_convocatoria ON menu_semana(id_convocatoria);
CREATE INDEX idx_menu_sem_dispositivo ON menu_semana(id_dispositivo);
CREATE INDEX idx_menu_sem_agente ON menu_semana(id_agente);
CREATE INDEX idx_menu_sem_fecha ON menu_semana(fecha_asignacion);
CREATE INDEX idx_menu_sem_turno ON menu_semana(id_turno);
