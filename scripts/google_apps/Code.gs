/**
 * GESTION RRHH - Funciones de UI y carga de datos de referencia
 * 
 * @author Pablo (Data Analyst)
 * @version 2.0.0 - Refactored: removed duplicates, uses db_helpers.gs
 * @date 2026-02-10
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
// MÓDULO: TEST DE CONEXIÓN
// ============================================================================

/**
 * Verifica conexión con Supabase.
 * Ejecutar desde el editor de Apps Script para validar configuración.
 * 
 * @returns {string} Estado de la conexión
 */
function testConnection() {
  var config = getSupabaseConfig_();
  
  // Validar credenciales configuradas
  if (!config.url || !config.key) {
    var error = '❌ FALTAN CREDENCIALES\n\n' +
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
  var endpoint = config.url + '/rest/v1/datos_personales?select=id_agente';
  
  try {
    var response = UrlFetchApp.fetch(endpoint, {
      headers: buildHeaders_(config.key),
      muteHttpExceptions: true
    });
    
    var code = response.getResponseCode();
    var body = response.getContentText();
    
    if (code === 200) {
      var data = JSON.parse(body);
      var count = data.length;
      var msg = '✅ CONEXIÓN EXITOSA\n\n' +
        'URL: ' + config.url + '\n' +
        'Tabla datos_personales: ' + count + ' registros';
      Logger.log(msg);
      return msg;
    } else {
      var errorMsg = '❌ ERROR ' + code + '\n' + body;
      Logger.log(errorMsg);
      return errorMsg;
    }
    
  } catch (e) {
    var errorMsg = '❌ ERROR DE RED: ' + e.message;
    Logger.log(errorMsg);
    throw new Error(errorMsg);
  }
}

// ============================================================================
// MÓDULO: CARGA DE DATOS DE REFERENCIA
// ============================================================================

/**
 * Carga datos_personales en hoja "datos_residentes" (todas las columnas)
 */
function loadDatosPersonales() {
  // Fetch ALL columns
  var data = fetchAll('datos_personales', '*');
  if (data.length === 0) return;
  
  // Filtrar por cohorte si está configurada
  var filteredData = data;
  try {
    var filters = getActiveFilters();
    if (filters && filters.cohorte_activa) {
      var cohorteStr = String(filters.cohorte_activa).trim();
      filteredData = data.filter(function(p) {
        return String(p.cohorte).trim() === cohorteStr;
      });
      Logger.log('👥 Filtrando personal por cohorte: ' + cohorteStr + ' (' + filteredData.length + '/' + data.length + ')');
    }
  } catch (e) {
    Logger.log('⚠️ No se pudieron cargar filtros: ' + e.message);
  }
  
  var sheet = getOrCreateSheet_('datos_residentes');
  
  if (filteredData.length === 0) {
    SpreadsheetApp.getUi().alert('ℹ️ No hay datos de residentes.');
    return;
  }
  
  var headers = Object.keys(filteredData[0]);
  var rows = filteredData.map(function(r) {
    return headers.map(function(h) { return r[h] || ''; });
  });
  
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
 * Carga turnos en hoja "REF_TURNOS" (incluye columna activo y color)
 */
function loadTurnos() {
  var fields = 'id_turno,tipo_turno,descripcion,cant_horas,hora_inicio,hora_fin,activo,color';
  var data = fetchAll('turnos', fields);
  if (data.length === 0) return;
  
  var sheet = getOrCreateSheet_('REF_TURNOS');
  var headers = ['id_turno', 'tipo_turno', 'descripcion', 'cant_horas', 'hora_inicio', 'hora_fin', 'activo', 'color'];
  var rows = data.map(function(r) {
    return headers.map(function(h) { return r[h]; });
  });
  
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
  var ui = SpreadsheetApp.getUi();
  
  try {
    var filters = getActiveFilters();
    var anio = filters.año_activo;
    var data;
    
    if (anio) {
      data = fetchAllWithFilters('vista_estado_cobertura', '*', { anio: anio });
      Logger.log('📅 Filtrando estado cobertura por año: ' + anio);
    } else {
      data = fetchAll('vista_estado_cobertura', '*');
    }
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay datos de estado de cobertura' + (anio ? ' para el año ' + anio : '') + '.');
      return;
    }
    
    var sheet = getOrCreateSheet_('ESTADO_COBERTURA');
    
    var headers = Object.keys(data[0]);
    var rows = data.map(function(r) {
      return headers.map(function(h) { return r[h] || ''; });
    });
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
      .setFontWeight('bold').setBackground('#bf360c').setFontColor('#ffffff');
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      var estadoColIdx = headers.indexOf('estado');
      if (estadoColIdx !== -1) {
        var estadoCol = estadoColIdx + 1;
        
        var ruleIncomplete = SpreadsheetApp.newConditionalFormatRule()
          .whenTextDoesNotContain('completo')
          .setBackground('#fee2e2').setFontColor('#dc2626')
          .setRanges([sheet.getRange(2, estadoCol, rows.length, 1)])
          .build();
        
        var ruleComplete = SpreadsheetApp.newConditionalFormatRule()
          .whenTextContains('completo')
          .setBackground('#dcfce7').setFontColor('#166534')
          .setRanges([sheet.getRange(2, estadoCol, rows.length, 1)])
          .build();
        
        sheet.setConditionalFormatRules([ruleIncomplete, ruleComplete]);
      }
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    ui.alert('✅ Estado de cobertura actualizado: ' + rows.length + ' registros' + (anio ? ' (Año ' + anio + ')' : ''));
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}
