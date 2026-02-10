/**
 * SYNC CONVOCATORIA - Sincronización de convocatorias a Supabase
 * Soporta sincronización selectiva (checkbox)
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN CONVOCATORIA
// ============================================================================

/**
 * Sincroniza hoja CONVOCATORIA con Supabase
 * Usa el mismo patrón checkbox-selectivo que syncPlanificacion e syncInasistencias
 */
function syncConvocatoria() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('CONVOCATORIA');
  
  if (!sheet) {
    ui.alert('❌ Hoja CONVOCATORIA no encontrada.\n\nDescarga primero con "Descargar Convocatoria".');
    return;
  }
  
  // 1. Analizar selección manual (Checkbox)
  var values = sheet.getDataRange().getValues();
  var headers = values[0].map(function(h) { return String(h).toLowerCase().trim(); });
  var syncColIdx = headers.indexOf('sincronizar');
  
  var rowsToSync = [];
  var isSelective = false;
  
  if (syncColIdx !== -1) {
    for (var i = 1; i < values.length; i++) {
      if (values[i][syncColIdx] === true) {
        rowsToSync.push({ index: i, data: values[i], rowNum: i + 1 });
      }
    }
    if (rowsToSync.length > 0) isSelective = true;
  }
  
  // 2. Mensaje de confirmación
  var message = 'Se actualizarán las convocatorias en Supabase.\n';
  
  if (isSelective) {
    message += '\n✅ MODO SELECTIVO: ' + rowsToSync.length + ' registros marcados.';
  } else {
    if (syncColIdx !== -1) {
      var confirmAll = ui.alert(
        'Sincronizar Todo',
        'No has marcado ninguna casilla. ¿Sincronizar TODO?',
        ui.ButtonSet.YES_NO
      );
      if (confirmAll !== ui.Button.YES) return;
    }
    for (var i = 1; i < values.length; i++) {
      rowsToSync.push({ index: i, data: values[i], rowNum: i + 1 });
    }
    message += '\n⚠️ MODO COMPLETO: Todos los registros.';
  }
  
  var result = ui.alert('Confirmar Sync Convocatoria', message, ui.ButtonSet.YES_NO);
  if (result !== ui.Button.YES) return;
  
  // 3. Cargar Lookups
  var agentesList = getCacheData('_CACHE_PERSONAL', false);
  
  var dniToId = {};
  var nombreToId = {};
  agentesList.forEach(function(a) {
    dniToId[String(a.dni).trim()] = a.id_agente;
    var nameKey = (a.apellido + ' ' + a.nombre).toLowerCase().trim();
    nombreToId[nameKey] = a.id_agente;
  });
  
  // 4. Asegurar status col
  var statusColIdx = headers.indexOf('sync_status');
  if (statusColIdx === -1) {
    sheet.insertColumnAfter(sheet.getLastColumn());
    sheet.getRange(1, sheet.getLastColumn()).setValue('sync_status');
    headers.push('sync_status');
    statusColIdx = headers.length - 1;
  }
  var statusCol = statusColIdx + 1;
  
  var successCount = 0;
  var errorCount = 0;
  
  // 5. Procesar filas
  rowsToSync.forEach(function(rowInfo) {
    var rowValues = rowInfo.data;
    var rowNum = rowInfo.rowNum;
    
    if (rowValues.every(function(v) { return v === '' || v === null; })) return;
    
    // Mapear headers a record
    var record = {};
    headers.forEach(function(h, idx) {
      if (h && rowValues[idx] !== '') record[h] = rowValues[idx];
    });
    
    // Resolver ID Agente
    var id_agente = record.id_agente;
    if (!id_agente && (record.dni || record.agente)) {
      if (record.dni) {
        var dniLimpio = String(record.dni).replace(/\D/g, '');
        id_agente = dniToId[dniLimpio];
      }
      if (!id_agente && record.agente) {
        var n = String(record.agente).toLowerCase().trim().replace(/\s+/g, ' ');
        id_agente = nombreToId[n];
      }
    }
    
    if (!id_agente) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Agente no identificado');
      errorCount++;
      return;
    }
    
    if (!record.id_plani) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Falta id_plani');
      errorCount++;
      return;
    }
    
    // Construir payload
    var payload = {
      id_agente: parseInt(id_agente),
      id_plani: parseInt(record.id_plani),
      id_turno: record.id_turno ? parseInt(record.id_turno) : null,
      estado: record.estado || 'convocada',
      turno_cancelado: record.turno_cancelado === 'Sí' || record.turno_cancelado === true,
      motivo_cambio: record.motivo_cambio || null
    };
    
    // Si tiene ID, es update
    if (record.id_convocatoria) {
      payload.id_convocatoria = parseInt(record.id_convocatoria);
    }
    
    var uniqueKey = record.id_convocatoria ? 'id_convocatoria' : null;
    
    try {
      var res;
      if (uniqueKey) {
        res = upsertRecord('convocatoria', payload, uniqueKey);
      } else {
        // INSERT puro si es nuevo
        res = supabaseRequest_('convocatoria', '', 'POST', payload);
        if (res.code === 201) res.success = true;
      }
      
      if (res.success) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleTimeString());
        if (isSelective && syncColIdx !== -1) {
          sheet.getRange(rowNum, syncColIdx + 1).setValue(false);
        }
        successCount++;
      } else {
        var err = res.error || ('HTTP ' + res.code);
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + err);
        errorCount++;
      }
      
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      errorCount++;
    }
  });
  
  ui.alert('✅ Sync Convocatoria completado: ' + successCount + ' OK, ' + errorCount + ' errores');
}
