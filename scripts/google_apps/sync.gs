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
        var val = rowValues[idx];
        
        // Manejo de Fechas (Google Sheets devuelve Date objects)
        if (val instanceof Date) {
          var colType = (config.types && config.types[header]) ? config.types[header] : null;
          
          if (colType === 'date') {
            // Formato YYYY-MM-DD para columnas tipo date
            val = Utilities.formatDate(val, Session.getScriptTimeZone(), 'yyyy-MM-dd');
          } else {
            // Default para datetime o timestamp (ISO 8601 compatible)
            val = Utilities.formatDate(val, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
          }
        }
        
        record[header] = val;
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
/**
 * Sincroniza hoja DATOS_PERSONALES (Manejo de 2 tablas)
 */
function syncDatosPersonales() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert(
    'Sincronizar Datos Personales',
    '¿Confirmas sincronizar DATOS_PERSONALES con Supabase?\nEsto actualizará tanto datos básicos como adicionales.',
    ui.ButtonSet.YES_NO
  );
  
  if (result !== ui.Button.YES) return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('datos_personales'); // Nombre estandarizado
  if (!sheet) {
    ui.alert('❌ No se encuentra la hoja "datos_personales". Ejecuta "Actualizar Datos Personales" primero.');
    return;
  }

  var dataRange = sheet.getDataRange();
  var values = dataRange.getValues();
  var headers = values[0].map(function(h) { return String(h).trim(); }); // Mantener case original para keys si coincide con DB
  
  // Identificar índices de columnas
  var statusIdx = headers.indexOf('sync_status');
  if (statusIdx === -1) {
    statusIdx = headers.length;
    sheet.getRange(1, statusIdx + 1).setValue('sync_status');
  }
  
  // Configs
  var configMain = getTableConfig('datos_personales');
  var configExtra = getTableConfig('datos_personales_adicionales');
  
  if (!configMain || !configExtra) {
    ui.alert('❌ Error de configuración de tablas en script.');
    return;
  }

  var stats = { success: 0, errors: 0 };

  for (var i = 1; i < values.length; i++) {
    var row = values[i];
    // Saltar filas vacías
    if (row.every(function(c) { return c === ''; })) continue;
    
    var record = {};
    headers.forEach(function(h, idx) {
      if (idx !== statusIdx && h) {
        var val = row[idx];
        
        // Determinar tipo de dato
        var colType = (configMain.types && configMain.types[h]) 
                   || (configExtra.types && configExtra.types[h]) 
                   || 'str';

        // Manejo de Fechas (Google Sheets devuelve Date objects)
        if (val instanceof Date) {
             val = Utilities.formatDate(val, Session.getScriptTimeZone(), 'yyyy-MM-dd');
        }
        
        // Manejo de Strings vacíos para tipos NO string (int, float, date, bool)
        // PostgreSQL rechaza "" para integer/date
        if (val === '' && colType !== 'str') {
          val = null;
        }

        record[h] = val;
      }
    });

    // Separar datos
    var dataMain = {};
    var dataExtra = {};
    
    // Campos de Main (datos_personales)
    Object.keys(configMain.types).forEach(function(k) {
      if (record.hasOwnProperty(k)) dataMain[k] = record[k];
    });
    
    // Campos de Extra (datos_personales_adicionales) - Excluyendo id_agente que se asigna dinámicamente
    Object.keys(configExtra.types).forEach(function(k) {
      if (k !== 'id_agente' && record.hasOwnProperty(k)) dataExtra[k] = record[k];
    });

    try {
      // 1. Upsert Main
      // IMPORTANTE: unique_key 'dni' para encontrar/actualizar
      // Si el ID viene vacío en hoja, Supabase lo genera o busca por DNI
      var resMain = upsertRecord('datos_personales', dataMain, 'dni');
      
      if (!resMain.success) {
        throw new Error('Main: ' + resMain.error);
      }
      
      // Obtener ID (Upsert devuelve array, tomamos el primero)
      var idAgente = null;
      if (resMain.data && resMain.data.length > 0) {
        idAgente = resMain.data[0].id_agente;
      } else if (dataMain.id_agente) {
        idAgente = dataMain.id_agente;
      }
      
      if (!idAgente) {
         // Si no devolvió data y no teniamos ID, intentar fetch por DNI
         var existing = fetchOne('datos_personales', 'id_agente', { dni: dataMain.dni });
         if (existing) idAgente = existing.id_agente;
      }

      if (!idAgente) {
        throw new Error('No se pudo obtener ID del agente tras guardar.');
      }

      // 2. Upsert Extra
      // Solo si hay datos extra para guardar
      var hasExtraData = Object.keys(dataExtra).some(function(k) { return dataExtra[k] !== '' && dataExtra[k] !== null; });
      
      if (hasExtraData) {
        dataExtra.id_agente = idAgente;
        var resExtra = upsertRecord('datos_personales_adicionales', dataExtra, 'id_agente');
        if (!resExtra.success) {
           throw new Error('Extra: ' + resExtra.error); // Warn pero cuenta como éxito parcial? No, error.
        }
      }
      
      sheet.getRange(i + 1, statusIdx + 1).setValue('✅ OK');
      stats.success++;
      
    } catch (e) {
      sheet.getRange(i + 1, statusIdx + 1).setValue('❌ ' + e.message);
      stats.errors++;
    }
  }
  
  ui.alert('Sincronización Finalizada\n✅ Éxitos: ' + stats.success + '\n❌ Errores: ' + stats.errors);
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
