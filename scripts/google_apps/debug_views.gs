/**
 * DIAGNÓSTICO - Funciones para debug de vistas y conexión
 * Agregar temporalmente al proyecto GAS para diagnosticar
 */

/**
 * Diagnóstico completo de vistas
 * Ejecutar desde menú o directamente
 */
function diagnosticarVistas() {
  const ui = SpreadsheetApp.getUi();
  let report = '=== DIAGNÓSTICO DE VISTAS ===\n\n';
  
  const vistas = [
    'vista_convocatoria_mes_activo',
    'vista_convocatoria_completa', 
    'vista_dashboard_kpis',
    'vista_saldo_horas_resumen',
    'vista_planificacion_anio'
  ];
  
  vistas.forEach(vista => {
    try {
      const data = fetchAll(vista, '*');
      report += '✅ ' + vista + ': ' + data.length + ' registros\n';
      
      // Si tiene datos, mostrar muestra
      if (data.length > 0) {
        report += '   Columnas: ' + Object.keys(data[0]).join(', ') + '\n';
      }
    } catch (e) {
      report += '❌ ' + vista + ': ERROR - ' + e.message + '\n';
    }
  });
  
  report += '\n=== FILTROS ACTIVOS ===\n';
  try {
    const filters = getActiveFilters();
    report += 'año_activo: ' + (filters.año_activo || 'NO CONFIGURADO') + '\n';
    report += 'mes_activo: ' + (filters.mes_activo || 'NO CONFIGURADO') + '\n';
    report += 'cohorte_activa: ' + (filters.cohorte_activa || 'NO CONFIGURADO') + '\n';
  } catch (e) {
    report += 'Error obteniendo filtros: ' + e.message + '\n';
  }
  
  report += '\n=== TEST ESPECÍFICO: Convocatoria Octubre 2025 ===\n';
  try {
    const conv = fetchAllWithFilters('vista_convocatoria_completa', '*', {
      anio: 2025,
      mes: 10
    });
    report += 'Registros encontrados: ' + conv.length + '\n';
    if (conv.length > 0) {
      report += 'Primer registro:\n' + JSON.stringify(conv[0], null, 2) + '\n';
    }
  } catch (e) {
    report += 'Error: ' + e.message + '\n';
  }
  
  // Mostrar en log y alert
  Logger.log(report);
  
  // Escribir a una hoja para mejor visualización
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('_DEBUG');
  if (!sheet) {
    sheet = ss.insertSheet('_DEBUG');
  }
  sheet.clear();
  sheet.getRange(1, 1).setValue(report);
  
  ui.alert('Diagnóstico completado. Ver hoja _DEBUG para detalles.');
}

/**
 * Test directo de la URL que se genera
 */
function testURLGenerada() {
  const ui = SpreadsheetApp.getUi();
  const config = getSupabaseConfig_();
  
  const testUrl = config.url + '/rest/v1/vista_convocatoria_completa?select=*&anio=eq.2025&mes=eq.10';
  
  Logger.log('URL de prueba: ' + testUrl);
  
  try {
    const options = {
      method: 'GET',
      headers: buildHeaders_(config.key),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(testUrl, options);
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    let report = 'URL: ' + testUrl + '\n\n';
    report += 'Código HTTP: ' + code + '\n\n';
    
    if (code === 200) {
      const data = JSON.parse(body);
      report += 'Registros: ' + data.length + '\n';
      if (data.length > 0) {
        report += 'Primer registro:\n' + JSON.stringify(data[0], null, 2);
      }
    } else {
      report += 'Respuesta: ' + body;
    }
    
    Logger.log(report);
    ui.alert(report.substring(0, 1000)); // Alert tiene límite
    
  } catch (e) {
    ui.alert('Error: ' + e.message);
  }
}
