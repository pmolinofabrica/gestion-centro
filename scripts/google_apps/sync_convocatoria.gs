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
  
  // 3. Cargar Lookups (Personas, Días, Turnos, Planificación)
  var agentesList = getCacheData('_CACHE_PERSONAL', false);
  
  var dniToId = {};
  var nombreToId = {};
  agentesList.forEach(function(a) {
    dniToId[String(a.dni).trim()] = a.id_agente;
    var nameKey = (a.apellido + ' ' + a.nombre).toLowerCase().trim();
    nombreToId[nameKey] = a.id_agente;
  });

  // Cargar Días y Turnos para resolver ID Plani
  var diasData = fetchAll('dias', 'id_dia,fecha');
  var turnosData = fetchAll('turnos', 'id_turno,tipo_turno');
  var planiData = fetchAll('planificacion', 'id_plani,id_dia,id_turno,grupo');

  var dateToIdDia = {};
  diasData.forEach(function(d) {
    dateToIdDia[d.fecha] = d.id_dia;
  });

  var turnoToId = {};
  turnosData.forEach(function(t) {
    var k = String(t.tipo_turno).toLowerCase().trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    turnoToId[k] = t.id_turno;
  });

  // Mapa (id_dia + "_" + id_turno) -> id_plani
  // Nota: Si hay varios grupos para el mismo día/turno, tomamos el primero (A)
  var planiMap = {};
  var planiMapByGroup = {}; // Mapa más específico: id_dia + "_" + id_turno + "_" + grupo
  var idPlaniToTurno = {}; // Mapa inverso: id_plani -> id_turno
  
  planiData.forEach(function(p) {
    var key = p.id_dia + '_' + p.id_turno;
    if (!planiMap[key]) {
      planiMap[key] = p.id_plani;
    }
    
    // Key con grupo (normalizado)
    if (p.grupo) {
      var gKey = key + '_' + String(p.grupo).trim().toUpperCase();
      planiMapByGroup[gKey] = p.id_plani;
    }
    
    idPlaniToTurno[p.id_plani] = p.id_turno;
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

    // Resolver ID Plani (Si falta id_plani, intentamos buscar por fecha y turno)
    if (!record.id_plani && record.fecha_turno && record.tipo_turno) {
      var fDate = record.fecha_turno;
      if (fDate instanceof Date) {
        fDate = Utilities.formatDate(fDate, Session.getScriptTimeZone(), 'yyyy-MM-dd');
      }
      
      var id_dia = dateToIdDia[fDate];
      var tKey = String(record.tipo_turno).toLowerCase().trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      var id_turno = turnoToId[tKey];
      
      if (id_dia && id_turno) {
        var pKey = id_dia + '_' + id_turno;
        
        // Si el usuario especificó grupo, intentamos busqueda exacta
        if (record.grupo) {
          var gKey = pKey + '_' + String(record.grupo).trim().toUpperCase();
          if (planiMapByGroup[gKey]) {
             record.id_plani = planiMapByGroup[gKey];
             record.id_turno = id_turno;
          }
        }
        
        // Fallback: si no encontró por grupo o no especificó grupo
        if (!record.id_plani && planiMap[pKey]) {
          record.id_plani = planiMap[pKey];
          record.id_turno = id_turno; // Aseguramos tener también id_turno
        }
      }
    }
    
    // Asegurar id_turno si tenemos id_plani pero no id_turno
    if (record.id_plani && !record.id_turno) {
       record.id_turno = idPlaniToTurno[record.id_plani];
    }
    
    if (!id_agente) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Agente no identificado');
      errorCount++;
      return;
    }
    
    if (!record.id_plani) {
      sheet.getRange(rowNum, statusCol).setValue('❌ No existe planificación para esa Fecha/Turno');
      errorCount++;
      return;
    }
    
    // Construir payload
    var payload = {
      id_agente: parseInt(id_agente),
      id_plani: parseInt(record.id_plani),
      id_turno: record.id_turno ? parseInt(record.id_turno) : null, // Opcional, trigger BD lo llena
      fecha_convocatoria: Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd'),
      estado: record.estado || 'vigente',
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
        // Si no tiene ID, intentamos upsert por clave natural (id_plani, id_agente)
        // Esto evita duplicados (HTTP 409) si el usuario vuelve a sincronizar lo mismo
        res = upsertRecord('convocatoria', payload, ['id_plani', 'id_agente']);
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

/**
 * Función de diagnóstico para depurar la última fila de Convocatoria
 */
function debugConvocatoriaLastRow() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('CONVOCATORIA');
  
  if (!sheet) return;
  
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(function(h) { return String(h).toLowerCase().trim(); });
  var values = sheet.getRange(lastRow, 1, 1, lastCol).getValues()[0];
  
  var record = {};
  headers.forEach(function(h, idx) {
    if (h && values[idx] !== '') record[h] = values[idx];
  });
  
  // LOGICA DE RESOLUCION IDENTICA A SYNC
  var log = '🔍 DIAGNÓSTICO FILA ' + lastRow + '\n\n';
  log += 'Datos crudos:\n' + JSON.stringify(record) + '\n\n';
  
  // 1. Resolver Agente
  var agentesList = getCacheData('_CACHE_PERSONAL', false);
  var dniToId = {};
  agentesList.forEach(function(a) { dniToId[String(a.dni).trim()] = a.id_agente; });
  
  var id_agente = record.id_agente;
  if (!id_agente && record.dni) {
    var dniLimpio = String(record.dni).replace(/\D/g, '');
    id_agente = dniToId[dniLimpio];
  }
  
  log += '🆔 ID Agente resuelto: ' + id_agente + '\n';
  
  // 2. Resolver Plani
  var diasData = fetchAll('dias', 'id_dia,fecha');
  var turnosData = fetchAll('turnos', 'id_turno,tipo_turno');
  var planiData = fetchAll('planificacion', 'id_plani,id_dia,id_turno,grupo');

  var dateToIdDia = {};
  diasData.forEach(function(d) { dateToIdDia[d.fecha] = d.id_dia; });

  var turnoToId = {};
  turnosData.forEach(function(t) {
    var k = String(t.tipo_turno).toLowerCase().trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    turnoToId[k] = t.id_turno;
  });

  var planiMap = {};
  var planiMapByGroup = {};
  var idPlaniToTurno = {}; 
  planiData.forEach(function(p) {
    var key = p.id_dia + '_' + p.id_turno;
    if (!planiMap[key]) planiMap[key] = p.id_plani;
    
    if (p.grupo) {
      var gKey = key + '_' + String(p.grupo).trim().toUpperCase();
      planiMapByGroup[gKey] = p.id_plani;
    }
    
    idPlaniToTurno[p.id_plani] = p.id_turno;
  });
  
  var id_plani = record.id_plani;
  var id_turno = record.id_turno;
  
  if (!id_plani && record.fecha_turno && record.tipo_turno) {
    var fDate = record.fecha_turno;
    if (fDate instanceof Date) {
      fDate = Utilities.formatDate(fDate, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    }
    var id_dia = dateToIdDia[fDate];
    var tKey = String(record.tipo_turno).toLowerCase().trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    id_turno = turnoToId[tKey]; // Puede sobreescribir
    
    log += '📅 Fecha: ' + fDate + ' -> id_dia: ' + id_dia + '\n';
    log += '🕐 Turno: ' + tKey + ' -> id_turno: ' + id_turno + '\n';
    
    if (id_dia && id_turno) {
      var pKey = id_dia + '_' + id_turno;
      
      if (record.grupo) {
         var gKey = pKey + '_' + String(record.grupo).trim().toUpperCase();
         log += '🔎 Buscando Grupo: ' + record.grupo + ' -> Key: ' + gKey + '\n';
         if (planiMapByGroup[gKey]) {
            id_plani = planiMapByGroup[gKey];
            log += '✅ Encontrado por grupo!\n';
         }
      }
      
      if (!id_plani && planiMap[pKey]) {
        id_plani = planiMap[pKey];
        log += '⚠️ Usando default (primer grupo encontrado)\n';
      }
    }
  }
  
  log += '📋 ID Plani resuelto: ' + id_plani + '\n';
  
  if (!id_agente || !id_plani) {
    ui.alert('❌ Faltan IDs clave:\n' + log);
    return;
  }
  
  // Construir payload
  var payload = {
    id_agente: parseInt(id_agente),
    id_plani: parseInt(id_plani),
    id_turno: id_turno ? parseInt(id_turno) : (idPlaniToTurno[id_plani] || null),
    fecha_convocatoria: Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    estado: record.estado || 'vigente',
    turno_cancelado: record.turno_cancelado === 'Sí',
    motivo_cambio: record.motivo_cambio || null
  };
  
  log += '\n📦 Payload Final:\n' + JSON.stringify(payload) + '\n';
  
  // PROBAR ENVIO (Simulado Upsert logic)
  var config = getSupabaseConfig_();
  var uniqueKey = record.id_convocatoria ? 'id_convocatoria' : null;
  // Si no hay id_convocatoria, intentamos INSERT
  
  var url = config.url + '/rest/v1/convocatoria';
  if (uniqueKey) {
    url += '?id_convocatoria=eq.' + record.id_convocatoria;
  } else {
    // Simular UPSERT por clave natural
    url += '?on_conflict=id_plani,id_agente';
    options.headers['Prefer'] = 'resolution=merge-duplicates, return=representation';
  }
  
  var options = {
    method: 'POST',
    headers: buildHeaders_(config.key),
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  // Headers para upsert si fuera necesario, pero aquí probamos insert simple o update
  if (!uniqueKey) {
     // Si es insert pero queremos ver si falla por unique constraint
     // Vamos a simular lo que hace sync:
     // res = supabaseRequest_('convocatoria', '', 'POST', payload);
  }
  
  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();
  var body = response.getContentText();
  
  ui.alert('📊 RESULTADO:\nCódigo: ' + code + '\nRespuesta:\n' + body + '\n\nDiagnostico:\n' + log);
}
