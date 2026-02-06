/**
 * SALDOS SYNC - Gestión de horas mensuales por agente
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: SINCRONIZACIÓN SALDOS
// ============================================================================

/**
 * Sincroniza hoja SALDOS con Supabase
 */
function syncSaldos() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.alert(
    'Sincronizar Saldos',
    '¿Confirmas sincronizar SALDOS con Supabase?',
    ui.ButtonSet.YES_NO
  );
  
  if (result === ui.Button.YES) {
    try {
      const res = syncSaldosWithValidation();
      ui.alert('✅ Sincronización completa\\n' + res.success + ' registros OK\\n' + res.errors.length + ' errores');
    } catch (e) {
      ui.alert('❌ Error: ' + e.message);
    }
  }
}

/**
 * Sincronización de saldos con validación
 * @private
 */
function syncSaldosWithValidation() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('SALDOS');
  
  if (!sheet) {
    throw new Error('❌ Hoja SALDOS no encontrada');
  }
  
  // Cargar mapeo de agentes para resolver DNI/nombre → id_agente
  const agentesMap = fetchAll('datos_personales', 'id_agente,dni,nombre,apellido');
  
  // Lookup por DNI
  const dniToIdAgente = {};
  agentesMap.forEach(a => {
    dniToIdAgente[String(a.dni).trim()] = a.id_agente;
  });
  
  // Lookup por id_agente (si ya viene el ID)
  const idAgenteExists = {};
  agentesMap.forEach(a => {
    idAgenteExists[a.id_agente] = true;
  });
  
  // Procesar hoja
  const values = sheet.getDataRange().getValues();
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
  
  const results = {success: 0, errors: []};
  
  // Procesar cada fila
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
    
    // Resolver id_agente
    let id_agente = null;
    
    if (record.id_agente) {
      // Si ya viene el ID, validar que existe
      id_agente = parseInt(record.id_agente);
      if (!idAgenteExists[id_agente]) {
        sheet.getRange(rowNum, statusCol).setValue('❌ ID agente no existe');
        results.errors.push({row: rowNum, errors: ['ID agente inválido']});
        continue;
      }
    } else if (record.dni) {
      // Resolver por DNI
      id_agente = dniToIdAgente[String(record.dni).trim()];
      if (!id_agente) {
        sheet.getRange(rowNum, statusCol).setValue('❌ DNI no encontrado');
        results.errors.push({row: rowNum, errors: ['DNI no encontrado']});
        continue;
      }
    } else {
      sheet.getRange(rowNum, statusCol).setValue('❌ Falta id_agente o DNI');
      results.errors.push({row: rowNum, errors: ['Falta identificador de agente']});
      continue;
    }
    
    // Validar mes y año
    if (!record.mes || !record.anio) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Falta mes o año');
      results.errors.push({row: rowNum, errors: ['Mes o año faltante']});
      continue;
    }
    
    const mes = parseInt(record.mes);
    const anio = parseInt(record.anio);
    
    if (mes < 1 || mes > 12) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Mes inválido (1-12)');
      results.errors.push({row: rowNum, errors: ['Mes debe estar entre 1 y 12']});
      continue;
    }
    
    if (anio < 2020 || anio > 2030) {
      sheet.getRange(rowNum, statusCol).setValue('❌ Año inválido');
      results.errors.push({row: rowNum, errors: ['Año fuera de rango válido']});
      continue;
    }
    
    // Construir payload
    const payload = {
      id_agente: id_agente,
      mes: mes,
      anio: anio,
      horas_mes: record.horas_mes ? parseFloat(record.horas_mes) : 0
    };
    
    // UPSERT
    try {
      const res = upsertRecord('saldos', payload, ['id_agente', 'mes', 'anio']);
      
      if (res.success) {
        sheet.getRange(rowNum, statusCol).setValue('✅ OK ' + new Date().toLocaleDateString());
        results.success++;
      } else {
        sheet.getRange(rowNum, statusCol).setValue('❌ ' + res.error);
        results.errors.push({row: rowNum, errors: [res.error]});
      }
    } catch (e) {
      sheet.getRange(rowNum, statusCol).setValue('❌ ' + e.message);
      results.errors.push({row: rowNum, errors: [e.message]});
    }
  }
  
  Logger.log('✅ Sync saldos: ' + results.success + ' OK, ' + results.errors.length + ' errores');
  return results;
}

// ============================================================================
// MÓDULO: CÁLCULO AUTOMÁTICO DE SALDOS
// ============================================================================

/**
 * Calcula saldos mensuales desde convocatoria y actualiza tabla saldos
 */
function calcularSaldosMensuales() {
  const ui = SpreadsheetApp.getUi();
  
  // Pedir mes y año
  const mesResult = ui.prompt(
    'Calcular Saldos Mensuales',
    'Ingresa MES (1-12):',
    ui.ButtonSet.OK_CANCEL
  );
  
  if (mesResult.getSelectedButton() !== ui.Button.OK) return;
  
  const anioResult = ui.prompt(
    'Calcular Saldos Mensuales',
    'Ingresa AÑO (ej: 2026):',
    ui.ButtonSet.OK_CANCEL
  );
  
  if (anioResult.getSelectedButton() !== ui.Button.OK) return;
  
  const mes = parseInt(mesResult.getResponseText());
  const anio = parseInt(anioResult.getResponseText());
  
  if (isNaN(mes) || mes < 1 || mes > 12 || isNaN(anio)) {
    ui.alert('❌ Mes o año inválido');
    return;
  }
  
  ui.alert('⏳ Calculando saldos para ' + mes + '/' + anio + '...\\n\\nEsto puede tardar unos segundos.');
  
  try {
    const resultado = calcularSaldosParaMes_(mes, anio);
    const msg = '✅ Cálculo completado\\n\\n' +
      'Agentes procesados: ' + resultado.agentes + '\\n' +
      'Total horas: ' + resultado.totalHoras.toFixed(2) + ' hs\\n' +
      'Promedio por agente: ' + (resultado.totalHoras / resultado.agentes).toFixed(2) + ' hs';
    
    ui.alert(msg);
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

/**
 * Calcula saldos para un mes específico
 * @private
 */
function calcularSaldosParaMes_(mes, anio) {
  Logger.log('📊 Calculando saldos para ' + mes + '/' + anio);
  
  // PASO 1: Obtener días del mes para filtrar por fecha REAL del turno
  const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
  const fechaFin = mes === 12 
    ? (anio + 1) + '-01-01' 
    : anio + '-' + String(mes + 1).padStart(2, '0') + '-01';
  
  Logger.log('   📅 Rango: ' + fechaInicio + ' a ' + fechaFin);
  
  // Obtener días del mes
  const diasDelMes = fetchAllWithFilters('dias', 'id_dia,fecha', {
    fecha_gte: fechaInicio,
    fecha_lt: fechaFin
  });
  
  const diasIds = new Set(diasDelMes.map(d => d.id_dia));
  Logger.log('   📅 ' + diasIds.size + ' días en el mes');
  
  // PASO 2: Obtener planificación del mes (via id_dia)
  const planificacion = fetchAll('planificacion', 'id_plani,id_dia,id_turno,cant_horas');
  const planiDelMes = planificacion.filter(p => diasIds.has(p.id_dia));
  
  // Crear mapa id_plani -> horas
  const planiHoras = {};
  planiDelMes.forEach(p => {
    planiHoras[p.id_plani] = p.cant_horas || 0;
  });
  
  Logger.log('   📊 ' + planiDelMes.length + ' turnos planificados en el mes');
  
  // PASO 3: Obtener convocatorias CUMPLIDAS y NO CANCELADAS
  const convocatorias = fetchAll('convocatoria', 'id_plani,id_agente,estado,turno_cancelado');
  
  // Filtrar: solo las del mes (via id_plani), cumplidas, y no canceladas
  const convValidas = convocatorias.filter(c => {
    return planiHoras.hasOwnProperty(c.id_plani) && 
           c.estado === 'cumplida' && 
           c.turno_cancelado !== true;
  });
  
  Logger.log('   ✅ ' + convValidas.length + ' convocatorias válidas (cumplidas, no canceladas)');
  
  // PASO 4: Acumular horas por agente
  const horasPorAgente = {};
  
  convValidas.forEach(conv => {
    const id_agente = conv.id_agente;
    const horas = planiHoras[conv.id_plani] || 0;
    
    if (!horasPorAgente[id_agente]) {
      horasPorAgente[id_agente] = 0;
    }
    horasPorAgente[id_agente] += horas;
  });
  
  // PASO 5: Escribir a Supabase
  let totalHoras = 0;
  let agentesCount = 0;
  
  for (const id_agente in horasPorAgente) {
    const horas = horasPorAgente[id_agente];
    
    const payload = {
      id_agente: parseInt(id_agente),
      mes: mes,
      anio: anio,
      horas_mes: horas
    };
    
    upsertRecord('saldos', payload, ['id_agente', 'mes', 'anio']);
    
    totalHoras += horas;
    agentesCount++;
  }
  
  Logger.log('✅ Saldos escritos: ' + agentesCount + ' agentes, ' + totalHoras.toFixed(2) + ' hs totales');
  
  return {
    agentes: agentesCount,
    totalHoras: totalHoras
  };
}

/**
 * Descarga saldos filtrados (por CONFIG) a hoja SALDOS
 */
function loadSaldos() {
  const filters = getActiveFilters();
  const customFilters = {};
  
  if (filters.año_activo) {
    customFilters.anio = filters.año_activo;
  }
  
  const data = fetchAllWithFilters('saldos', 'id_agente,mes,anio,horas_mes', customFilters);
  
  if (data.length === 0) {
    SpreadsheetApp.getUi().alert('No hay datos de saldos para los filtros configurados');
    return;
  }
  
  const sheet = getOrCreateSheet_('SALDOS');
  const headers = ['id_agente', 'mes', 'anio', 'horas_mes'];
  const rows = data.map(r => headers.map(h => r[h]));
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  
  Logger.log('✅ SALDOS actualizada: ' + rows.length + ' registros');
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' registros descargados');
}
