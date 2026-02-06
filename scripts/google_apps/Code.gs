/**
 * GESTION RRHH - Google Sheets Admin Interface
 * Conexión segura con Supabase
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 * @date 2026-01-26
 * 
 * CONFIGURACIÓN REQUERIDA:
 * ========================
 * Archivo → Configuración del proyecto → Propiedades de script
 *   - SUPABASE_URL = https://xxx.supabase.co
 *   - SUPABASE_SERVICE_KEY = eyJh... (service_role key)
 * 
 * NUNCA hardcodear credenciales en este archivo.
 */

// ============================================================================
// MÓDULO: CONFIGURACIÓN SEGURA
// ============================================================================

/**
 * Obtiene configuración de Supabase desde PropertiesService
 * @private
 * @returns {Object} {url, key}
 */
function getSupabaseConfig_() {
  const props = PropertiesService.getScriptProperties();
  return {
    url: props.getProperty('SUPABASE_URL'),
    key: props.getProperty('SUPABASE_SERVICE_KEY')
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
// MÓDULO: TEST DE CONEXIÓN
// ============================================================================

/**
 * Verifica conexión con Supabase.
 * Ejecutar desde el editor de Apps Script para validar configuración.
 * 
 * @returns {string} Estado de la conexión
 */
function testConnection() {
  const config = getSupabaseConfig_();
  
  // Validar credenciales configuradas
  if (!config.url || !config.key) {
    const error = '❌ FALTAN CREDENCIALES\n\n' +
      'Configura en Archivo → Configuración del proyecto → Propiedades de script:\n' +
      '  • SUPABASE_URL\n' +
      '  • SUPABASE_SERVICE_KEY';
    Logger.log(error);
    throw new Error(error);
  }
  
  // Validar formato de URL
  if (!config.url.includes('supabase.co')) {
    throw new Error('❌ SUPABASE_URL inválida. Debe terminar en .supabase.co');
  }
  
  // Test: obtener conteo de datos_personales
  const endpoint = config.url + '/rest/v1/datos_personales?select=id_agente';
  
  try {
    const response = UrlFetchApp.fetch(endpoint, {
      headers: buildHeaders_(config.key),
      muteHttpExceptions: true
    });
    
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    if (code === 200) {
      const data = JSON.parse(body);
      const count = data.length;
      const msg = '✅ CONEXIÓN EXITOSA\n\n' +
        'URL: ' + config.url + '\n' +
        'Tabla datos_personales: ' + count + ' registros';
      Logger.log(msg);
      return msg;
    } else {
      const errorMsg = '❌ ERROR ' + code + '\n' + body;
      Logger.log(errorMsg);
      return errorMsg;
    }
    
  } catch (e) {
    const errorMsg = '❌ ERROR DE RED: ' + e.message;
    Logger.log(errorMsg);
    throw new Error(errorMsg);
  }
}

// ============================================================================
// MÓDULO: OPERACIONES CRUD (Preparado para expansión)
// ============================================================================

/**
 * Fetch genérico a Supabase REST API
 * @param {string} table - Nombre de la tabla
 * @param {string} query - Query string (ej: "?select=*&dni=eq.12345678")
 * @param {string} method - GET, POST, PATCH, DELETE
 * @param {Object} payload - Datos para POST/PATCH (opcional)
 * @returns {Object} Response parseada
 */
function supabaseRequest_(table, query, method, payload) {
  const config = getSupabaseConfig_();
  const url = config.url + '/rest/v1/' + table + (query || '');
  
  const options = {
    method: method || 'GET',
    headers: buildHeaders_(config.key),
    muteHttpExceptions: true
  };
  
  if (payload && (method === 'POST' || method === 'PATCH')) {
    options.payload = JSON.stringify(payload);
  }
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  return {
    success: code >= 200 && code < 300,
    code: code,
    data: body ? JSON.parse(body) : null
  };
}

/**
 * Obtiene todos los registros de una tabla (con paginación automática)
 * Supabase limita a 1000 registros por defecto. Esta función maneja paginación.
 * @param {string} table - Nombre de la tabla
 * @param {string} select - Columnas a seleccionar (default: *)
 * @returns {Array} Todos los registros
 */
function fetchAll(table, select) {
  const PAGE_SIZE = 1000; // Máximo permitido por Supabase
  let allData = [];
  let offset = 0;
  let hasMore = true;
  
  Logger.log('📥 Fetching ' + table + '...');
  
  while (hasMore) {
    const rangeStart = offset;
    const rangeEnd = offset + PAGE_SIZE - 1;
    
    const query = '?select=' + (select || '*');
    const config = getSupabaseConfig_();
    const url = config.url + '/rest/v1/' + table + query;
    
    const options = {
      method: 'GET',
      headers: Object.assign(buildHeaders_(config.key), {
        'Range': rangeStart + '-' + rangeEnd  // Header de paginación
      }),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    if (code === 200 || code === 206) {  // 206 = Partial Content
      const pageData = JSON.parse(body);
      allData = allData.concat(pageData);
      
      // Verificar si hay más datos
      const contentRange = response.getHeaders()['Content-Range'];
      if (contentRange) {
        // Format: "0-999/3000" o "0-999/*"
        const match = contentRange.match(/(\d+)-(\d+)\/(\d+|\*)/);
        if (match) {
          const end = parseInt(match[2]);
          const total = match[3] === '*' ? Infinity : parseInt(match[3]);
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

// ============================================================================
// MENÚ PERSONALIZADO
// ============================================================================

/**
 * DEPRECADO - Ver menu_updates.gs para versión actualizada
 * @deprecated
 */
function onOpen_old() {
  const menu = SpreadsheetApp.getUi().createMenu('🔌 Supabase');
  
  // Test section
  menu.addItem('🧪 Test Conexión', 'testConnection');
  menu.addSeparator();
  
  // Download section (Supabase → Sheets)
  menu.addSubMenu(SpreadsheetApp.getUi().createMenu('📥 Descargar Datos')
    .addItem('Datos Personales', 'loadDatosPersonales')
    .addItem('Turnos', 'loadTurnos')
    .addItem('Días (calendario)', 'loadDias')
  );
  
  // Upload section (Sheets → Supabase) - requiere sync.gs
  menu.addSubMenu(SpreadsheetApp.getUi().createMenu('📤 Sincronizar a Supabase')
    .addItem('Datos Personales', 'syncDatosPersonales')
    .addItem('Planificación', 'syncPlanificacion')
  );
  
  menu.addSeparator();
  menu.addItem('🧹 Limpiar Status', 'clearAllSyncStatus');
  
  menu.addToUi();
}


/**
 * Carga datos_personales en hoja "datos_residentes" (todas las columnas)
 */
function loadDatosPersonales() {
  // Fetch ALL columns
  const data = fetchAll('datos_personales', '*');
  if (data.length === 0) return;
  
  // Filtrar por cohorte si está configurada
  let filteredData = data;
  try {
    const filters = getActiveFilters();
    if (filters && filters.cohorte_activa) {
      const cohorteStr = String(filters.cohorte_activa).trim();
      filteredData = data.filter(p => String(p.cohorte).trim() === cohorteStr);
      Logger.log('👥 Filtrando personal por cohorte: ' + cohorteStr + ' (' + filteredData.length + '/' + data.length + ')');
    }
  } catch (e) {
    Logger.log('⚠️ No se pudieron cargar filtros: ' + e.message);
  }
  
  // Rename sheet to datos_residentes
  const sheet = getOrCreateSheet_('datos_residentes');
  
  // Get headers dynamically from first row
  if (filteredData.length === 0) {
    SpreadsheetApp.getUi().alert('ℹ️ No hay datos de residentes.');
    return;
  }
  
  const headers = Object.keys(filteredData[0]);
  const rows = filteredData.map(r => headers.map(h => r[h] || ''));
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold').setBackground('#4527a0').setFontColor('#ffffff');
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, Math.min(headers.length, 10));
  
  SpreadsheetApp.getUi().alert('✅ datos_residentes actualizada: ' + rows.length + ' registros');
}

/**
 * Carga turnos en hoja "REF_TURNOS" (incluye columna activo)
 */
function loadTurnos() {
  const fields = 'id_turno,tipo_turno,descripcion,cant_horas,hora_inicio,hora_fin,activo';
  const data = fetchAll('turnos', fields);
  if (data.length === 0) return;
  
  const sheet = getOrCreateSheet_('REF_TURNOS');
  const headers = ['id_turno', 'tipo_turno', 'descripcion', 'cant_horas', 'hora_inicio', 'hora_fin', 'activo'];
  const rows = data.map(r => headers.map(h => r[h]));
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold').setBackground('#00695c').setFontColor('#ffffff');
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  sheet.setFrozenRows(1);
  
  SpreadsheetApp.getUi().alert('✅ REF_TURNOS actualizada: ' + rows.length + ' registros');
}

/**
 * Carga vista_estado_cobertura en hoja "ESTADO_COBERTURA"
 * Marca con color los estados incompletos
 */
function loadEstadoCobertura() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const data = fetchAll('vista_estado_cobertura', '*');
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay datos de estado de cobertura.');
      return;
    }
    
    const sheet = getOrCreateSheet_('ESTADO_COBERTURA');
    
    // Get headers dynamically
    const headers = Object.keys(data[0]);
    const rows = data.map(r => headers.map(h => r[h] || ''));
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
      .setFontWeight('bold').setBackground('#bf360c').setFontColor('#ffffff');
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Find 'estado' column index
      const estadoColIdx = headers.indexOf('estado');
      if (estadoColIdx !== -1) {
        const estadoCol = estadoColIdx + 1; // 1-indexed
        
        // Red for incomplete states
        const ruleIncomplete = SpreadsheetApp.newConditionalFormatRule()
          .whenTextDoesNotContain('completo')
          .setBackground('#fee2e2').setFontColor('#dc2626')
          .setRanges([sheet.getRange(2, estadoCol, rows.length, 1)])
          .build();
        
        // Green for complete
        const ruleComplete = SpreadsheetApp.newConditionalFormatRule()
          .whenTextContains('completo')
          .setBackground('#dcfce7').setFontColor('#166534')
          .setRanges([sheet.getRange(2, estadoCol, rows.length, 1)])
          .build();
        
        sheet.setConditionalFormatRules([ruleIncomplete, ruleComplete]);
      }
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    ui.alert('✅ Estado de cobertura actualizado: ' + rows.length + ' registros');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

/**
 * Obtiene o crea una hoja
 * @private
 */
function getOrCreateSheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
