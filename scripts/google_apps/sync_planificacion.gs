/**
 * PLANIFICACION SYNC - Sincronización de guardia/turnos
 * Soporta sincronización selectiva (checkbox)
 * @author Pablo (Data Analyst)
 * @version 1.1.0 - Selective sync & time formatting
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN PLANIFICACION
// ============================================================================

/**
 * Sincroniza hoja PLANIFICACION con Supabase
 */
function syncPlanificacion() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('PLANIFICACION');
  
  if (!sheet) {
    ui.alert('❌ Hoja PLANIFICACION no encontrada.\n\nDescarga primero con "Descargar Planificación".');
    return;
  }
  
  // Analizar si hay selección manual
  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(h => String(h).toLowerCase().trim());
  const syncColIdx = headers.indexOf('sincronizar');
  
  let rowsToSync = [];
  let isSelective = false;
  
  if (syncColIdx !== -1) {
    // Buscar filas marcadas
    for (let i = 1; i < values.length; i++) {
      if (values[i][syncColIdx] === true) {
        rowsToSync.push({ index: i, data: values[i], rowNum: i + 1 });
      }
    }
    
    if (rowsToSync.length > 0) {
      isSelective = true;
    }
  }
  
  // Mensaje de confirmación dinámico
  let message = 'Se actualizarán:\n• Turnos y Residentes\n• Horarios (Inicio/Fin)\n';
  
  if (isSelective) {
    message += '\n✅ MODO SELECTIVO: Se sincronizarán solo las ' + rowsToSync.length + ' filas marcadas.';
  } else {
    // Si hay columna pero nada marcado
    if (syncColIdx !== -1) {
      const confirmAll = ui.alert(
        'Sincronizar Todo',
        'No has marcado ninguna casilla "sincronizar".\n¿Deseas sincronizar TODAS las filas (' + (values.length - 1) + ')?',
        ui.ButtonSet.YES_NO
      );
      if (confirmAll !== ui.Button.YES) return;
    }
    
    // Preparar todas las filas
    for (let i = 1; i < values.length; i++) {
        rowsToSync.push({ index: i, data: values[i], rowNum: i + 1 });
    }
    message += '\n⚠️ MODO COMPLETO: Se procesarán TODAS las filas.';
  }

  const result = ui.alert('Confirmar Sincronización', message, ui.ButtonSet.YES_NO);
  if (result !== ui.Button.YES) return;

  // Cargar referencias para lookup
  const diasMap = fetchAll('dias', 'id_dia,fecha'); // Para buscar id_dia por fecha
  const turnosMap = fetchAll('turnos', 'id_turno,tipo_turno'); // Para buscar id_turno por nombre
  
  // Crear índices
  const fechaToIdDia = {};
  diasMap.forEach(d => { fechaToIdDia[d.fecha] = d.id_dia; });
  
  // Helper para normalizar texto (quita tildes y pasa a minúsculas)
  const normalizeText = (str) => {
    return String(str).trim().toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  };
  
  const tipoToIdTurno = {};
  const tipoOriginal = {};  // Para guardar el nombre original
  turnosMap.forEach(t => { 
    const key = normalizeText(t.tipo_turno);
    tipoToIdTurno[key] = t.id_turno;
    tipoOriginal[key] = t.tipo_turno;
  });
  
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
  
  // Helper para formatear hora
  const formatTime_ = (val) => {
    if (!val) return null;
    if (val instanceof Date) {
      const h = String(val.getHours()).padStart(2, '0');
      const m = String(val.getMinutes()).padStart(2, '0');
      return h + ':' + m;
    }
    const s = String(val).trim();
    return s === '' ? null : s;
  };
  
  // Procesar filas seleccionadas
  rowsToSync.forEach(rowInfo => {
    const rowValues = rowInfo.data;
    const rowNum = rowInfo.rowNum;
    
    if (rowValues.every(v => v === '' || v === null)) return;
    
    // Construir objeto RECORD usando headers
    const record = {};
    headers.forEach((header, idx) => {
      if (header && rowValues[idx] !== '') {
        record[header] = rowValues[idx];
      }
    });
    
    // Lookup de IDs
    let id_dia = record.id_dia; 
    if (!id_dia && record.fecha) {
        const f = formatDate_(record.fecha);
        id_dia = fechaToIdDia[f];
    }
    
    let id_turno = record.id_turno;
    if (!id_turno && record.tipo_turno) {
        const keyNorm = normalizeText(record.tipo_turno);
        id_turno = tipoToIdTurno[keyNorm];
    }
    
    // Validar mandatorios con mensaje detallado
    if (!id_dia && !id_turno) {
       sheet.getRange(rowNum, statusCol).setValue('❌ Falta fecha Y tipo_turno válido');
       errorCount++;
       return;
    }
    if (!id_dia) {
       const fechaVal = record.fecha ? formatDate_(record.fecha) : '(vacío)';
       sheet.getRange(rowNum, statusCol).setValue('❌ Fecha no existe en DB: ' + fechaVal);
       errorCount++;
       return;
    }
    if (!id_turno) {
       const tipoVal = record.tipo_turno ? String(record.tipo_turno).trim() : '(vacío)';
       sheet.getRange(rowNum, statusCol).setValue('❌ Tipo turno no existe en DB: ' + tipoVal);
       errorCount++;
       return;
    }
    
    const payload = {
      id_dia: id_dia,
      id_turno: id_turno,
      cant_residentes_plan: record.cant_residentes_plan || 0,
      cant_visit: record.cant_visit || 0,
      hora_inicio: formatTime_(record.hora_inicio),
      hora_fin: formatTime_(record.hora_fin),
      cant_horas: record.cant_horas || null,
      lugar: record.lugar || null,
      grupo: record.grupo || null,
      plani_notas: record.plani_notas || null
    };
    
    // UPSERT (unique key: id_dia, id_turno)
    try {
      const res = upsertRecord('planificacion', payload, ['id_dia', 'id_turno']);
      
      if (res.success) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleTimeString());
        
        // Desmarcar checkbox si fue éxito selectivo
        if (isSelective && syncColIdx !== -1) {
            sheet.getRange(rowNum, syncColIdx + 1).setValue(false);
        }
        successCount++;
      } else {
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + res.error);
        errorCount++;
      }
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      errorCount++;
    }
  });
  
  // Invalida la caché de planificación
  if (successCount > 0) {
    try {
      const props = PropertiesService.getScriptProperties();
      props.deleteProperty('CACHE_META__CACHE_PLANI_ANIO');
      Logger.log('🔄 Caché _CACHE_PLANI_ANIO invalidada.');
    } catch (e) {
      Logger.log('⚠️ Error invalidando caché: ' + e.message);
    }
  }
  
  ui.alert('✅ Sincronización Completa\n\n' + successCount + ' registros procesados correctamente.');
}
