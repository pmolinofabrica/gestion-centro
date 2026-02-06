/**
 * HELPERS DB - Funciones para interacción con Supabase
 * Generado para Módulo Asignaciones 2026
 */

/**
 * Inserta una fila nueva (POST estándar)
 */
function insertRow(table, record) {
  const config = getSupabaseConfig_(); // Debe estar en secrets.gs o definido abajo
  const url = config.url + '/rest/v1/' + table;
  
  const options = {
    method: 'POST',
    headers: {
      'apikey': config.key,
      'Authorization': 'Bearer ' + config.key,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation'
    },
    payload: JSON.stringify(record),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    return { success: true, data: JSON.parse(body) };
  } else {
    return { success: false, error: 'HTTP ' + code + ': ' + body };
  }
}

/**
 * Llama a una función RPC de PostgreSQL (POST /rpc/...)
 * @param {string} rpcName - Nombre de la función SQL (ej: 'rpc_importar_calendario')
 * @param {Object} params - Objeto con los parámetros (ej: { payload: [...] })
 */
function callRpc(rpcName, params) {
  const config = getSupabaseConfig_();
  const url = config.url + '/rest/v1/rpc/' + rpcName;
  
  const options = {
    method: 'POST',
    headers: {
      'apikey': config.key,
      'Authorization': 'Bearer ' + config.key,
      'Content-Type': 'application/json' 
    },
    payload: JSON.stringify(params || {}),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    // Si returns void, body puede ser vacío. Si returns json, parseamos.
    try {
        return { success: true, data: body ? JSON.parse(body) : null };
    } catch(e) {
        return { success: true, data: body }; // Texto plano?
    }
  } else {
    return { success: false, error: 'RPC Error ' + code + ': ' + body };
  }
}

/**
 * Obtiene registros con filtros (GET)
 */
function fetchAllWithFilters(table, select, filters) {
  const config = getSupabaseConfig_();
  let query = '?select=' + (select || '*');
  
  if (filters) {
    Object.keys(filters).forEach(key => {
      const val = filters[key];
      if (val !== null && val !== undefined) {
        // Soporte para operadores: { fecha: { operator: 'gte', value: '2025-01-01' } }
        if (typeof val === 'object' && val.operator && val.value) {
            query += '&' + key + '=' + val.operator + '.' + val.value;
        } else {
            // Comportamiento default: igualdad
            query += '&' + key + '=eq.' + val;
        }
      }
    });
  }
  
  const url = config.url + '/rest/v1/' + table + query;
  
  const options = {
    method: 'GET',
    headers: {
      'apikey': config.key,
      'Authorization': 'Bearer ' + config.key
    },
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  if (code === 200) {
    return JSON.parse(body);
  } else {
    Logger.log('Error fetching ' + table + ': ' + body);
    return [];
  }
}

/**
 * Obtiene un solo registro
 */
function fetchOne(table, select, filters) {
  const res = fetchAllWithFilters(table, select, filters);
  return (res && res.length > 0) ? res[0] : null;
}

/**
 * Obtiene todos los registros (Wrapper para compatibilidad)
 */
function fetchAll(table, select) {
  return fetchAllWithFilters(table, select, null);
}

/**
 * Obtiene configuración de secretos (Fallback si no existe secrets.gs)
 */
function getSupabaseConfig_() {
  // Intenta leer de PropertiesService primero
  try {
    const props = PropertiesService.getScriptProperties();
    const url = props.getProperty('SUPABASE_URL');
    const key = props.getProperty('SUPABASE_KEY');
    if (url && key) return { url: url, key: key };
  } catch (e) {
    // Ignorar si falla
  }

  // Fallback a placeholders (El usuario debe editar esto si no usa PropertiesService)
  return {
    url: 'https://TU-PROYECTO.supabase.co',
    key: 'TU-ANON-KEY-AQUI' 
  };
}
