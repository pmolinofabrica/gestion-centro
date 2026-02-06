/**
 * TURNOS SYNC - Sincronización bidireccional de tipos de turno
 * @author Pablo (Data Analyst)
 * @version 1.1.0 - Fixed column names to match Supabase schema
 */

// ============================================================================
// MÓDULO: DESCARGA DE TURNOS PARA EDICIÓN
// ============================================================================

/**
 * Descarga turnos en hoja TURNOS para edición
 * NOTA: Columnas reales en Supabase: cant_horas, hora_inicio, hora_fin (sin _default)
 */
function downloadTurnos() {
  const data = fetchAll('turnos', 'id_turno,tipo_turno,descripcion,hora_inicio,hora_fin,cant_horas,solo_semana,activo');
  
  if (!data || data.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️ No hay turnos en Supabase');
    return;
  }
  
  const sheet = getOrCreateSheet_('TURNOS');
  const headers = ['id_turno', 'tipo_turno', 'descripcion', 'hora_inicio', 'hora_fin', 
                   'cant_horas', 'solo_semana', 'activo', 'sync_status'];
  const rows = data.map(r => {
    return [
      r.id_turno,
      r.tipo_turno,
      r.descripcion || '',
      r.hora_inicio || '',
      r.hora_fin || '',
      r.cant_horas,
      r.solo_semana,
      r.activo,
      '' // sync_status vacío
    ];
  });
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#4285f4')
    .setFontColor('#ffffff');
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  
  // Formatear columnas booleanas
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 7, lastRow - 1, 1).insertCheckboxes(); // solo_semana
    sheet.getRange(2, 8, lastRow - 1, 1).insertCheckboxes(); // activo
  }
  
  Logger.log('✅ TURNOS descargados: ' + rows.length + ' registros');
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' turnos descargados en hoja TURNOS');
}

// ============================================================================
// MÓDULO: SINCRONIZACIÓN TURNOS → SUPABASE
// ============================================================================

/**
 * Sincroniza hoja TURNOS con Supabase
 */
function syncTurnos() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.alert(
    'Sincronizar Turnos',
    '¿Confirmas sincronizar TURNOS con Supabase?\n\n' +
    'Esto creará/actualizará turnos según tipo_turno.',
    ui.ButtonSet.YES_NO
  );
  
  if (result !== ui.Button.YES) return;
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('TURNOS');
  
  if (!sheet) {
    ui.alert('❌ Hoja TURNOS no encontrada.\n\nCrea una hoja llamada TURNOS o descarga primero con "Descargar Turnos".');
    return;
  }
  
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) {
    ui.alert('⚠️ La hoja TURNOS está vacía');
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
    
    // Validar campo obligatorio
    if (!record.tipo_turno) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Falta tipo_turno');
      errorCount++;
      continue;
    }
    
    // Preparar payload con nombres correctos
    const payload = {
      tipo_turno: String(record.tipo_turno).trim(),
      descripcion: record.descripcion || null,
      hora_inicio: record.hora_inicio || null,
      hora_fin: record.hora_fin || null,
      cant_horas: record.cant_horas ? parseFloat(record.cant_horas) : null,
      solo_semana: record.solo_semana === true || record.solo_semana === 'TRUE',
      activo: record.activo === true || record.activo === 'TRUE' || record.activo === undefined
    };
    
    // UPSERT
    try {
      const res = upsertRecord('turnos', payload, ['tipo_turno']);
      
      if (res.success) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleDateString());
        successCount++;
      } else {
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + res.error);
        errorCount++;
      }
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      errorCount++;
    }
  }
  
  ui.alert('✅ Sincronización completa\n\n' + 
           successCount + ' turnos OK\n' + 
           errorCount + ' errores');
  
  Logger.log('Sync completado: ' + successCount + ' OK, ' + errorCount + ' errores');
}
