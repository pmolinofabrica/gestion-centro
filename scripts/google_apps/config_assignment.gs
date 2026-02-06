/**
 * CONFIGURACIÓN ADICIONAL - Módulo Asignaciones (Menu 2026)
 * Agrega las definiciones de las nuevas tablas al sistema DAMA
 */

// Extender, no reemplazar si ya existe TABLE_CONFIG.
// Si es un script nuevo, simplemente definimos TABLE_CONFIG.
if (typeof TABLE_CONFIG === 'undefined') {
  var TABLE_CONFIG = {};
}

// 1. Calendario de Dispositivos (Menú)
TABLE_CONFIG['calendario_dispositivos'] = {
  unique_key: ['fecha', 'id_turno', 'id_dispositivo'],
  mandatory: ['fecha', 'id_turno', 'id_dispositivo'],
  types: {
    id: 'int',
    fecha: 'date',
    id_turno: 'int',
    id_dispositivo: 'int',
    cupo_objetivo: 'int'
  }
};

// 4. Staging Importación (Buzón)
TABLE_CONFIG['stg_calendario_import'] = {
  unique_key: ['id'], // Es serial, no tiene unique key natural obligatoria para insert
  mandatory: ['fecha', 'id_turno', 'config_raw'],
  types: {
    id: 'int',
    fecha: 'date',
    id_turno: 'int',
    config_raw: 'string'
  }
};

// 5. Vista Estado Calendario (ReadOnly)
TABLE_CONFIG['vista_estado_calendario'] = {
  unique_key: ['fecha', 'id_turno'], 
  mandatory: ['fecha'],
  types: {
    fecha: 'date',
    id_turno: 'int',
    nombre_turno: 'string',
    dispositivos_configurados: 'int',
    personas_asignadas: 'int',
    estado: 'string'
  }
};

// 6. Vista Demanda (Planificación)
TABLE_CONFIG['vista_demanda_planificada'] = {
  unique_key: ['fecha', 'id_turno'],
  mandatory: ['fecha'],
  types: {
    fecha: 'date',
    id_turno: 'int',
    cantidad_personas: 'int'
  }
};

// 2. Asignaciones (Registro)
TABLE_CONFIG['asignaciones'] = {
  unique_key: ['id_agente', 'fecha', 'id_turno'],
  mandatory: ['id_agente', 'id_dispositivo', 'fecha', 'id_turno'],
  types: {
    id: 'int',
    id_agente: 'int',
    id_dispositivo: 'int',
    fecha: 'date',
    id_turno: 'int',
    es_doble_turno: 'bool',
    es_capacitacion_servicio: 'bool'
  }
};

// 3. Dispositivos (Maestra)
// 3. Dispositivos (Maestra)
TABLE_CONFIG['dispositivos'] = {
  unique_key: ['id_dispositivo'],
  mandatory: ['nombre_dispositivo', 'activo'],
  types: {
    id_dispositivo: 'int',
    nombre_dispositivo: 'string',
    piso_dispositivo: 'int',
    activo: 'bool',
    es_critico: 'bool',
    cupo_minimo: 'int',
    cupo_optimo: 'int'
  }
};

/**
 * Valida un registro (Versión Standalone si no copiaste config.gs)
 */
function validateRecord(tableName, record) {
  const config = TABLE_CONFIG[tableName];
  if (!config) return { valid: false, errors: ['Tabla no configurada: ' + tableName] };
  
  const errors = [];
  config.mandatory.forEach(field => {
    if (record[field] === null || record[field] === undefined || record[field] === '') {
      errors.push('Falta: ' + field);
    }
  });
  
  return { valid: errors.length === 0, errors: errors };
}
