/**
 * Carga días en hoja "REF_DIAS"
 */
/**
 * Carga días en hoja "REF_DIAS" (Filtrado por año activo si existe)
 */
function loadDias() {
  // Pedir columna 'anio' también para poder filtrar
  const data = fetchAll('dias', 'id_dia,fecha,es_feriado,descripcion_feriado,anio');
  
  if (data.length === 0) return;
  
  // Obtener filtro de configuración
  let filteredData = data;
  try {
    const filters = getActiveFilters();
    if (filters && filters.año_activo) {
      const anioStr = String(filters.año_activo);
      filteredData = data.filter(d => String(d.anio) === anioStr);
      Logger.log('📅 Filtrando días por año: ' + anioStr + ' (' + filteredData.length + '/' + data.length + ')');
    }
  } catch (e) {
    Logger.log('⚠️ No se pudieron cargar filtros, mostrando todo: ' + e.message);
  }
  
  const sheet = getOrCreateSheet_('REF_DIAS');
  const headers = ['id_dia', 'fecha', 'es_feriado', 'descripcion_feriado']; // No mostramos 'anio' para mantener compatibilidad
  const rows = filteredData.map(r => [r.id_dia, r.fecha, r.es_feriado, r.descripcion_feriado]);
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  
  const ui = SpreadsheetApp.getUi();
  ui.alert('✅ REF_DIAS actualizada: ' + rows.length + ' registros');
}

/**
 * Limpia todas las columnas sync_status
 */
function clearAllSyncStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  
  sheets.forEach(sheet => {
    clearSyncStatus(sheet.getName());
  });
  
  SpreadsheetApp.getUi().alert('✅ Status limpiado en todas las hojas');
}
