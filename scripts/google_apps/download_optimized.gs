/**
 * DOWNLOAD OPTIMIZED - Funciones de descarga optimizadas usando vistas y caché
 * Reemplaza download_data.gs con versión que usa arquitectura híbrida
 * 
 * @author Pablo (Data Analyst)
 * @version 2.0.0
 */

/**
 * TEST DIRECTO - Diagnóstico de conexión a vista_dashboard_kpis
 * Ejecutar desde el editor de Apps Script para ver logs detallados
 */
function testVistaDashboardKPIs() {
  const config = getSupabaseConfig_();
  const url = config.url + '/rest/v1/vista_dashboard_kpis?select=*&limit=5';
  
  Logger.log('🔧 URL: ' + url);
  Logger.log('🔧 API Key presente: ' + (config.key ? 'SÍ (' + config.key.substring(0,20) + '...)' : 'NO'));
  
  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: buildHeaders_(config.key),
      muteHttpExceptions: true
    });
    
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    Logger.log('📡 HTTP Code: ' + code);
    Logger.log('📡 Response: ' + body.substring(0, 500));
    
    if (code === 200) {
      const data = JSON.parse(body);
      SpreadsheetApp.getUi().alert('✅ Vista accesible!\n\nRegistros: ' + data.length + '\n\nPrimer registro:\n' + JSON.stringify(data[0], null, 2));
    } else {
      SpreadsheetApp.getUi().alert('❌ Error HTTP ' + code + '\n\n' + body);
    }
  } catch (e) {
    Logger.log('❌ Exception: ' + e.message);
    SpreadsheetApp.getUi().alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// CONVOCATORIA OPTIMIZADA (Usa vista filtrada)
// ============================================================================

/**
 * Descarga convocatoria del MES ACTUAL usando vista optimizada
 * Reduce 3600 → ~300 registros
 */
function downloadConvocatoriaMesActual() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    // Usa vista que solo trae mes actual (pre-filtrada en Supabase)
    const data = fetchAll('vista_convocatoria_mes_activo', '*');
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay convocatorias para el mes actual');
      return;
    }
    
    const sheet = getOrCreateSheet_('CONVOCATORIA');
    
    const headers = [
      'id_convocatoria', 'agente', 'dni', 'fecha_turno', 'tipo_turno',
      'estado', 'turno_cancelado', 'motivo_cambio', 'cant_horas',
      'id_plani', 'id_agente', 'id_turno', 'sync_status'
    ];
    
    const rows = data.map(c => [
      c.id_convocatoria,
      c.agente,
      c.dni,
      c.fecha_turno,
      c.tipo_turno,
      c.estado,
      c.turno_cancelado ? 'Sí' : 'No',
      c.motivo_cambio || '',
      c.cant_horas,
      c.id_plani,
      c.id_agente,
      c.id_turno,
      '✅'
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
    
    // Formato
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ ' + rows.length + ' convocatorias del mes actual descargadas');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

/**
 * Descarga convocatoria de un MES ESPECÍFICO
 */
function downloadConvocatoriaMes() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  // Pedir mes si no está en CONFIG
  let mes = filters.mes_activo;
  let anio = filters.año_activo;
  
  if (!mes) {
    const mesResult = ui.prompt('Descargar Convocatoria', 'Mes (1-12):', ui.ButtonSet.OK_CANCEL);
    if (mesResult.getSelectedButton() !== ui.Button.OK) return;
    mes = parseInt(mesResult.getResponseText());
  }
  
  if (!anio) {
    const anioResult = ui.prompt('Descargar Convocatoria', 'Año:', ui.ButtonSet.OK_CANCEL);
    if (anioResult.getSelectedButton() !== ui.Button.OK) return;
    anio = parseInt(anioResult.getResponseText());
  }
  
  try {
    // Usa vista completa con filtros
    const data = fetchAllWithFilters('vista_convocatoria_completa', '*', {
      anio: anio,
      mes: mes
    });
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay datos para ' + mes + '/' + anio);
      return;
    }
    
    const sheet = getOrCreateSheet_('CONVOCATORIA');
    
    const headers = [
      'sincronizar', 'id_convocatoria', 'agente', 'dni', 'fecha_turno', 'tipo_turno',
      'estado', 'turno_cancelado', 'motivo_cambio', 'cant_horas',
      'id_plani', 'id_agente', 'id_turno', 'sync_status'
    ];
    
    const rows = data.map(c => [
      false, // Checkbox inicial
      c.id_convocatoria,
      c.agente,
      c.dni,
      c.fecha_turno,
      c.tipo_turno,
      c.estado,
      c.turno_cancelado ? 'Sí' : 'No',
      c.motivo_cambio || '',
      c.cant_horas,
      c.id_plani,
      c.id_agente,
      c.id_turno,
      '✅'
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Validation Checkbox
      const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
      const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
      checkboxRange.setDataValidation(rule);
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ ' + rows.length + ' convocatorias de ' + mes + '/' + anio);
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// DASHBOARD OPTIMIZADO (Usa vista pre-calculada)
// ============================================================================

/**
 * Carga KPIs desde vista pre-calculada (instantáneo)
 */
/**
 * Carga SEGUIMIENTO RESIDENTES (Dashboard Detallado)
 * Maneja columnas de turnos dinámicas (JSON)
 */
function loadSeguimientoResidentes() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  try {
    const kpis = fetchAllWithFilters('vista_seguimiento_residentes', '*', {});
    
    if (kpis.length === 0) {
      ui.alert('ℹ️ No hay datos de seguimiento.\nVerifica Supabase.');
      return;
    }
    
    // Filtrado opcional por mes
    let displayData = kpis;
    const mesResult = ui.prompt('Filtrar Seguimiento', 'Ingresa MES (1-12) o deja vacío:', ui.ButtonSet.OK_CANCEL);
    if (mesResult.getSelectedButton() === ui.Button.OK) {
      if (mesResult.getResponseText().trim()) {
        displayData = kpis.filter(k => k.mes == parseInt(mesResult.getResponseText()));
      }
    }
    
    // 1. Identificar TODOS los tipos de turno dinámicos presentes en la data
    const allTurnTypes = new Set();
    displayData.forEach(row => {
      if (row.tipos_turno_json) {
        Object.keys(row.tipos_turno_json).forEach(t => allTurnTypes.add(t));
      }
    });
    const dynamicHeaders = Array.from(allTurnTypes).sort();
    
    const sheet = getOrCreateSheet_('SEGUIMIENTO_RESIDENTES');
    sheet.clear();
    
    // Headers with color groups
    const baseHeaders = ['Año', 'Mes', 'Agente', 'DNI'];
    const turnoHeaders = ['Turnos Tot.', 'Horas Tot.'];
    const inasisHeaders = ['Tardanzas', 'Total Inasis.', 'I. Salud', 'I. Estudio', 'I. Imprev.'];
    
    const headers = [...baseHeaders, ...turnoHeaders, ...dynamicHeaders, ...inasisHeaders];
    
    // Write headers
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    
    // Color banding for header groups
    // Base (Año, Mes, Agente, DNI) - Gray
    sheet.getRange(1, 1, 1, baseHeaders.length).setBackground('#424242').setFontColor('#ffffff');
    // Turnos Tot, Horas Tot - Blue
    sheet.getRange(1, baseHeaders.length + 1, 1, turnoHeaders.length).setBackground('#1565c0').setFontColor('#ffffff');
    // Dynamic turn types - Green tones
    if (dynamicHeaders.length > 0) {
      sheet.getRange(1, baseHeaders.length + turnoHeaders.length + 1, 1, dynamicHeaders.length).setBackground('#2e7d32').setFontColor('#ffffff');
    }
    // Inasistencias - Orange/Red
    const inasisStart = baseHeaders.length + turnoHeaders.length + dynamicHeaders.length + 1;
    sheet.getRange(1, inasisStart, 1, 1).setBackground('#e65100').setFontColor('#ffffff'); // Tardanzas - Orange
    sheet.getRange(1, inasisStart + 1, 1, 1).setBackground('#c62828').setFontColor('#ffffff'); // Total Inasis - Red
    sheet.getRange(1, inasisStart + 2, 1, inasisHeaders.length - 2).setBackground('#ef5350').setFontColor('#ffffff'); // Types - Light Red
    
    // Data Mapping
    const rows = displayData.map(k => {
      const turnCounts = k.tipos_turno_json || {};
      const dynamicValues = dynamicHeaders.map(h => turnCounts[h] || 0);
      
      return [
        k.anio,
        k.mes,
        k.agente,
        k.dni,
        k.turnos_totales || 0,
        parseFloat(k.horas_totales || 0).toFixed(1),
        ...dynamicValues,
        k.tardanzas || 0,
        k.total_inasistencias || 0,
        k.inasistencias_salud || 0,
        k.inasistencias_estudio || 0,
        k.inasistencias_imprevisto || 0
      ];
    });
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // === Tardanzas Color Logic ===
      // Columna Tardanzas = baseHeaders + turnoHeaders + dynamicHeaders + 1
      const tardanzasCol = baseHeaders.length + turnoHeaders.length + dynamicHeaders.length + 1;
      
      // Yellow: 1-2 before limit (4-5, 10-11, 16-17...)
      const ruleYellow = SpreadsheetApp.newConditionalFormatRule()
        .whenFormulaSatisfied('=OR(MOD($' + String.fromCharCode(64 + tardanzasCol) + '2, 6)=4, MOD($' + String.fromCharCode(64 + tardanzasCol) + '2, 6)=5)')
        .setBackground('#fef08a').setFontColor('#854d0e')
        .setRanges([sheet.getRange(2, tardanzasCol, rows.length, 1)])
        .build();
      
      // Red: At limit (6, 12, 18...)
      const ruleRed = SpreadsheetApp.newConditionalFormatRule()
        .whenFormulaSatisfied('=AND(MOD($' + String.fromCharCode(64 + tardanzasCol) + '2, 6)=0, $' + String.fromCharCode(64 + tardanzasCol) + '2>0)')
        .setBackground('#fca5a5').setFontColor('#7f1d1d')
        .setRanges([sheet.getRange(2, tardanzasCol, rows.length, 1)])
        .build();
      
      sheet.setConditionalFormatRules([ruleYellow, ruleRed]);
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    ui.alert('✅ Seguimiento actualizado. Tipos de turno: ' + dynamicHeaders.join(', '));
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// SALDOS OPTIMIZADO (Smart Logic + Acumulados)
// ============================================================================

/**
 * Descarga Saldos Detallados con Lógica de Fechas (Alta/Baja) y Acumulados
 */
function downloadSaldosResumen() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const data = fetchAllWithFilters('vista_saldos_resumen', '*', {});
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay datos de saldos');
      return;
    }
    
    const sheet = getOrCreateSheet_('SALDOS_RESUMEN');
    
    const headers = [
      'Agente', 'Año', 'Mes', 
      'Hs. Obj. Mes', 'Hs. Cump. Mes', 'Saldo Mes',
      'Hs. Obj. ACUM', 'Hs. Cump. ACUM', 'SALDO ACUM',
      'Inasis.', 'Turnos Canc.'
    ];
    
    const rows = data.map(s => [
      s.agente,
      s.anio,
      s.mes,
      parseFloat(s.horas_objetivo_mes || 0).toFixed(1),
      parseFloat(s.horas_cumplidas || 0).toFixed(1),
      parseFloat(s.saldo_mensual || 0).toFixed(1),
      parseFloat(s.horas_objetivo_acumuladas || 0).toFixed(1),
      parseFloat(s.horas_cumplidas_acumuladas || 0).toFixed(1),
      parseFloat(s.saldo_acumulado || 0).toFixed(1),
      s.inasistencias_mes || 0,
      s.turnos_cancelados || 0
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
      .setFontWeight('bold').setBackground('#5e35b1').setFontColor('#ffffff');
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // === Color Logic INVERTIDA ===
      // VERDE = Saldo negativo (residente debe horas = bueno para el espacio)
      // ROJO = Saldo positivo (residente excedió horas = atención)
      
      // Saldo Acumulado (Col I = 9)
      const saldoAcumCol = 9;
      // Verde para negativo (debe horas)
      const ruleGreenAcum = SpreadsheetApp.newConditionalFormatRule()
        .whenNumberLessThan(0)
        .setBackground('#bbf7d0').setFontColor('#166534')
        .setRanges([sheet.getRange(2, saldoAcumCol, rows.length, 1)])
        .build();
      // Rojo para positivo alto (excedió horas)
      const ruleRedAcum = SpreadsheetApp.newConditionalFormatRule()
        .whenNumberGreaterThan(0)
        .setBackground('#fca5a5').setFontColor('#7f1d1d')
        .setRanges([sheet.getRange(2, saldoAcumCol, rows.length, 1)])
        .build();
        
      // Saldo Mensual (Col F = 6)
      const saldoMesCol = 6;
      const ruleGreenMes = SpreadsheetApp.newConditionalFormatRule()
        .whenNumberLessThan(0)
        .setBackground('#dcfce7').setFontColor('#15803d')
        .setRanges([sheet.getRange(2, saldoMesCol, rows.length, 1)])
        .build();
      const ruleRedMes = SpreadsheetApp.newConditionalFormatRule()
        .whenNumberGreaterThan(0)
        .setBackground('#fee2e2').setFontColor('#dc2626')
        .setRanges([sheet.getRange(2, saldoMesCol, rows.length, 1)])
        .build();

      sheet.setConditionalFormatRules([ruleGreenAcum, ruleRedAcum, ruleGreenMes, ruleRedMes]);
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ Saldos descargados. Se detectaron ' + rows.length + ' registros (incluye lógicas de alta/baja).');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// SALDOS OPTIMIZADO (Usa vista pre-calculada)
// ============================================================================

/**
 * Carga saldos desde vista (elimina cálculo en GAS)
 */
function loadSaldosDesdeVista() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  try {
    let saldos;
    if (filters.año_activo) {
      saldos = fetchAllWithFilters('vista_saldo_horas_resumen', '*', {
        anio: filters.año_activo
      });
    } else {
      saldos = fetchAll('vista_saldo_horas_resumen', '*');
    }
    
    if (saldos.length === 0) {
      ui.alert('ℹ️ No hay saldos para mostrar');
      return;
    }
    
    const sheet = getOrCreateSheet_('SALDOS_VISTA');
    sheet.clear();
    
    const headers = ['Agente', 'Cohorte', 'Año', 'Mes', 'Turnos', 'Horas'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    
    const rows = saldos.map(s => [
      s.agente,
      s.cohorte,
      s.anio,
      s.mes,
      s.turnos_cumplidos,
      s.horas_mes
    ]);
    
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ ' + rows.length + ' registros de saldos cargados');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// PLANIFICACIÓN CON CACHÉ
// ============================================================================

/**
 * Descarga planificación del año usando caché
 */
function downloadPlanificacionConCache() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    // Refresca caché si es necesario y lee de ella
    const data = getCacheData('_CACHE_PLANI_ANIO', false);
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay planificación. Verifica año_activo en CONFIG.');
      return;
    }
    
    const sheet = getOrCreateSheet_('PLANIFICACION');
    sheet.clear();
    
    const headers = [
      'id_plani', 'fecha', 'mes', 'tipo_turno', 'cant_residentes_plan',
      'cant_visit', 'hora_inicio', 'hora_fin', 'cant_horas', 'es_feriado', 'sync_status'
    ];
    
    const rows = data.map(p => [
      p.id_plani,
      p.fecha,
      p.mes,
      p.tipo_turno,
      p.cant_residentes_plan,
      p.cant_visit,
      p.hora_inicio,
      p.hora_fin,
      p.cant_horas,
      p.es_feriado ? 'Sí' : 'No',
      '✅'
    ]);
    
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ ' + rows.length + ' turnos planificados (desde caché)');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

// ============================================================================
// UTILIDADES
// ============================================================================

/**
 * Obtiene o crea hoja
 * @private
 */
function getOrCreateSheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

// ============================================================================
// HARD REFRESH (Control de Caché para Analistas)
// ============================================================================

/**
 * Fuerza recarga completa de todas las cachés
 * Uso: Cuando el analista sospecha discrepancias entre Sheets y Supabase
 */
function forzarRecargaCompleta() {
  const ui = SpreadsheetApp.getUi();
  
  const confirm = ui.alert(
    '🔄 Forzar Recarga Completa',
    'Esta acción:\\n\\n' +
    '• Eliminará TODO el caché local\\n' +
    '• Descargará datos frescos de Supabase\\n' +
    '• Puede tardar 30-60 segundos\\n\\n' +
    '¿Continuar?',
    ui.ButtonSet.YES_NO
  );
  
  if (confirm !== ui.Button.YES) return;
  
  try {
    Logger.log('🔄 Iniciando Hard Refresh...');
    
    // Limpiar metadata de cachés (forzar expiración)
    const props = PropertiesService.getScriptProperties();
    const cacheNames = ['_CACHE_DIAS', '_CACHE_TURNOS', '_CACHE_PERSONAL', '_CACHE_PLANI_ANIO'];
    
    cacheNames.forEach(cacheName => {
      props.deleteProperty('CACHE_META_' + cacheName);
      Logger.log('  ❌ Invalidada: ' + cacheName);
    });
    
    // Refrescar todas las cachés
    let totalRecords = 0;
    cacheNames.forEach(cacheName => {
      try {
        const count = refreshCache(cacheName);
        totalRecords += count;
        Logger.log('  ✅ Recargada: ' + cacheName + ' (' + count + ' registros)');
      } catch (e) {
        Logger.log('  ⚠️ Error en ' + cacheName + ': ' + e.message);
      }
    });
    
    ui.alert(
      '✅ Recarga Completa Exitosa',
      'Se han recargado ' + totalRecords + ' registros desde Supabase.\\n\\n' +
      'Las cachés están ahora sincronizadas con la base de datos.',
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert('❌ Error durante Hard Refresh: ' + e.message);
  }
}
