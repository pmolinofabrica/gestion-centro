/**
 * SYNC MODULE - Sincronización bidireccional Sheets ↔ Supabase
 * DAMA Compliant: Validación antes de escritura
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN SHEETS → SUPABASE
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
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) {
    throw new Error('❌ Hoja no encontrada: ' + sheetName);
  }
  
  const config = getTableConfig(tableName);
  if (!config) {
    throw new Error('❌ Tabla no configurada: ' + tableName);
  }
  
  // Obtener datos
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();
  const headers = values[0].map(h => String(h).toLowerCase().trim());
  const dataStartRow = startRow || 2;
  
  // Preparar columna de status (si no existe, crearla)
  const statusColIndex = headers.indexOf('sync_status');
  const hasStatusCol = statusColIndex !== -1;
  
  if (!hasStatusCol) {
    sheet.insertColumnAfter(sheet.getLastColumn());
    sheet.getRange(1, sheet.getLastColumn()).setValue('sync_status');
    headers.push('sync_status');
  }
  
  const statusCol = hasStatusCol ? statusColIndex + 1 : sheet.getLastColumn();
  
  // Procesar filas
  const results = {
    success: 0,
    errors: []
  };
  
  for (let i = dataStartRow - 1; i < values.length; i++) {
    const rowNum = i + 1;
    const rowValues = values[i];
    
    // Skip filas vacías
    if (rowValues.every(v => v === '' || v === null)) {
      continue;
    }
    
    // Construir objeto
    const record = {};
    headers.forEach((header, idx) => {
      if (header && header !== 'sync_status' && rowValues[idx] !== '') {
        record[header] = rowValues[idx];
      }
    });
    
    // Validar DAMA
    const validation = validateRecord(tableName, record);
    
    if (!validation.valid) {
      const errorMsg = '❌ ' + validation.errors.join(', ');
      sheet.getRange(rowNum, statusCol).setValue(errorMsg);
      results.errors.push({row: rowNum, errors: validation.errors});
      continue;
    }
    
    // Intentar upsert
    try {
      const upsertResult = upsertRecord(tableName, record, config.unique_key);
      
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

/**
 * Upsert genérico (insert o update)
 * @private
 */
function upsertRecord(table, record, uniqueKey) {
  const config = getSupabaseConfig_();
  
  // Construir query para unique constraint
  let conflictClause = '';
  if (Array.isArray(uniqueKey)) {
    conflictClause = uniqueKey.join(',');
  } else {
    conflictClause = uniqueKey;
  }
  
  const url = config.url + '/rest/v1/' + table + 
    (conflictClause ? '?on_conflict=' + conflictClause : '');
  
  const options = {
    method: 'POST',
    headers: buildHeaders_(config.key),
    payload: JSON.stringify(record),
    muteHttpExceptions: true
  };
  
  // Agregar header para upsert
  options.headers['Prefer'] = 'resolution=merge-duplicates';
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  if (code >= 200 && code < 300) {
    return {success: true};
  } else {
    return {success: false, error: 'HTTP ' + code + ': ' + body.substring(0, 100)};
  }
}

// ============================================================================
// MÓDULO: FUNCIONES DE MENÚ
// ============================================================================

/**
 * Sincroniza hoja DATOS_PERSONALES
 */
function syncDatosPersonales() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.alert(
    'Sincronizar Datos Personales',
    '¿Confirmas sincronizar DATOS_PERSONALES con Supabase?',
    ui.ButtonSet.YES_NO
  );
  
  if (result === ui.Button.YES) {
    try {
      const res = syncSheetToSupabase('DATOS_PERSONALES', 'datos_personales');
      ui.alert('✅ Sincronización completa\\n' + res.success + ' registros OK\\n' + res.errors.length + ' errores');
    } catch (e) {
      ui.alert('❌ Error: ' + e.message);
    }
  }
}

/**
 * Sincroniza hoja PLANIFICACION
 */
function syncPlanificacion() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.alert(
    'Sincronizar Planificación',
    '¿Confirmas sincronizar PLANIFICACION con Supabase?',
    ui.ButtonSet.YES_NO
  );
  
  if (result === ui.Button.YES) {
    try {
      // Primero necesitamos resolver los mapeos de id_dia y id_turno
      const res = syncPlanificacionWithMappings();
      ui.alert('✅ Sincronización completa\\n' + res.success + ' registros OK\\n' + res.errors.length + ' errores');
    } catch (e) {
      ui.alert('❌ Error: ' + e.message);
    }
  }
}

/**
 * Sincronización especial para planificación con resolución de IDs
 * @private
 */
function syncPlanificacionWithMappings() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('PLANIFICACION');
  
  if (!sheet) {
    throw new Error('❌ Hoja PLANIFICACION no encontrada');
  }
  
  // Obtener mapeos de referencia
  const diasMap = fetchAll('dias', 'id_dia,fecha');
  const turnosMap = fetchAll('turnos', 'id_turno,tipo_turno');
  
  // Crear lookup tables
  const fechaToIdDia = {};
  diasMap.forEach(d => {
    fechaToIdDia[d.fecha] = d.id_dia;
  });
  
  const tipoToIdTurno = {};
  turnosMap.forEach(t => {
    tipoToIdTurno[t.tipo_turno] = t.id_turno;
  });
  
  // Obtener datos de la hoja
  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(h => String(h).toLowerCase().trim());
  
  const results = {success: 0, errors: []};
  
  // Procesar filas
  for (let i = 1; i < values.length; i++) {
    const rowNum = i + 1;
    const rowValues = values[i];
    
    if (rowValues.every(v => v === '' || v === null)) continue;
    
    const record = {};
    headers.forEach((header, idx) => {
      if (header && rowValues[idx] !== '') {
        record[header] = rowValues[idx];
      }
    });
    
    // Resolver IDs
    if (record.fecha) {
      const fechaStr = formatDate_(record.fecha);
      record.id_dia = fechaToIdDia[fechaStr];
      if (!record.id_dia) {
        sheet.getRange(rowNum, headers.indexOf('sync_status') + 1).setValue('❌ Fecha no encontrada en tabla dias');
        results.errors.push({row: rowNum, errors: ['Fecha no encontrada']});
        continue;
      }
    }
    
    if (record.tipo_turno) {
      record.id_turno = tipoToIdTurno[record.tipo_turno];
      if (!record.id_turno) {
        sheet.getRange(rowNum, headers.indexOf('sync_status') + 1).setValue('❌ Tipo turno no encontrado');
        results.errors.push({row: rowNum, errors: ['Tipo turno no encontrado']});
        continue;
      }
    }
    
    // Limpiar campos que no van a la DB
    delete record.fecha;
    delete record.tipo_turno;
    
    // Upsert
    try {
      const res = upsertRecord('planificacion', record, ['id_dia', 'id_turno']);
      if (res.success) {
        sheet.getRange(rowNum, headers.indexOf('sync_status') + 1).setValue('✅ OK');
        results.success++;
      } else {
        sheet.getRange(rowNum, headers.indexOf('sync_status') + 1).setValue('❌ ' + res.error);
        results.errors.push({row: rowNum, errors: [res.error]});
      }
    } catch (e) {
      sheet.getRange(rowNum, headers.indexOf('sync_status') + 1).setValue('❌ ' + e.message);
      results.errors.push({row: rowNum, errors: [e.message]});
    }
  }
  
  return results;
}

/**
 * Formatea fecha a YYYY-MM-DD
 * @private
 */
function formatDate_(dateValue) {
  if (dateValue instanceof Date) {
    return Utilities.formatDate(dateValue, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  return String(dateValue);
}

// ============================================================================
// MÓDULO: LIMPIEZA Y UTILIDADES
// ============================================================================

/**
 * Limpia columna sync_status de una hoja
 */
function clearSyncStatus(sheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) return;
  
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const statusIdx = headers.findIndex(h => String(h).toLowerCase() === 'sync_status');
  
  if (statusIdx !== -1) {
    const statusCol = statusIdx + 1;
    sheet.getRange(2, statusCol, sheet.getLastRow() - 1, 1).clearContent();
    Logger.log('✅ Columna sync_status limpiada en ' + sheetName);
  }
}
