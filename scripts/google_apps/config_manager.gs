/**
 * CONFIG MODULE - Gestión de configuración global
 * Permite filtrado por año/cohorte para optimizar descargas
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// MÓDULO: LECTURA DE CONFIGURACIÓN
// ============================================================================

/**
 * Obtiene o crea la hoja CONFIG
 * @private
 * @returns {Sheet}
 */
function getConfigSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('CONFIG');
  
  if (!sheet) {
    sheet = ss.insertSheet('CONFIG');
    initializeConfigSheet_(sheet);
  }
  
  return sheet;
}

/**
 * Inicializa la hoja CONFIG con estructura
 * @private
 */
function initializeConfigSheet_(sheet) {
  const data = [
    ['CONFIGURACIÓN GLOBAL', ''],
    ['', ''],
    ['Parámetro', 'Valor'],
    ['año_activo', new Date().getFullYear()],
    ['cohorte_activa', new Date().getFullYear()],
    ['', ''],
    ['INSTRUCCIONES:', ''],
    ['• año_activo: Filtra datos por año (planificación, convocatoria)', ''],
    ['• cohorte_activa: Filtra agentes por cohorte (datos_personales)', ''],
    ['• Dejar vacío para descargar TODO el histórico', '']
  ];
  
  sheet.getRange(1, 1, data.length, 2).setValues(data);
  
  // Formato
  sheet.getRange('A1:B1').setFontWeight('bold').setFontSize(12);
  sheet.getRange('A3:B3').setFontWeight('bold').setBackground('#e8f0fe');
  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 150);
  
  Logger.log('✅ Hoja CONFIG inicializada');
}

/**
 * Lee un valor de configuración de la hoja CONFIG
 * @param {string} param - Nombre del parámetro
 * @returns {any} Valor del parámetro o null
 */
function getConfigValue(param) {
  const sheet = getConfigSheet_();
  const data = sheet.getDataRange().getValues();
  
  for (let i = 0; i < data.length; i++) {
    if (data[i][0] === param) {
      const value = data[i][1];
      return value === '' ? null : value;
    }
  }
  
  return null;
}

/**
 * Obtiene todos los parámetros de configuración activos
 * @returns {Object} {año_activo, cohorte_activa}
 */
function getActiveFilters() {
  return {
    año_activo: getConfigValue('año_activo'),
    cohorte_activa: getConfigValue('cohorte_activa')
  };
}

/**
 * Establece un valor de configuración
 * @param {string} param - Nombre del parámetro
 * @param {any} value - Valor a establecer
 */
function setConfigValue(param, value) {
  const sheet = getConfigSheet_();
  const data = sheet.getDataRange().getValues();
  
  for (let i = 0; i < data.length; i++) {
    if (data[i][0] === param) {
      sheet.getRange(i + 1, 2).setValue(value);
      Logger.log('✅ ' + param + ' = ' + value);
      
      // Invalida cachés si cambia la configuración
      const props = PropertiesService.getScriptProperties();
      
      if (param === 'año_activo') {
        // Al cambiar el año, la planificación del año anterior ya no sirve
        props.deleteProperty('CACHE_META__CACHE_PLANI_ANIO');
        // También invalidamos la convocatoria (aunque esta no usa caché persistente igual, mejor prevenir)
        Logger.log('🔄 Caché _CACHE_PLANI_ANIO invalidada por cambio de año');
      }
      
      if (param === 'cohorte_activa') {
        // Al cambiar cohorte, la lista de personal filtrada puede cambiar
        props.deleteProperty('CACHE_META__CACHE_PERSONAL');
        Logger.log('🔄 Caché _CACHE_PERSONAL invalidada por cambio de cohorte');
      }
      
      return;
    }
  }
  
  Logger.log('⚠️ Parámetro no encontrado: ' + param);
}

// ============================================================================
// MENÚ DE CONFIGURACIÓN
// ============================================================================

/**
 * Muestra diálogo para configurar filtros
 */
function configurarFiltros() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  const result = ui.prompt(
    'Configurar Filtros',
    'Año activo (dejar vacío para TODO):',
    ui.ButtonSet.OK_CANCEL
  );
  
  if (result.getSelectedButton() === ui.Button.OK) {
    const año = result.getResponseText().trim();
    setConfigValue('año_activo', año === '' ? '' : parseInt(año));
  }
  
  const result2 = ui.prompt(
    'Configurar Filtros',
    'Cohorte activa (dejar vacío para TODO):',
    ui.ButtonSet.OK_CANCEL
  );
  
  if (result2.getSelectedButton() === ui.Button.OK) {
    const cohorte = result2.getResponseText().trim();
    setConfigValue('cohorte_activa', cohorte === '' ? '' : parseInt(cohorte));
  }
  
  ui.alert('✅ Configuración actualizada');
}

/**
 * Muestra filtros activos
 */
function mostrarFiltrosActivos() {
  const filters = getActiveFilters();
  const ui = SpreadsheetApp.getUi();
  
  let msg = 'FILTROS ACTIVOS:\n\n';
  msg += 'Año: ' + (filters.año_activo || 'TODO el histórico') + '\n';
  msg += 'Cohorte: ' + (filters.cohorte_activa || 'TODAS');
  
  ui.alert(msg);
}
