/**
 * HELPERS DB - Capa de acceso a datos (Data Access Layer)
 * Funciones centralizadas para interacción con Supabase REST API
 * 
 * Este archivo es el ÚNICO punto de contacto con Supabase.
 * Todos los demás archivos deben usar estas funciones.
 * 
 * @author Pablo (Data Analyst)
 * @version 3.0.0 - Refactored: single source of truth
 */

// ============================================================================
// CONFIGURACIÓN Y AUTENTICACIÓN
// ============================================================================

/**
 * Obtiene configuración de Supabase desde PropertiesService
 * Soporta ambos nombres de propiedad: SUPABASE_SERVICE_KEY y SUPABASE_KEY
 * @private
 * @returns {Object} {url, key}
 */
function getSupabaseConfig_() {
  try {
    const props = PropertiesService.getScriptProperties();
    const url = props.getProperty('SUPABASE_URL');
    // Intentar SERVICE_KEY primero (más privilegios), luego KEY
    const key = props.getProperty('SUPABASE_SERVICE_KEY') 
             || props.getProperty('SUPABASE_KEY');
    if (url && key) return { url: url, key: key };
  } catch (e) {
    // Ignorar si falla
  }

  // Fallback a placeholders
  return {
    url: 'https://TU-PROYECTO.supabase.co',
    key: 'TU-ANON-KEY-AQUI' 
  };
}

/**
 * Construye headers estándar para Supabase REST API
 * @private
 * @param {string} apiKey - API Key de Supabase
 * @returns {Object} Headers HTTP
 */
function buildHeaders_(apiKey) {
  return {
    'apikey': apiKey,
    'Authorization': 'Bearer ' + apiKey,
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
  };
}

// ============================================================================
// FETCH: LECTURA DE DATOS (con paginación automática)
// ============================================================================

/**
 * Obtiene todos los registros de una tabla con filtros y paginación automática.
 * Supabase limita a 1000 registros por request. Esta función pagina transparentemente.
 * 
 * Soporta filtros con operadores:
 *   - Igualdad: { campo: valor }
 *   - Operador objeto: { campo: { operator: 'gte', value: '2025-01-01' } }
 *   - Sufijo convención: { fecha_gte: '2025-01-01', fecha_lt: '2026-01-01' }
 * 
 * @param {string} table - Nombre de la tabla o vista
 * @param {string} select - Columnas a seleccionar (default: *)
 * @param {Object} filters - Filtros opcionales
 * @returns {Array} Todos los registros
 */
function fetchAllWithFilters(table, select, filters) {
  const PAGE_SIZE = 1000;
  let allData = [];
  let offset = 0;
  let hasMore = true;
  
  // Construir query base con filtros
  let queryBase = '?select=' + (select || '*');
  
  if (filters) {
    Object.keys(filters).forEach(function(key) {
      var val = filters[key];
      if (val !== null && val !== undefined) {
        // Soporte para operador objeto: { operator: 'gte', value: '2025-01-01' }
        if (typeof val === 'object' && val.operator && val.value) {
          queryBase += '&' + key + '=' + val.operator + '.' + val.value;
        // Soporte para sufijo _gte / _lt
        } else if (key.endsWith('_gte')) {
          queryBase += '&' + key.replace('_gte', '') + '=gte.' + val;
        } else if (key.endsWith('_lt')) {
          queryBase += '&' + key.replace('_lt', '') + '=lt.' + val;
        } else {
          // Default: igualdad
          queryBase += '&' + key + '=eq.' + val;
        }
      }
    });
  }
  
  Logger.log('📥 Fetching ' + table + '...');
  
  while (hasMore) {
    var rangeStart = offset;
    var rangeEnd = offset + PAGE_SIZE - 1;
    
    var config = getSupabaseConfig_();
    var url = config.url + '/rest/v1/' + table + queryBase;
    
    var options = {
      method: 'GET',
      headers: Object.assign(buildHeaders_(config.key), {
        'Range': rangeStart + '-' + rangeEnd
      }),
      muteHttpExceptions: true
    };
    
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    var body = response.getContentText();
    
    if (code === 200 || code === 206) {  // 206 = Partial Content
      var pageData = JSON.parse(body);
      allData = allData.concat(pageData);
      
      // Verificar si hay más datos via Content-Range header
      var contentRange = response.getHeaders()['Content-Range'];
      if (contentRange) {
        // Format: "0-999/3000" o "0-999/*"
        var match = contentRange.match(/(\d+)-(\d+)\/(\d+|\*)/);
        if (match) {
          var end = parseInt(match[2]);
          var total = match[3] === '*' ? Infinity : parseInt(match[3]);
          hasMore = (end + 1) < total;
          offset = end + 1;
          
          if (hasMore) {
            Logger.log('   📄 Página ' + Math.floor(offset / PAGE_SIZE) + ': ' + pageData.length + ' registros');
          }
        } else {
          hasMore = false;
        }
      } else {
        // Sin Content-Range, asumir que es todo
        hasMore = false;
      }
      
      // Protección: si una página viene vacía, parar
      if (pageData.length === 0) {
        hasMore = false;
      }
      
    } else {
      Logger.log('❌ Error en ' + table + ': ' + code + ' - ' + body);
      hasMore = false;
    }
  }
  
  Logger.log('✅ ' + table + ': ' + allData.length + ' registros totales');
  return allData;
}

/**
 * Obtiene todos los registros de una tabla (wrapper sin filtros)
 * @param {string} table - Nombre de la tabla
 * @param {string} select - Columnas a seleccionar (default: *)
 * @returns {Array} Todos los registros
 */
function fetchAll(table, select) {
  return fetchAllWithFilters(table, select, null);
}

/**
 * Obtiene un solo registro
 * @param {string} table - Nombre de la tabla
 * @param {string} select - Columnas a seleccionar
 * @param {Object} filters - Filtros para buscar
 * @returns {Object|null} Primer registro encontrado o null
 */
function fetchOne(table, select, filters) {
  var res = fetchAllWithFilters(table, select, filters);
  return (res && res.length > 0) ? res[0] : null;
}

// ============================================================================
// WRITE: ESCRITURA DE DATOS
// ============================================================================

/**
 * Fetch genérico a Supabase REST API (CRUD)
 * @param {string} table - Nombre de la tabla
 * @param {string} query - Query string (ej: "?select=*&dni=eq.12345678")
 * @param {string} method - GET, POST, PATCH, DELETE
 * @param {Object} payload - Datos para POST/PATCH (opcional)
 * @returns {Object} { success, code, data }
 */
function supabaseRequest_(table, query, method, payload) {
  var config = getSupabaseConfig_();
  var url = config.url + '/rest/v1/' + table + (query || '');
  
  var options = {
    method: method || 'GET',
    headers: buildHeaders_(config.key),
    muteHttpExceptions: true
  };
  
  if (payload && (method === 'POST' || method === 'PATCH')) {
    options.payload = JSON.stringify(payload);
  }
  
  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();
  var body = response.getContentText();
  
  return {
    success: code >= 200 && code < 300,
    code: code,
    data: body ? JSON.parse(body) : null
  };
}

/**
 * Inserta una fila nueva (POST estándar)
 * @param {string} table - Nombre de la tabla
 * @param {Object} record - Datos a insertar
 * @returns {Object} { success, data/error }
 */
function insertRow(table, record) {
  var config = getSupabaseConfig_();
  var url = config.url + '/rest/v1/' + table;
  
  var options = {
    method: 'POST',
    headers: buildHeaders_(config.key),
    payload: JSON.stringify(record),
    muteHttpExceptions: true
  };
  
  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();
  var body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    return { success: true, data: JSON.parse(body) };
  } else {
    return { success: false, error: 'HTTP ' + code + ': ' + body };
  }
}

/**
 * Upsert genérico (insert o update por unique key)
 * @param {string} table - Nombre de la tabla
 * @param {Object} record - Datos a insertar/actualizar
 * @param {string|Array} uniqueKey - Columna(s) de constraint único
 * @returns {Object} { success, error? }
 */
function upsertRecord(table, record, uniqueKey) {
  var config = getSupabaseConfig_();
  
  var conflictClause = '';
  if (Array.isArray(uniqueKey)) {
    conflictClause = uniqueKey.join(',');
  } else {
    conflictClause = uniqueKey;
  }
  
  var url = config.url + '/rest/v1/' + table + 
    (conflictClause ? '?on_conflict=' + conflictClause : '');
  
  var options = {
    method: 'POST',
    headers: buildHeaders_(config.key),
    payload: JSON.stringify(record),
    muteHttpExceptions: true
  };
  
  // Header para upsert
  // Header para upsert
  options.headers['Prefer'] = 'resolution=merge-duplicates, return=representation';
  
  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();
  var body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    return { success: true, data: body ? JSON.parse(body) : null };
  } else {
    return { success: false, error: 'HTTP ' + code + ': ' + body.substring(0, 100) };
  }
}

/**
 * Llama a una función RPC de PostgreSQL (POST /rpc/...)
 * @param {string} rpcName - Nombre de la función SQL
 * @param {Object} params - Parámetros
 * @returns {Object} { success, data/error }
 */
function callRpc(rpcName, params) {
  var config = getSupabaseConfig_();
  var url = config.url + '/rest/v1/rpc/' + rpcName;
  
  var options = {
    method: 'POST',
    headers: {
      'apikey': config.key,
      'Authorization': 'Bearer ' + config.key,
      'Content-Type': 'application/json' 
    },
    payload: JSON.stringify(params || {}),
    muteHttpExceptions: true
  };
  
  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();
  var body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    try {
      return { success: true, data: body ? JSON.parse(body) : null };
    } catch(e) {
      return { success: true, data: body };
    }
  } else {
    return { success: false, error: 'RPC Error ' + code + ': ' + body };
  }
}

// ============================================================================
// UTILIDADES COMPARTIDAS
// ============================================================================

/**
 * Obtiene o crea una hoja de cálculo por nombre
 * @param {string} name - Nombre de la hoja
 * @returns {Sheet} Hoja de Google Sheets
 */
function getOrCreateSheet_(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

/**
 * Formatea una fecha a YYYY-MM-DD
 * @param {Date|string|number} dateValue - Fecha a formatear
 * @returns {string} Fecha formateada
 */
function formatDate_(dateValue) {
  if (!dateValue) return null;
  if (dateValue instanceof Date) {
    return Utilities.formatDate(dateValue, 'America/Argentina/Buenos_Aires', 'yyyy-MM-dd');
  }
  // Si es un número (serial de Excel), convertir primero
  if (typeof dateValue === 'number') {
    var d = new Date(new Date(1899, 11, 30).getTime() + Math.floor(dateValue) * 86400000);
    return Utilities.formatDate(d, 'America/Argentina/Buenos_Aires', 'yyyy-MM-dd');
  }
  return String(dateValue);
}

/**
 * Formatea un timestamp para Postgres (ISO 8601)
 * Evita errores de zona horaria no reconocida como "GMT-0300"
 * @param {Date|string} val - Valor de fecha/hora
 * @returns {string} ISO String
 */
function formatTimestamp_(val) {
  if (!val) return null;
  var d = (val instanceof Date) ? val : new Date(val);
  // forzar toISOString() que es el standard que Postgres ama
  try {
    return d.toISOString();
  } catch(e) {
    Logger.log('⚠️ formatTimestamp_: Error al parsear ' + val);
    return null;
  }
}

/**
 * Alerta por email ante errores críticos
 * @param {string} asunto - Titulo del error
 * @param {string} cuerpo - Detalle del error
 */
function _alertar_(asunto, cuerpo) {
  try {
    MailApp.sendEmail(
      Session.getEffectiveUser().getEmail(),
      '[RRHH Molino] ' + asunto,
      cuerpo + '\n\nFecha: ' + new Date().toString()
    );
  } catch(e) { 
    Logger.log('⚠️ No se pudo enviar alerta por email: ' + e.message);
  }
}
