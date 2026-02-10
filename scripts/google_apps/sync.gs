/**
 * SYNC MODULE - Sincronización genérica Sheets → Supabase
 * DAMA Compliant: Validación antes de escritura
 * 
 * @author Pablo (Data Analyst)
 * @version 2.0.0 - Refactored: removed duplicates (syncPlanificacion → sync_planificacion.gs)
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN GENÉRICA SHEETS → SUPABASE
// ============================================================================

/**
 * Sincroniza una hoja de Google Sheets con una tabla de Supabase.
 * Usa UPSERT para insertar o actualizar registros.
 * 
 * @param {string} sheetName - Nombre de la hoja
 * @param {string} tableName - Nombre de la tabla Supabase
 * @param {number} startRow - Fila de inicio de datos (default: 2)
 * @returns {Object} {success: number, errors: Array}
 */
function syncSheetToSupabase(sheetName, tableName, startRow) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) {
    throw new Error('❌ Hoja no encontrada: ' + sheetName);
  }
  
  var config = getTableConfig(tableName);
  if (!config) {
    throw new Error('❌ Tabla no configurada: ' + tableName);
  }
  
  var dataRange = sheet.getDataRange();
  var values = dataRange.getValues();
  var headers = values[0].map(function(h) { return String(h).toLowerCase().trim(); });
  var dataStartRow = startRow || 2;
  
  // Preparar columna de status
  var statusColIndex = headers.indexOf('sync_status');
  var hasStatusCol = statusColIndex !== -1;
  
  if (!hasStatusCol) {
    sheet.insertColumnAfter(sheet.getLastColumn());
    sheet.getRange(1, sheet.getLastColumn()).setValue('sync_status');
    headers.push('sync_status');
  }
  
  var statusCol = hasStatusCol ? statusColIndex + 1 : sheet.getLastColumn();
  
  var results = {
    success: 0,
    errors: []
  };
  
  for (var i = dataStartRow - 1; i < values.length; i++) {
    var rowNum = i + 1;
    var rowValues = values[i];
    
    if (rowValues.every(function(v) { return v === '' || v === null; })) {
      continue;
    }
    
    // Construir objeto
    var record = {};
    headers.forEach(function(header, idx) {
      if (header && header !== 'sync_status' && rowValues[idx] !== '') {
        record[header] = rowValues[idx];
      }
    });
    
    // Validar DAMA
    var validation = validateRecord(tableName, record);
    
    if (!validation.valid) {
      var errorMsg = '❌ ' + validation.errors.join(', ');
      sheet.getRange(rowNum, statusCol).setValue(errorMsg);
      results.errors.push({row: rowNum, errors: validation.errors});
      continue;
    }
    
    // Intentar upsert
    try {
      var upsertResult = upsertRecord(tableName, record, config.unique_key);
      
      if (upsertResult.success) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleDateString());
        results.success++;
      } else {
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + upsertResult.error);
        results.errors.push({row: rowNum, errors: [upsertResult.error]});
      }
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      results.errors.push({row: rowNum, errors: [e.message]});
    }
  }
  
  Logger.log('Sync completado: ' + results.success + ' OK, ' + results.errors.length + ' errores');
  return results;
}

// ============================================================================
// MÓDULO: FUNCIONES DE MENÚ (Sync específicos)
// ============================================================================

/**
 * Sincroniza hoja DATOS_PERSONALES
 */
function syncDatosPersonales() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert(
    'Sincronizar Datos Personales',
    '¿Confirmas sincronizar DATOS_PERSONALES con Supabase?',
    ui.ButtonSet.YES_NO
  );
  
  if (result === ui.Button.YES) {
    try {
      var res = syncSheetToSupabase('DATOS_PERSONALES', 'datos_personales');
      ui.alert('✅ Sincronización completa\n' + res.success + ' registros OK\n' + res.errors.length + ' errores');
    } catch (e) {
      ui.alert('❌ Error: ' + e.message);
    }
  }
}

// ============================================================================
// MÓDULO: LIMPIEZA Y UTILIDADES
// ============================================================================

/**
 * Limpia columna sync_status de una hoja
 */
function clearSyncStatus(sheetName) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) return;
  
  var values = sheet.getDataRange().getValues();
  var headers = values[0];
  var statusIdx = headers.findIndex(function(h) { return String(h).toLowerCase() === 'sync_status'; });
  
  if (statusIdx !== -1) {
    var statusCol = statusIdx + 1;
    sheet.getRange(2, statusCol, sheet.getLastRow() - 1, 1).clearContent();
    Logger.log('✅ Columna sync_status limpiada en ' + sheetName);
  }
}
