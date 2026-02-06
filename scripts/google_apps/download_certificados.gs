/**
 * DOWNLOAD CERTIFICADOS - Gestión de entrega de certificados
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

function downloadCertificadosPendientes() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    // Descargar certificados (filtro opcional: solo presentados?)
    // Por ahora bajamos todo el historial reciente o filtramos por año
    const anio = new Date().getFullYear();
    
    // Usamos vista_certificados_completa
    // Filtramos por año de inasistencia o año actual
    const data = fetchAllWithFilters('vista_certificados_completa', '*', {
      // Podríamos filtrar, pero mejor traer todo lo activo
    });
    
    // Filtrar localmente por año si es necesario para no saturar
    // O mejor: traer últimos 500
    
    if (data.length === 0) {
      ui.alert('ℹ️ No hay certificados registrados.');
    }
    
    const sheet = getOrCreateSheet_('CERTIFICADOS');
    
    const headers = [
      'sincronizar',
      'id_certificado', 'agente', 'dni', 
      'fecha_entrega', 'fecha_justificada', 
      'tipo', 'estado', 'observaciones',
      'id_inasistencia', 'id_agente', 'sync_status'
    ];
    
    const rows = data.map(r => [
      false,
      r.id_certificado,
      r.agente,
      r.dni,
      r.fecha_entrega_certificado,
      r.fecha_inasistencia_justifica,
      r.tipo_certificado || 'medico',
      r.estado_certificado || 'presentado',
      r.observaciones || '',
      r.id_inasistencia,
      r.id_agente,
      '✅'
    ]);
    
    sheet.clear();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers])
         .setFontWeight('bold')
         .setBackground('#fbbc04'); // Amarillo
         
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Validation Checkbox
      const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
      const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
      checkboxRange.setDataValidation(rule);
      
      // Dropdown Tipo
      const tipos = ['medico', 'academico', 'otro'];
      sheet.getRange(2, 7, rows.length, 1).setDataValidation(
        SpreadsheetApp.newDataValidation().requireValueInList(tipos).build()
      );
      
      // Dropdown Estado
      const estados = ['presentado', 'aprobado', 'rechazado'];
      sheet.getRange(2, 8, rows.length, 1).setDataValidation(
        SpreadsheetApp.newDataValidation().requireValueInList(estados).build()
      );
    }
    
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, headers.length);
    
    ui.alert('✅ ' + rows.length + ' certificados descargados.');
    
  } catch(e) {
    ui.alert('❌ Error: ' + e.message);
  }
}
