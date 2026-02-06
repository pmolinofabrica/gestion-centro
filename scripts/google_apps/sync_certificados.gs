/**
 * SYNC CERTIFICADOS - Gestión de certificados médicos/académicos
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

function syncCertificados() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('CERTIFICADOS');
  
  if (!sheet) {
    ui.alert('❌ Hoja CERTIFICADOS no encontrada.');
    return;
  }
  
  // 1. Selector
  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(h => String(h).toLowerCase().trim());
  const syncColIdx = headers.indexOf('sincronizar');
  
  let rowsToSync = [];
  let isSelective = false;
  
  if (syncColIdx !== -1) {
    for (let i = 1; i < values.length; i++) {
        if (values[i][syncColIdx] === true) {
            rowsToSync.push({ index: i, data: values[i], rowNum: i+1 });
        }
    }
    if (rowsToSync.length > 0) isSelective = true;
  }
  
  // Prompt
  let message = 'Se actualizarán Certificados en Supabase.\n';
  if (isSelective) {
     message += '✅ MODO SELECTIVO: ' + rowsToSync.length + ' filas.';
  } else {
     if (syncColIdx !== -1) {
         if (ui.alert('Sync Todo', 'No hay selección. ¿Sync Todo?', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
     }
     for (let i = 1; i < values.length; i++) rowsToSync.push({ index: i, data: values[i], rowNum: i+1 });
  }

  if (ui.alert('Confirmar', message, ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  
  // Helpers
  const formatDate_ = (val) => {
    if (val instanceof Date) return Utilities.formatDate(val, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    return String(val);
  };
  
  // Status col
  let statusColIdx = headers.indexOf('sync_status');
  if (statusColIdx === -1) {
    sheet.insertColumnAfter(sheet.getLastColumn());
    headers.push('sync_status');
    statusColIdx = headers.length - 1;
  }
  const statusCol = statusColIdx + 1;
  
  let success = 0;
  
  // Process
  rowsToSync.forEach(rowInfo => {
    const rowValues = rowInfo.data;
    const rowNum = rowInfo.rowNum;
    
    // Map record
    const record = {};
    headers.forEach((h, idx) => { if (h && rowValues[idx] !== '') record[h] = rowValues[idx]; });
    
    if (!record.id_inasistencia && !record.id_certificado) {
        sheet.getRange(rowNum, statusCol).setValue('❌ Falta ID Referencia (Inasistencia o Certificado)');
        return;
    }
    
    const payload = {
        id_agente: record.id_agente,
        id_inasistencia: record.id_inasistencia,
        fecha_entrega_certificado: formatDate_(record.fecha_entrega),
        fecha_inasistencia_justifica: formatDate_(record.fecha_justificada),
        tipo_certificado: record.tipo || 'medico',
        estado_certificado: record.estado || 'presentado',
        observaciones: record.observaciones || null
    };
    
    if (record.id_certificado) payload.id_certificado = record.id_certificado;
    
    const uniqueKey = record.id_certificado ? 'id_certificado' : null;
    
    try {
        let res;
        if (uniqueKey) {
            res = upsertRecord('certificados', payload, uniqueKey);
        } else {
            // New certificate
            res = supabaseRequest_('certificados', '', 'POST', payload);
            if (res.code === 201) res.success = true;
        }
        
        if (res.success) {
            sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleTimeString());
            if (isSelective && syncColIdx !== -1) sheet.getRange(rowNum, syncColIdx + 1).setValue(false);
            success++;
        } else {
            sheet.getRange(rowNum, statusCol).setValue('❌ ' + (res.error || res.code));
        }
    } catch(e) {
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
    }
  });
  
  ui.alert('✅ Sync Certificados: ' + success + ' procesados.');
}
