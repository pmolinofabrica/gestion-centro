/**
 * SYNC INASISTENCIAS - Sincronización de faltas y licencias
 * Soporta búsqueda de agentes por Nombre/DNI
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN INASISTENCIAS
// ============================================================================

function syncInasistencias() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('INASISTENCIAS');
  
  if (!sheet) {
    ui.alert('❌ Hoja INASISTENCIAS no encontrada.');
    return;
  }
  
  // 1. Analizar selección manual (Checkbox)
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
  
  // 2. Mensaje de confirmación
  let message = 'Se actualizarán las inasistencias en Supabase.\n';
  
  if (isSelective) {
     message += '\n✅ MODO SELECTIVO: ' + rowsToSync.length + ' registros marcados.';
  } else {
     // Si no hay selección, preguntar por todo (modo legacy)
     if (syncColIdx !== -1) {
        const confirmAll = ui.alert(
          'Sincronizar Todo',
          'No has marcado ninguna casilla. ¿Sincronizar TODO?',
          ui.ButtonSet.YES_NO
        );
        if (confirmAll !== ui.Button.YES) return;
     }
     // Cargar todo
     for (let i = 1; i < values.length; i++) {
        rowsToSync.push({ index: i, data: values[i], rowNum: i+1 });
     }
     message += '\n⚠️ MODO COMPLETO: Todos los registros.';
  }
  
  const result = ui.alert('Confirmar Sync Inasistencias', message, ui.ButtonSet.YES_NO);
  if (result !== ui.Button.YES) return;
  
  // 3. Cargar Lookups (Agentes)
  const agentesList = getCacheData('_CACHE_PERSONAL', false); // Cache local
  
  // Lookup DNI -> ID
  const dniToId = {};
  const nombreToId = {};
  
  agentesList.forEach(a => {
    dniToId[String(a.dni).trim()] = a.id_agente;
    const nameKey = (a.apellido + ' ' + a.nombre).toLowerCase().trim();
    nombreToId[nameKey] = a.id_agente;
  });
  
  // Asegurar status col
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
  
  // 4. Helper Dates
  const formatDate_ = (val) => {
    if (val instanceof Date) {
      return Utilities.formatDate(val, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    }
    return String(val);
  };
  
  // 5. Procesar filas
  rowsToSync.forEach(rowInfo => {
    const rowValues = rowInfo.data;
    const rowNum = rowInfo.rowNum;
    
    if (rowValues.every(v => v === '' || v === null)) return;
    
    // Mapear headers
    const record = {};
    headers.forEach((h, idx) => {
        if (h && rowValues[idx] !== '') record[h] = rowValues[idx];
    });
    
    // Resolver ID Agente
    let id_agente = record.id_agente;
    if (!id_agente && (record.dni || record.agente)) {
        // Intentar DNI
        if (record.dni) {
             const dniLimpio = String(record.dni).replace(/\D/g,'');
             id_agente = dniToId[dniLimpio];
        }
        // Intentar Nombre
        if (!id_agente && record.agente) {
            const n = String(record.agente).toLowerCase().trim().replace(/\s+/g,' ');
            id_agente = nombreToId[n];
        }
    }
    
    if (!id_agente) {
        sheet.getRange(rowNum, statusCol).setValue('❌ Agente no identificado');
        errorCount++;
        return;
    }
    
    if (!record.fecha_inasistencia) {
        sheet.getRange(rowNum, statusCol).setValue('❌ Falta fecha');
        errorCount++;
        return;
    }
    
    // Construir Payload DAMA-compliant
    const payload = {
        id_agente: id_agente,
        fecha_inasistencia: formatDate_(record.fecha_inasistencia),
        motivo: record.motivo || 'imprevisto',
        estado: record.estado || 'pendiente',
        observaciones: record.observaciones || null,
        // requiere_certificado: se deja automático por trigger DB a menos que se fuerce
    };
    
    // Si tiene ID, es update
    if (record.id_inasistencia) {
        payload.id_inasistencia = record.id_inasistencia;
    }
    
    const uniqueKey = record.id_inasistencia ? 'id_inasistencia' : null; 
    // Si no hay ID, es INSERT. No hay unique constraint fuerte en (agente, fecha) en DB schema?
    // Verificamos schema: No hay UNIQUE(id_agente, fecha_inasistencia) en inasistencias.
    // DAMA: Deberíamos usar UPSERT por id_inasistencia si existe, o INSERT si no.
    
    try {
        let res;
        if (uniqueKey) {
            res = upsertRecord('inasistencias', payload, uniqueKey);
        } else {
            // INSERT puro si es nuevo
            // O usaremos una búsqueda previa? Mejor usar REST POST normal
            res = supabaseRequest_('inasistencias', '', 'POST', payload);
            // supabaseRequest_ devuelve objeto {success, code}
            if (res.code === 201) res.success = true;
        }
        
        if (res.success) {
             sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleTimeString());
             if (isSelective && syncColIdx !== -1) {
                 sheet.getRange(rowNum, syncColIdx + 1).setValue(false);
             }
             successCount++;
        } else {
             const err = res.error || ('HTTP ' + res.code);
             sheet.getRange(rowNum, statusCol).setValue('❌ ' + err);
             errorCount++;
        }
        
    } catch(e) {
         sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
         errorCount++;
    }
  });
  
  if (successCount > 0) {
      // Refresh cache si existiera cache de inasistencias (aún no)
      // refreshCache('_CACHE_KPI_INASISTENCIAS'); 
  }
  
  ui.alert('✅ Sync Inasistencias completado: ' + successCount + ' OK');
}
