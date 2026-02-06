/**
 * DOWNLOAD INASISTENCIAS - Descarga de inasistencias y gestión
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: DESCARGA DE INASISTENCIAS
// ============================================================================

/**
 * Descarga inasistencias de un MES o AÑO específico
 */
function downloadInasistenciasMes() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  // Pedir mes si no está en CONFIG
  let mes = filters.mes_activo;
  let anio = filters.año_activo;
  
  if (!anio) {
    const anioResult = ui.prompt('Descargar Inasistencias', 'Año (YYYY) o * para todos:', ui.ButtonSet.OK_CANCEL);
    if (anioResult.getSelectedButton() !== ui.Button.OK) return;
    const resp = anioResult.getResponseText().trim();
    if (resp !== '*') anio = parseInt(resp);
  }
  
  // Construir filtros para la vista
  const queryFilters = {};
  if (anio) queryFilters.anio = anio;
  if (mes) queryFilters.mes = mes;
  
  try {
    const data = fetchAllWithFilters('vista_inasistencias_completa', '*', queryFilters);
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay inasistencias registradas para ' + (mes ? mes + '/' : '') + (anio || 'todos los años'));
      // No retornamos, permitimos crear la hoja vacía para carga manual
    }
    
    const sheet = getOrCreateSheet_('INASISTENCIAS');
    
    const headers = [
      'sincronizar', // Checkbox
      'id_inasistencia', 'agente', 'dni', 'fecha_inasistencia', 
      'motivo', 'estado', 'requiere_certificado', 'observaciones',
      'id_agente', 'sync_status'
    ];
    
    // Mapear datos
    const rows = data.map(r => [
      false, // Checkbox default
      r.id_inasistencia,
      r.agente,
      r.dni,
      r.fecha_inasistencia,
      r.motivo || 'imprevisto',
      r.estado || 'pendiente',
      r.requiere_certificado ? 'Sí' : 'No',
      r.observaciones || '',
      r.id_agente,
      '✅'
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
      .setFontWeight('bold')
      .setBackground('#ea4335') // Rojo Inasistencias
      .setFontColor('#ffffff');
      
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Checkbox validation
      const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
      const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
      checkboxRange.setDataValidation(rule);
      
      // Dropdown Motivos (Columna F -> índice 6)
      const motivos = ['medico', 'estudio', 'imprevisto', 'injustificada', 'otro_justificada'];
      const motivosRange = sheet.getRange(2, 6, rows.length, 1);
      const motivosRule = SpreadsheetApp.newDataValidation().requireValueInList(motivos).build();
      motivosRange.setDataValidation(motivosRule);
      
      // Dropdown Estado (Columna G -> índice 7)
      const estados = ['pendiente', 'justificada', 'injustificada'];
      const estadosRange = sheet.getRange(2, 7, rows.length, 1);
      const estadosRule = SpreadsheetApp.newDataValidation().requireValueInList(estados).build();
      estadosRange.setDataValidation(estadosRule);
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    const countMsg = rows.length > 0 ? rows.length : '0';
    ui.alert('✅ ' + countMsg + ' inasistencias descargadas.');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

/**
 * Descarga COMPLETA de Inasistencias (todos los meses/años o filtro opcional)
 * Incluye checkbox para edición masiva/selectiva
 */
function downloadInasistenciasCompleta() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  let anio = filters.año_activo;
  
  if (!anio) {
    const result = ui.prompt('Descarga Completa Inasistencias', 'Filtrar por Año (YYYY) o dejar vacío para TODO:', ui.ButtonSet.OK_CANCEL);
    if (result.getSelectedButton() !== ui.Button.OK) return;
    const input = result.getResponseText().trim();
    if (input) anio = parseInt(input);
  }
  
  try {
    const queryFilters = {};
    if (anio) queryFilters.anio = anio;
    
    const data = fetchAllWithFilters('vista_inasistencias_completa', '*', queryFilters);
    
    if (data.length === 0) {
       ui.alert('ℹ️ No hay registros encontrados.');
       return;
    }
    
    const sheet = getOrCreateSheet_('INASISTENCIAS');
    
    // Mismos headers que la descarga mensual
    const headers = [
      'sincronizar', 
      'id_inasistencia', 'agente', 'dni', 'fecha_inasistencia', 
      'motivo', 'estado', 'requiere_certificado', 'observaciones',
      'id_agente', 'sync_status'
    ];
    
     const rows = data.map(r => [
      false, // Checkbox inicial
      r.id_inasistencia,
      r.agente,
      r.dni,
      r.fecha_inasistencia,
      r.motivo || 'imprevisto',
      r.estado || 'pendiente',
      r.requiere_certificado ? 'Sí' : 'No',
      r.observaciones || '',
      r.id_agente,
      '✅'
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
      .setFontWeight('bold')
      .setBackground('#ea4335')
      .setFontColor('#ffffff');
      
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Checkbox validation
      const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
      const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
      checkboxRange.setDataValidation(rule);
      
      // Dropdown Motivos
      const motivos = ['medico', 'estudio', 'imprevisto', 'injustificada', 'otro_justificada'];
      const motivosRange = sheet.getRange(2, 6, rows.length, 1);
      const motivosRule = SpreadsheetApp.newDataValidation().requireValueInList(motivos).build();
      motivosRange.setDataValidation(motivosRule);
      
      // Dropdown Estado
      const estados = ['pendiente', 'justificada', 'injustificada'];
      const estadosRange = sheet.getRange(2, 7, rows.length, 1);
      const estadosRule = SpreadsheetApp.newDataValidation().requireValueInList(estados).build();
      estadosRange.setDataValidation(estadosRule);
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ Desarga Completa: ' + rows.length + ' inasistencias cargadas.');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}
