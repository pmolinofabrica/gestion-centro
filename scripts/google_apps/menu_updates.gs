/**
 * FUNCIONES MENU - Menú actualizado con todas las opciones
 * @author Pablo (Data Analyst)
 * @version 2.0.0
 */

/**
 * Obtiene todos los registros de una tabla (con soporte para filtros y paginación)
 * @param {string} table - Nombre de la tabla
 * @param {string} select - Columnas a seleccionar (default: *)
 * @param {Object} filters - Filtros opcionales {campo: valor}
 * @returns {Array} Registros
 */
function fetchAllWithFilters(table, select, filters) {
  const PAGE_SIZE = 1000;
  let allData = [];
  let offset = 0;
  let hasMore = true;
  
  // Construir query base con filtros
  let queryBase = '?select=' + (select || '*');
  
  if (filters) {
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined) {
        if (key.endsWith('_gte')) {
          queryBase += '&' + key.replace('_gte', '') + '=gte.' + filters[key];
        } else if (key.endsWith('_lt')) {
          queryBase += '&' + key.replace('_lt', '') + '=lt.' + filters[key];
        } else {
          queryBase += '&' + key + '=eq.' + filters[key];
        }
      }
    });
  }
  
  Logger.log('📥 Fetching ' + table + ' (filtered)...');
  
  while (hasMore) {
    const rangeStart = offset;
    const rangeEnd = offset + PAGE_SIZE - 1;
    
    const config = getSupabaseConfig_();
    const url = config.url + '/rest/v1/' + table + queryBase;
    
    const options = {
      method: 'GET',
      headers: Object.assign(buildHeaders_(config.key), {
        'Range': rangeStart + '-' + rangeEnd
      }),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    if (code === 200 || code === 206) {
      const pageData = JSON.parse(body);
      allData = allData.concat(pageData);
      
      const contentRange = response.getHeaders()['Content-Range'];
      if (contentRange) {
        const match = contentRange.match(/(\d+)-(\d+)\/(\d+|\*)/);
        if (match) {
          const end = parseInt(match[2]);
          const total = match[3] === '*' ? Infinity : parseInt(match[3]);
          hasMore = (end + 1) < total;
          offset = end + 1;
          
          if (hasMore) {
            Logger.log('   📄 Página ' + Math.floor(offset / PAGE_SIZE) + ': ' + pageData.length + ' registros');
          }
        } else {
          hasMore = false;
        }
      } else {
        hasMore = false;
      }
      
      if (pageData.length === 0) {
        hasMore = false;
      }
      
    } else {
      Logger.log('❌ Error en ' + table + ': ' + code);
      hasMore = false;
    }
  }
  
  Logger.log('✅ ' + table + ': ' + allData.length + ' registros totales');
  return allData;
}

/**
 * Menú completo con todas las opciones (v2.0 - Arquitectura Híbrida)
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  const menu = ui.createMenu('🔌 Supabase');
  
  // Test
  menu.addItem('🧪 Test Conexión', 'testConnection');
  menu.addSeparator();
  
  // Configuración
  const configMenu = ui.createMenu('⚙️ Configuración');
  configMenu.addItem('Configurar Filtros (Año/Cohorte)', 'configurarFiltros');
  configMenu.addItem('Ver Filtros Activos', 'mostrarFiltrosActivos');
  menu.addSubMenu(configMenu);
  menu.addSeparator();
  
  // === NUEVO: Descargas Optimizadas (usan vistas) ===
  const optimizedMenu = ui.createMenu('⚡ Descarga Rápida (Vistas)');
  optimizedMenu.addItem('📅 Convocatoria Mes Actual', 'downloadConvocatoriaMesActual');
  optimizedMenu.addItem('📅 Convocatoria por Mes', 'downloadConvocatoriaMes');
  optimizedMenu.addItem('🏥 Inasistencias (Mes)', 'downloadInasistenciasMes');
  optimizedMenu.addItem('🏥 Certificados Pendientes', 'downloadCertificadosPendientes');
  optimizedMenu.addSeparator();
  optimizedMenu.addItem('📊 Seguimiento Residentes (Dashboard)', 'loadSeguimientoResidentes');
  optimizedMenu.addItem('⚖️ Saldos Resumen (Smart)', 'downloadSaldosResumen');
  optimizedMenu.addItem('🎯 Estado Cobertura', 'loadEstadoCobertura');
  optimizedMenu.addItem('📋 Planificación (Caché)', 'downloadPlanificacionConCache');
  menu.addSubMenu(optimizedMenu);
  
  // === NUEVO: Gestión de Caché ===
  const cacheMenu = ui.createMenu('💾 Caché');
  cacheMenu.addItem('🔄 Forzar Recarga Completa', 'forzarRecargaCompleta');
  cacheMenu.addSeparator();
  cacheMenu.addItem('🔃 Refrescar Todas', 'refreshAllCaches');
  cacheMenu.addItem('📊 Ver Estado', 'showCacheStatus');
  menu.addSubMenu(cacheMenu);
  menu.addSeparator();
  
  // Descargas completas (legacy, para casos especiales)
  const downloadMenu = ui.createMenu('📥 Descarga Completa');
  downloadMenu.addItem('👥 Datos Residentes (REF)', 'loadDatosPersonales');
  downloadMenu.addItem('🕐 Turnos (REF)', 'loadTurnos');
  downloadMenu.addItem('📅 Días (REF)', 'loadDias');
  downloadMenu.addSeparator();
  downloadMenu.addItem('✏️ Turnos (editable)', 'downloadTurnos');
  downloadMenu.addItem('✏️ Feriados (editable)', 'downloadDiasFeriados');
  downloadMenu.addItem('✏️ Inasistencias (editable)', 'downloadInasistenciasCompleta');
  downloadMenu.addSeparator();
  downloadMenu.addItem('📊 Planificación (TODO)', 'downloadPlanificacion');
  downloadMenu.addItem('👥 Convocatoria (TODO)', 'downloadConvocatoria');
  // Eliminado Saldos legacy
  menu.addSubMenu(downloadMenu);
  
  // Sincronizar a Supabase (Sheets → Supabase)
  const syncMenu = ui.createMenu('📤 Sincronizar a Supabase');
  syncMenu.addItem('🧑 Datos Personales', 'syncDatosPersonales');
  syncMenu.addItem('🕐 Turnos', 'syncTurnos');
  syncMenu.addItem('📅 Feriados', 'syncDiasFeriados');
  syncMenu.addItem('🏥 Inasistencias', 'syncInasistencias');
  syncMenu.addItem('🏥 Certificados', 'syncCertificados');
  syncMenu.addSeparator();
  syncMenu.addItem('📊 Planificación', 'syncPlanificacion');
  syncMenu.addItem('👥 Convocatoria', 'syncConvocatoria');
  // syncSaldos removido por ser cálculo automático
  menu.addSubMenu(syncMenu);
  
  menu.addSeparator();

  // Cálculos automáticos
  const calculosMenu = ui.createMenu('🧮 Cálculos Automáticos');
  calculosMenu.addItem('Calcular Saldos Mensuales', 'calcularSaldosMensuales');
  menu.addSubMenu(calculosMenu);

  
  menu.addSeparator();
  
  // Limpiar
  menu.addItem('🧹 Limpiar Status', 'clearAllSyncStatus');
  
  menu.addToUi();
}

