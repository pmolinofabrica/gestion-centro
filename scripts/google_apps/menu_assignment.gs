/**
 * MENÚ ASIGNACIONES - Interfaz de Usuario v2.0
 */

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🏠 Asignaciones')
    .addItem('👤 Ver Disponibles (Pop-up)', 'checkDisponiblesUI_')
    .addSeparator()
    .addSubMenu(ui.createMenu('📅 Gestión Calendario')
        .addItem('📥 Descargar (Mensual)', 'downloadCalendarioDispositivos')
        .addItem('📊 Ver Estado Planificado', 'downloadEstadoCalendario')
        .addSeparator()
        .addItem('📝 Generar Asignación Diaria (NUEVO)', 'generarPlantillaAsignacionDiaria')
        .addSeparator()
        .addItem('🏗️ Generar Plantilla Diseño', 'generarPlantillaDiseño')
        .addItem('🚀 Subir Diseño Matriz', 'uploadDiseñoMatriz'))
    .addSeparator()
    .addSubMenu(ui.createMenu('🏢 Gestión Dispositivos')
        .addItem('📥 Descargar Referencia', 'downloadDispositivos')
        .addItem('📤 Cargar Nuevos', 'uploadDispositivos'))
    .addSeparator()
    .addItem('📥 Descargar Historial Asignaciones', 'downloadAsignaciones')
    .addItem('📚 Historial de Capacitaciones (VISTA)', 'downloadHistorialCapacitaciones')
    .addToUi();
}

/**
 * Función auxiliar para UI
 */
function checkDisponiblesUI_() {
  const ui = SpreadsheetApp.getUi();
  const respFecha = ui.prompt('Fecha (YYYY-MM-DD):', ui.ButtonSet.OK_CANCEL);
  if (respFecha.getSelectedButton() !== ui.Button.OK) return;
  
  const respTurno = ui.prompt('ID Turno:', ui.ButtonSet.OK_CANCEL);
  if (respTurno.getSelectedButton() !== ui.Button.OK) return;

  try {
    const datos = obtenerDisponibles(respFecha.getResponseText().trim(), parseInt(respTurno.getResponseText().trim()));
    if (datos.residentes.length === 0) {
      ui.alert('Información', datos.mensaje, ui.ButtonSet.OK);
      return;
    }
    
    let msg = `Encontrados: ${datos.residentes.length}\n\n`;
    msg += datos.residentes.slice(0, 15).map(r => `- ${r.nombre_completo} ${r.icono_alerta}`).join('\n');
    if (datos.residentes.length > 15) msg += '\n...';
    
    ui.alert('Disponibles', msg, ui.ButtonSet.OK);
    
  } catch (e) {
    ui.alert('Error', e.message, ui.ButtonSet.OK);
  }
}
