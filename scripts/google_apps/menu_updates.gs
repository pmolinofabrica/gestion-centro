/**
 * MENÚ PRINCIPAL - Definición del menú de la hoja de cálculo
 * 
 * @author Pablo (Data Analyst)
 * @version 3.0.0 - Refactored: menu-only, no data functions
 */

/**
 * Menú completo con estructura reorganizada (v3.0 - User Centric)
 * Todas las funciones referenciadas están definidas en sus archivos respectivos.
 */
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  var menu = ui.createMenu('🔌 Supabase');
  
  // === GRUPO 1: PLANIFICACIÓN Y TURNOS (Operativo Diario) ===
  var planiMenu = ui.createMenu('📅 Planificación y Turnos');
  
  // Descargas
  planiMenu.addItem('📥 Descargar Planificación (Anual)', 'downloadPlanificacion');
  planiMenu.addItem('📥 Descargar Convocatoria (Mes)', 'downloadConvocatoriaMes');
  planiMenu.addSeparator();
  planiMenu.addItem('✏️ Gestión de Turnos', 'downloadTurnos');
  planiMenu.addItem('✏️ Gestión de Feriados', 'downloadDiasFeriados');
  planiMenu.addItem('📊 Ver Estado de Cobertura', 'loadEstadoCobertura');
  
  planiMenu.addSeparator();
  
  // Guardados (Sync)
  planiMenu.addItem('📤 Guardar Planificación', 'syncPlanificacion');
  planiMenu.addItem('📤 Guardar Convocatoria', 'syncConvocatoria');
  planiMenu.addItem('📤 Guardar Turnos', 'syncTurnos');
  planiMenu.addItem('📤 Guardar Feriados', 'syncDiasFeriados');
  
  menu.addSubMenu(planiMenu);
  
  // === GRUPO 2: SEGUIMIENTO RESIDENTES (Gestión RRHH) ===
  var rrhhMenu = ui.createMenu('👥 Seguimiento Residentes');
  
  // Dashboard y Reportes
  rrhhMenu.addItem('📊 Ver Tablero de Control', 'loadSeguimientoResidentes');
  rrhhMenu.addItem('⚖️ Ver Saldos de Horas', 'downloadSaldosResumen');
  rrhhMenu.addItem('📥 Descargar Grupos de Escuelas (Jue y Vie)', 'downloadGruposEscuelas');
  rrhhMenu.addSeparator();
  
  // Datos Personales
  rrhhMenu.addItem('📥 Descargar Datos Personales', 'loadDatosPersonales');
  rrhhMenu.addItem('📤 Guardar Datos Personales', 'syncDatosPersonales');
  rrhhMenu.addSeparator();
  
  // Incidencias
  rrhhMenu.addItem('📥 Descargar Inasistencias (Mes)', 'downloadInasistenciasMes');
  rrhhMenu.addItem('📥 Descargar Certificados Pend.', 'downloadCertificadosPendientes');
  rrhhMenu.addItem('📤 Guardar Inasistencias', 'syncInasistencias');
  rrhhMenu.addItem('📤 Guardar Certificados', 'syncCertificados');
  
  menu.addSubMenu(rrhhMenu);
  
  menu.addSeparator();
  
  // === GRUPO 3: AVANZADO / ADMIN ===
  var adminMenu = ui.createMenu('⚙️ Avanzado / Admin');
  
  // Mantenimiento
  adminMenu.addItem('🔄 Recargar Todo (Solucionar Errores)', 'forzarRecargaCompleta');
  adminMenu.addItem('⚙️ Configurar Año/Cohorte', 'configurarFiltros');
  adminMenu.addItem('🧹 Limpiar Estados (✅/❌)', 'clearAllSyncStatus');
  adminMenu.addSeparator();
  
  // Diagnóstico
  adminMenu.addItem('🧪 Test Conexión', 'testConnection');
  adminMenu.addItem('🐞 Debug Convocatoria (Última Fila)', 'debugConvocatoriaLastRow');
  adminMenu.addItem('📊 Estado de Caché', 'showCacheStatus');
  
  // Cálculos manuales
  adminMenu.addSeparator();
  adminMenu.addItem('🧮 Calcular Saldos Mensuales', 'calcularSaldosMensuales');
  
  menu.addSubMenu(adminMenu);
  
  menu.addToUi();
}
