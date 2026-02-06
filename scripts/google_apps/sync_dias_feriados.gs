/**
 * DIAS_FERIADOS SYNC - Sincronización de marcas de feriados
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: DESCARGA DE FERIADOS PARA EDICIÓN
// ============================================================================

/**
 * Descarga días marcados como feriados en hoja DIAS_FERIADOS
 */
function downloadDiasFeriados() {
  const data = fetchAll('dias', 'id_dia,fecha,es_feriado,descripcion_feriado');
  
  if (!data || data.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️ No hay días en Supabase');
    return;
  }
  
  // Filtrar solo feriados o permitir editar todos (configurable)
  const filteredData = data; // Mostrar TODOS para poder marcar/desmarcar
  
  const sheet = getOrCreateSheet_('DIAS_FERIADOS');
  const headers = ['id_dia', 'fecha', 'es_feriado', 'descripcion_feriado', 'sync_status'];
  const rows = filteredData.map(r => [
    r.id_dia,
    r.fecha,
    r.es_feriado,
    r.descripcion_feriado || '',
    '' // sync_status
  ]);
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#34a853')
    .setFontColor('#ffffff');
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  
  // Formatear columna es_feriado con checkboxes
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 3, lastRow - 1, 1).insertCheckboxes();
  }
  
  // Congelar encabezados y fecha
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  
  Logger.log('✅ DIAS_FERIADOS descargados: ' + rows.length + ' registros');
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' días descargados.\n\nMarca/desmarca feriados y sincroniza.');
}

// ============================================================================
// MÓDULO: SINCRONIZACIÓN FERIADOS → SUPABASE
// ============================================================================

/**
 * Sincroniza hoja DIAS_FERIADOS con Supabase
 */
function syncDiasFeriados() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.alert(
    'Sincronizar Feriados',
    '¿Confirmas actualizar marcas de feriados en Supabase?\n\n' +
    'Solo se actualizan es_feriado y descripcion_feriado.',
    ui.ButtonSet.YES_NO
  );
  
  if (result !== ui.Button.YES) return;
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('DIAS_FERIADOS');
  
  if (!sheet) {
    ui.alert('❌ Hoja DIAS_FERIADOS no encontrada.\n\nDescarga primero con "Descargar Feriados".');
    return;
  }
  
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) {
    ui.alert('⚠️ La hoja DIAS_FERIADOS está vacía');
    return;
  }
  
  const headers = values[0].map(h => String(h).toLowerCase().trim());
  
  // Asegurar columna sync_status
  let statusColIdx = headers.indexOf('sync_status');
  if (statusColIdx === -1) {
    sheet.insertColumnAfter(sheet.getLastColumn());
    sheet.getRange(1, sheet.getLastColumn()).setValue('sync_status');
    headers.push('sync_status');
    statusColIdx = headers.length - 1;
  }
  const statusCol = statusColIdx + 1;
  
  let successCount = 0;
  let errorCount = 0;
  
  // Procesar filas
  for (let i = 1; i < values.length; i++) {
    const rowNum = i + 1;
    const rowValues = values[i];
    
    // Skip filas vacías
    if (rowValues.every(v => v === '' || v === null)) continue;
    
    // Construir objeto
    const record = {};
    headers.forEach((header, idx) => {
      if (header && rowValues[idx] !== '') {
        record[header] = rowValues[idx];
      }
    });
    
    // Validar id_dia o fecha
    if (!record.id_dia && !record.fecha) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Falta id_dia o fecha');
      errorCount++;
      continue;
    }
    
    // Preparar payload (solo campos editables)
    const payload = {
      es_feriado: record.es_feriado === true || record.es_feriado === 'TRUE',
      descripcion_feriado: record.descripcion_feriado || null
    };
    
    // UPDATE por id_dia (más eficiente)
    const idDia = record.id_dia;
    
    try {
      const config = getSupabaseConfig_();
      const url = config.url + '/rest/v1/dias?id_dia=eq.' + idDia;
      
      const options = {
        method: 'PATCH',
        headers: buildHeaders_(config.key),
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };
      
      const response = UrlFetchApp.fetch(url, options);
      const code = response.getResponseCode();
      
      if (code >= 200 && code < 300) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleDateString());
        successCount++;
      } else {
        sheet.getRange(rowNum, statusCol).setValue('❌ Error ' + code);
        errorCount++;
      }
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      errorCount++;
    }
  }
  
  ui.alert('✅ Sincronización completa\n\n' + 
           successCount + ' días actualizados\n' + 
           errorCount + ' errores');
  
  Logger.log('Sync feriados completado: ' + successCount + ' OK, ' + errorCount + ' errores');
}
