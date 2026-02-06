/**
 * DOWNLOAD OPTIMIZED - Funciones de descarga optimizadas usando vistas y caché
 * Reemplaza download_data.gs con versión que usa arquitectura híbrida
 * 
 * @author Pablo (Data Analyst)
 * @version 2.0.0
 */

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
function loadDashboardKPIs() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  try {
    // Usa vista que ya tiene los cálculos hechos
    let kpis;
    if (filters.año_activo) {
      kpis = fetchAllWithFilters('vista_dashboard_kpis', '*', {
        anio: filters.año_activo
      });
    } else {
      kpis = fetchAll('vista_dashboard_kpis', '*');
    }
    
    if (kpis.length === 0) {
      ui.alert('ℹ️ No hay datos de KPIs');
      return;
    }
    
    const sheet = getOrCreateSheet_('DASHBOARD_KPIS');
    sheet.clear();
    
    // Headers
    const headers = ['Año', 'Mes', 'Turnos Plan.', 'Requeridos', 'Cubiertos', 
                     'Hs. Plan.', 'Hs. Cumplidas', '% Cobertura'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    
    // Data
    const rows = kpis.map(k => [
      k.anio,
      k.mes,
      k.turnos_planificados,
      k.residentes_requeridos,
      k.turnos_cubiertos,
      k.horas_planificadas,
      k.horas_cumplidas,
      (k.porcentaje_cobertura || 0) + '%'
    ]);
    
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    
    // Formato condicional para cobertura
    const coberturaCol = 8;
    const coberturaRange = sheet.getRange(2, coberturaCol, rows.length, 1);
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ Dashboard actualizado con ' + rows.length + ' meses de datos');
    
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
