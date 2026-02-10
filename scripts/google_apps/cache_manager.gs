/**
 * CACHE MANAGER - Sistema de caché inteligente para datos estáticos/semi-estáticos
 * Arquitectura Híbrida: Reduce llamadas a Supabase cacheando datos de baja volatilidad
 * 
 * @author Pablo (Data Analyst)
 * @version 1.0.0
 */

// ============================================================================
// CONFIGURACIÓN DE CACHÉ
// ============================================================================

const CACHE_CONFIG = {
  // Datos MUY estáticos (refrescar manualmente o cada 7 días)
  '_CACHE_DIAS': {
    source: 'dias',
    select: 'id_dia,fecha,es_feriado,descripcion_feriado,anio',
    filter: null,
    ttlMinutes: 60 * 24 * 7,  // 7 días
    hidden: true
  },
  '_CACHE_TURNOS': {
    source: 'turnos',
    select: 'id_turno,tipo_turno,descripcion,cant_horas,hora_inicio,hora_fin,activo',
    filter: null,
    ttlMinutes: 60 * 24 * 7,  // 7 días
    hidden: true
  },
  '_CACHE_PERSONAL': {
    source: 'datos_personales',
    select: 'id_agente,dni,nombre,apellido,cohorte,activo',
    filter: { activo: true },
    ttlMinutes: 60 * 24,  // 1 día
    hidden: true
  },
  
  // Datos semi-dinámicos (refrescar cada hora o al iniciar trabajo)
  '_CACHE_PLANI_ANIO': {
    source: 'planificacion',  // CAMBIO TEMPORAL: Usar tabla directa para asegurar campo 'lugar'
    select: '*',
    filter: null,  // Se aplica año_activo dinámicamente
    ttlMinutes: 60,  // 1 hora
    hidden: true
  }
};

// ============================================================================
// GESTIÓN DE CACHÉ
// ============================================================================

/**
 * Refresca una caché específica
 * @param {string} cacheName - Nombre de la caché (ej: '_CACHE_DIAS')
 */
function refreshCache(cacheName) {
  const config = CACHE_CONFIG[cacheName];
  if (!config) {
    throw new Error('Caché no configurada: ' + cacheName);
  }
  
  Logger.log('🔄 Refrescando caché: ' + cacheName);
  
  // Aplicar filtros dinámicos
  let filters = config.filter ? Object.assign({}, config.filter) : {};
  
  // Filtro especial para planificación: usar año_activo
  if (cacheName === '_CACHE_PLANI_ANIO') {
    const activeFilters = getActiveFilters();
    if (activeFilters.año_activo) {
      filters.anio = activeFilters.año_activo;
    }
  }
  
  // Fetch datos
  const data = Object.keys(filters).length > 0 
    ? fetchAllWithFilters(config.source, config.select, filters)
    : fetchAll(config.source, config.select);
  
  // ⚠️ SIEMPRE limpiar la hoja de caché antes de escribir (aunque no haya datos)
  // Esto evita que queden datos viejos de otro año/filtro
  const sheet = getOrCreateCacheSheet_(cacheName, config.hidden);
  sheet.clear();
  
  if (!data || data.length === 0) {
    Logger.log('⚠️ Caché ' + cacheName + ' vacía (0 registros para filtros actuales)');
    // Guardar metadata indicando que está vacía pero actualizada
    setCacheMetadata_(cacheName, {
      lastRefresh: new Date().toISOString(),
      recordCount: 0,
      ttlMinutes: config.ttlMinutes
    });
    return 0;
  }
  
  // Escribir datos a hoja
  writeCacheData_(sheet, data);
  
  // Guardar metadata de última actualización
  setCacheMetadata_(cacheName, {
    lastRefresh: new Date().toISOString(),
    recordCount: data.length,
    ttlMinutes: config.ttlMinutes
  });
  
  Logger.log('✅ Caché ' + cacheName + ': ' + data.length + ' registros');
  return data.length;
}

/**
 * Obtiene datos de caché (refresca si expiró)
 * @param {string} cacheName - Nombre de la caché
 * @param {boolean} forceRefresh - Forzar refresco aunque no haya expirado
 * @returns {Array} Datos cacheados
 */
function getCacheData(cacheName, forceRefresh) {
  const metadata = getCacheMetadata_(cacheName);
  
  // Verificar si necesita refrescar
  if (forceRefresh || !metadata || isCacheExpired_(metadata)) {
    refreshCache(cacheName);
  }
  
  // Leer de hoja
  return readCacheData_(cacheName);
}

/**
 * Refresca todas las cachés
 */
function refreshAllCaches() {
  const ui = SpreadsheetApp.getUi();
  let total = 0;
  
  for (const cacheName in CACHE_CONFIG) {
    try {
      total += refreshCache(cacheName);
    } catch (e) {
      Logger.log('❌ Error en caché ' + cacheName + ': ' + e.message);
    }
  }
  
  ui.alert('✅ Cachés actualizadas\n\n' + total + ' registros totales cargados');
}

/**
 * Muestra estado de todas las cachés
 */
function showCacheStatus() {
  const ui = SpreadsheetApp.getUi();
  let status = '📊 ESTADO DE CACHÉS\n\n';
  
  for (const cacheName in CACHE_CONFIG) {
    const metadata = getCacheMetadata_(cacheName);
    if (metadata) {
      const expired = isCacheExpired_(metadata) ? '⚠️ EXPIRADA' : '✅ OK';
      const lastRefresh = new Date(metadata.lastRefresh).toLocaleString();
      status += cacheName + '\n';
      status += '  Registros: ' + metadata.recordCount + '\n';
      status += '  Última act.: ' + lastRefresh + '\n';
      status += '  Estado: ' + expired + '\n\n';
    } else {
      status += cacheName + ': ❌ No inicializada\n\n';
    }
  }
  
  ui.alert(status);
}

// ============================================================================
// FUNCIONES AUXILIARES PRIVADAS
// ============================================================================

/**
 * Crea u obtiene hoja de caché
 * @private
 */
function getOrCreateCacheSheet_(name, hidden) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (hidden) {
      sheet.hideSheet();
    }
  }
  
  return sheet;
}

/**
 * Escribe datos en hoja de caché
 * @private
 */
function writeCacheData_(sheet, data) {
  sheet.clear();
  
  if (data.length === 0) return;
  
  // Headers
  const headers = Object.keys(data[0]);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Data
  const rows = data.map(row => headers.map(h => row[h]));
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
}

/**
 * Lee datos de hoja de caché
 * @private
 */
function readCacheData_(cacheName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(cacheName);
  
  if (!sheet) return [];
  
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) return [];
  
  const headers = values[0];
  const data = [];
  
  for (let i = 1; i < values.length; i++) {
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[i][idx];
    });
    data.push(row);
  }
  
  return data;
}

/**
 * Guarda metadata de caché en PropertiesService
 * @private
 */
function setCacheMetadata_(cacheName, metadata) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('CACHE_META_' + cacheName, JSON.stringify(metadata));
}

/**
 * Obtiene metadata de caché
 * @private
 */
function getCacheMetadata_(cacheName) {
  const props = PropertiesService.getScriptProperties();
  const raw = props.getProperty('CACHE_META_' + cacheName);
  return raw ? JSON.parse(raw) : null;
}

/**
 * Verifica si la caché expiró
 * @private
 */
function isCacheExpired_(metadata) {
  if (!metadata || !metadata.lastRefresh) return true;
  
  const lastRefresh = new Date(metadata.lastRefresh);
  const now = new Date();
  const diffMinutes = (now - lastRefresh) / (1000 * 60);
  
  return diffMinutes > metadata.ttlMinutes;
}

// ============================================================================
// LOOKUPS RÁPIDOS (usan caché)
// ============================================================================

/**
 * Obtiene id_dia desde fecha (usa caché)
 */
function getIdDiaFromFecha(fecha) {
  const dias = getCacheData('_CACHE_DIAS');
  const fechaStr = formatDate_(fecha);
  
  for (const d of dias) {
    if (d.fecha === fechaStr) {
      return d.id_dia;
    }
  }
  return null;
}

/**
 * Obtiene id_turno desde tipo_turno (usa caché)
 */
function getIdTurnoFromTipo(tipoTurno) {
  const turnos = getCacheData('_CACHE_TURNOS');
  const tipo = String(tipoTurno).trim().toLowerCase();
  
  for (const t of turnos) {
    if (String(t.tipo_turno).toLowerCase() === tipo) {
      return t.id_turno;
    }
  }
  return null;
}

/**
 * Obtiene id_agente desde DNI (usa caché)
 */
function getIdAgenteFromDni(dni) {
  const personal = getCacheData('_CACHE_PERSONAL');
  const dniStr = String(dni).trim();
  
  for (const p of personal) {
    if (String(p.dni).trim() === dniStr) {
      return p.id_agente;
    }
  }
  return null;
}

/**
 * Obtiene nombre completo desde id_agente (usa caché)
 */
function getNombreFromIdAgente(idAgente) {
  const personal = getCacheData('_CACHE_PERSONAL');
  
  for (const p of personal) {
    if (p.id_agente === idAgente) {
      return p.apellido + ', ' + p.nombre;
    }
  }
  return 'ID ' + idAgente;
}
