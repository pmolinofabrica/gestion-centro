/**
 * CONFIGURACIÓN DE TABLAS - DAMA COMPLIANT
 * Debe coincidir con config_tables.json y schema_v3_DAMA_compliant.sql
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// CONFIGURACIÓN DE TABLAS
// ============================================================================

/**
 * Metadata de tablas sincronizadas.
 * DAMA Compliance: Nombres de columnas = esquema SQL exacto
 */
const TABLE_CONFIG = {
  
  // Master Data
  datos_personales: {
    unique_key: 'dni',
    mandatory: ['nombre', 'apellido', 'dni', 'cohorte'],
    types: {
      id_agente: 'int',
      nombre: 'str',
      apellido: 'str',
      dni: 'str',
      fecha_nacimiento: 'date',
      email: 'str',
      telefono: 'str',
      domicilio: 'str',
      activo: 'bool',
      fecha_alta: 'datetime',
      fecha_baja: 'datetime',
      cohorte: 'int'
    }
  },
  
  // Reference Data
  turnos: {
    unique_key: 'tipo_turno',
    mandatory: ['tipo_turno', 'cant_horas_default'],
    allowed_values: {
      tipo_turno: ['mañana', 'tarde', 'intermedio', 'capacitacion', 
                   'apertura_publico_corto', 'apertura_publico_largo', 'descanso']
    },
    types: {
      id_turno: 'int',
      tipo_turno: 'str',
      descripcion: 'str',
      hora_inicio_default: 'time',
      hora_fin_default: 'time',
      cant_horas_default: 'float',
      solo_fines_semana: 'bool',
      solo_semana: 'bool',
      activo: 'bool'
    }
  },
  
  // Reference Data (Time Dimension)
  dias: {
    unique_key: 'fecha',
    mandatory: ['fecha', 'es_feriado'],
    types: {
      id_dia: 'int',
      fecha: 'date',
      mes: 'int',
      semana: 'int',
      dia: 'int',
      numero_dia_semana: 'int',
      es_feriado: 'bool',
      nombre_feriado: 'str'
    }
  },
  
  // Transactional Data
  planificacion: {
    unique_key: ['id_dia', 'id_turno'],
    mandatory: ['id_dia', 'id_turno', 'cant_residentes_plan'],
    types: {
      id_plani: 'int',
      id_dia: 'int',
      id_turno: 'int',
      hora_inicio: 'time',
      hora_fin: 'time',
      cant_horas: 'float',
      usa_horario_custom: 'bool',
      motivo_horario_custom: 'str',
      cant_residentes_plan: 'int',
      cant_visit: 'int'
    }
  },
  
  // Transactional Data
  convocatoria: {
    unique_key: ['id_plani', 'id_agente'],
    mandatory: ['id_plani', 'id_agente', 'id_turno', 'fecha_convocatoria'],
    allowed_values: {
      estado: ['vigente', 'historica', 'cancelada', 'cumplida', 'con_inasistencia']
    },
    types: {
      id_convocatoria: 'int',
      id_plani: 'int',
      id_agente: 'int',
      id_turno: 'int',
      fecha_convocatoria: 'date',
      estado: 'str',
      turno_cancelado: 'bool',  // NUEVO: marca turnos cancelados individualmente
      motivo_cambio: 'str'
    }
  },
  
  // Transactional Data
  saldos: {
    unique_key: ['id_agente', 'mes', 'anio'],
    mandatory: ['id_agente', 'mes', 'anio'],
    types: {
      id_agente: 'int',
      mes: 'int',
      anio: 'int',
      horas_mes: 'float'
    }
  },

  // Transactional Data
  inasistencias: {
    unique_key: 'id_inasistencia',
    mandatory: ['id_agente', 'fecha_inasistencia'],
    types: {
      id_inasistencia: 'int',
      id_agente: 'int',
      fecha_inasistencia: 'date',
      motivo: 'str',
      estado: 'str',
      observaciones: 'str',
      requiere_certificado: 'bool'
    }
  },

  // Transactional Data
  certificados: {
    unique_key: 'id_certificado',
    mandatory: ['id_agente'],
    types: {
      id_certificado: 'int',
      id_agente: 'int',
      id_inasistencia: 'int',
      fecha_entrega_certificado: 'date',
      fecha_inasistencia_justifica: 'date',
      tipo_certificado: 'str',
      estado_certificado: 'str',
      observaciones: 'str'
    }
  }
};

// ============================================================================
// FUNCIONES DE VALIDACIÓN DAMA
// ============================================================================

/**
 * Valida un registro contra la configuración de tabla
 * @param {string} tableName - Nombre de la tabla
 * @param {Object} record - Registro a validar
 * @returns {Object} {valid: bool, errors: string[]}
 */
function validateRecord(tableName, record) {
  const config = TABLE_CONFIG[tableName];
  if (!config) {
    return { valid: false, errors: ['Tabla no configurada: ' + tableName] };
  }
  
  const errors = [];
  
  // Validar campos obligatorios
  config.mandatory.forEach(field => {
    if (record[field] === null || record[field] === undefined || record[field] === '') {
      errors.push('Campo obligatorio faltante: ' + field);
    }
  });
  
  // Validar valores permitidos
  if (config.allowed_values) {
    Object.keys(config.allowed_values).forEach(field => {
      if (record[field] && !config.allowed_values[field].includes(record[field])) {
        errors.push(field + ': valor no permitido "' + record[field] + '"');
      }
    });
  }
  
  // Validar tipos de datos
  Object.keys(record).forEach(field => {
    const value = record[field];
    const expectedType = config.types[field];
    
    if (value !== null && value !== undefined && value !== '' && expectedType) {
      const actualType = typeof value;
      
      switch (expectedType) {
        case 'int':
          if (!Number.isInteger(Number(value))) {
            errors.push(field + ': debe ser entero');
          }
          break;
        case 'float':
          if (isNaN(Number(value))) {
            errors.push(field + ': debe ser número');
          }
          break;
        case 'bool':
          if (value !== true && value !== false && value !== 0 && value !== 1) {
            errors.push(field + ': debe ser booleano');
          }
          break;
        case 'date':
          if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
            errors.push(field + ': formato fecha debe ser YYYY-MM-DD');
          }
          break;
      }
    }
  });
  
  return {
    valid: errors.length === 0,
    errors: errors
  };
}

/**
 * Obtiene la configuración de una tabla
 * @param {string} tableName
 * @returns {Object|null}
 */
function getTableConfig(tableName) {
  return TABLE_CONFIG[tableName] || null;
}

/**
 * Lista todas las tablas configuradas
 * @returns {string[]}
 */
function getConfiguredTables() {
  return Object.keys(TABLE_CONFIG);
}
