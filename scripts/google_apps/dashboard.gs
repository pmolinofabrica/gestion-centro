/**
 * DASHBOARD OPTIMIZADO - Visualización y Métricas
 * Reemplaza la lógica antigua de cálculo en JS por consumo de vistas SQL
 * 
 * @author Pablo (Data Analyst)
 * @version 2.0.0 (Hybrid Tech)
 */

/**
 * Genera/Actualiza el Dashboard usando latencia cero (Vistas SQL)
 * Esta función reemplaza la antigua lógica pesada.
 */
function actualizarDashboard() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  // Validar si tenemos año (el mes ya viene pre-calculado por año en la vista)
  let anio = filters.año_activo;
  
  if (!anio) {
    const anioResult = ui.prompt('Configuración', 'Ingresa el AÑO a visualizar:', ui.ButtonSet.OK_CANCEL);
    if (anioResult.getSelectedButton() !== ui.Button.OK) return;
    anio = parseInt(anioResult.getResponseText().trim());
  }
  
  const sheet = setupDashboardSheet_();
  sheet.getRange('B4').setValue('⏳ Obteniendo métricas de Supabase...');
  SpreadsheetApp.flush();
  
  try {
    // Usar la VISTA optimizada que ya tiene los cálculos
    // Filtramos por año en la petición REST
    const kpis = fetchAllWithFilters('vista_dashboard_kpis', '*', { anio: anio });
    
    if (kpis.length === 0) {
      ui.alert('ℹ️ No se encontraron datos para el año ' + anio);
      sheet.getRange('B4').setValue('Sin datos para ' + anio);
      return;
    }
    
    // Renderizamos (usando el primer registro del mes solicitado si existiera, o todos)
    // El dashboard original era MENSUAL. Vamos a pedir el mes.
    const mesResult = ui.prompt('Dashboard', 'Ingresa el MES (1-12) a detallar:', ui.ButtonSet.OK_CANCEL);
    if (mesResult.getSelectedButton() !== ui.Button.OK) return;
    const mes = parseInt(mesResult.getResponseText().trim());
    
    // Buscamos el KPI específico del mes en los datos descargados
    const kpiMes = kpis.find(k => k.mes === mes);
    
    if (!kpiMes) {
      ui.alert('ℹ️ No hay datos calculados para el mes ' + mes + '/' + anio);
      sheet.getRange('B4').setValue('Sin datos para ' + mes + '/' + anio);
      return;
    }
    
    renderDashboardOptimized_(sheet, kpiMes, mes, anio);
    ui.alert('✅ Dashboard actualizado (vía SQL View)');
    
  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
    sheet.getRange('B4').setValue('Error: ' + e.message);
  }
}

/**
 * Configura la hoja
 * @private
 */
function setupDashboardSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('DASHBOARD');
  
  if (!sheet) {
    sheet = ss.insertSheet('DASHBOARD', 0);
  }
  
  sheet.clear();
  sheet.setHiddenGridlines(true);
  
  // Anchos
  sheet.setColumnWidth(1, 20);
  sheet.setColumnWidth(2, 150);
  sheet.setColumnWidth(3, 100);
  sheet.setColumnWidth(4, 20);
  sheet.setColumnWidth(5, 150);
  sheet.setColumnWidth(6, 100);
  return sheet;
}

/**
 * Renderiza usando los datos pre-calculados
 * @private
 */
function renderDashboardOptimized_(sheet, metrics, mes, anio) {
  // Title
  sheet.getRange('B2').setValue('DASHBOARD OPERATIVO - ' + mes + '/' + anio).setFontSize(16).setFontWeight('bold');
  sheet.getRange('B2:F2').merge().setHorizontalAlignment('center').setBackground('#10b981').setFontColor('white');
  
  // KPIs Cards
  const fillRate = metrics.porcentaje_cobertura / 100; // Viene como 95.5
  const vacantes = metrics.residentes_requeridos - metrics.turnos_cubiertos;
  
  drawCard_(sheet, 4, 2, 'COBERTURA (%)', metrics.porcentaje_cobertura + '%', fillRate >= 0.95 ? '#dcfce7' : '#fee2e2');
  drawCard_(sheet, 4, 5, 'VACANTES (Turnos)', vacantes, '#f3f4f6');
  
  drawCard_(sheet, 7, 2, 'TURNOS TOTALES', metrics.residentes_requeridos, '#f3f4f6');
  drawCard_(sheet, 7, 5, 'HORAS CUMPLIDAS', Math.round(metrics.horas_cumplidas), '#f3f4f6');
  
  // Nota footer
  sheet.getRange('B11').setValue('ℹ️ Datos calculados directamente en Supabase (Vista SQL)').setFontStyle('italic').setFontColor('#6b7280');
}

/**
 * Helper para dibujar tarjetas
 */
function drawCard_(sheet, row, col, title, value, color) {
  sheet.getRange(row, col).setValue(title).setFontSize(10).setFontColor('#6b7280');
  sheet.getRange(row + 1, col).setValue(value).setFontSize(24).setFontWeight('bold');
  
  const range = sheet.getRange(row, col, 2, 2);
  range.merge();
  range.setBorder(true, true, true, true, null, null, '#e5e7eb', SpreadsheetApp.BorderStyle.SOLID);
  if (color) range.setBackground(color);
  range.setHorizontalAlignment('center').setVerticalAlignment('middle');
}
