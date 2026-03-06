/**
 * sync_formularios.gs
 * ============================================================
 * Integración automática: Google Forms → Supabase
 * Tablas: inasistencias | tardanzas | descansos
 *
 * Depende de: db_helpers.gs (getSupabaseConfig_, buildHeaders_,
 *             upsertRecord, fetchAll)
 *
 * INSTALACIÓN (una vez por cada sheet vinculado al form):
 *   1. Abrir el Google Sheet del formulario → Extensiones → Apps Script
 *   2. Pegar este código junto a db_helpers.gs
 *   3. Correr la función `instalarTrigger_NOMBRE()` correspondiente
 *   4. Autorizar permisos
 *
 * CONVENCIÓN DE NOMBRES DE COLUMNAS (índices en e.values):
 *   Inasistencias: [0]MarcaTemporal [1]Email [2]Residente [3]Fecha [4]Motivo
 *   Tardanzas:     [0]MarcaTemporal [1]Email [2]Fecha     [3]Residente
 *   Descansos:     [0]MarcaTemporal [1]Email [2]Residente [3..N]Días
 * ============================================================
 */

// ============================================================
// HELPER: NORMALIZACIÓN DE FECHA
// Convierte seriales Excel, strings "DD/M", "M/D/YYYY" → "YYYY-MM-DD"
// ============================================================
function normalizarFecha_(val, anioContexto) {
  anioContexto = anioContexto || 2026;
  if (!val && val !== 0) return null;

  // Date object (Google Sheets puede pasar un Date directamente)
  if (val instanceof Date) {
    return Utilities.formatDate(val, 'America/Argentina/Buenos_Aires', 'yyyy-MM-dd');
  }

  // Número → serial Excel (días desde 30/12/1899)
  if (typeof val === 'number') {
    var d = new Date(new Date(1899, 11, 30).getTime() + Math.floor(val) * 86400000);
    return Utilities.formatDate(d, 'America/Argentina/Buenos_Aires', 'yyyy-MM-dd');
  }

  // Calcular el año actual para forzarlo y evitar errores de validación de los residentes (e.g. "0026", "2025")
  var y = new Date().getFullYear();

  var s = String(val).trim();

  // "26/2" → DD/M sin año
  if (/^\d{1,2}\/\d{1,2}$/.test(s)) {
    var p = s.split('/');
    return y + '-' + p[1].padStart(2,'0') + '-' + p[0].padStart(2,'0');
  }

  // "2/27/2026" o "2/27/0026" (bug de año en Google Forms, M/D/YYYY original vs D/M/YYYY nuevo)
  // Las Form responses actuales vienen como DD/MM/YYYY ej: 20/2/2026
  if (/^\d{1,2}\/\d{1,2}\/\d+$/.test(s)) {
    var p2 = s.split('/');
    // Ignoramos completamente el año tipeado por el usuario (p2[2]) y usamos el año forzado (y)
    // p2[0] = DD, p2[1] = MM en los forms en Español
    return y + '-' + p2[1].padStart(2,'0') + '-' + p2[0].padStart(2,'0');
  }

  // Si ya viene en formato de Base de Datos, intentar arreglar el año también
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
     var p3 = s.split('-');
     return y + '-' + p3[1] + '-' + p3[2];
  }

  Logger.log('⚠️ normalizarFecha_: no se pudo parsear: ' + val);
  return null;
}

// ============================================================
// HELPER: RESOLUCIÓN DE AGENTE
// "Apellido, Nombre" del form → id_agente en Supabase
// ============================================================
var _cacheAgentes = null; // Cache en memoria durante la ejecución

function resolverIdAgente_(nombreForm) {
  if (!nombreForm) return null;

  // Cargar cache de agentes (una sola request por ejecución)
  if (!_cacheAgentes) {
    _cacheAgentes = fetchAll('datos_personales', 'id_agente,apellido,nombre') || [];
  }

  var partes    = String(nombreForm).split(',');
  var apellido  = partes[0].trim().toLowerCase();
  var nombre    = partes.length > 1 ? partes[1].trim().toLowerCase() : '';

  var matches = _cacheAgentes.filter(function(a) {
    return a.apellido && a.apellido.toLowerCase().indexOf(apellido) >= 0;
  });

  if (matches.length === 1) return matches[0].id_agente;

  // Si hay múltiples: refinar por primer nombre
  if (matches.length > 1 && nombre) {
    var nombre0 = nombre.split(' ')[0];
    var refined = matches.filter(function(a) {
      return a.nombre && a.nombre.toLowerCase().indexOf(nombre0) >= 0;
    });
    if (refined.length === 1) return refined[0].id_agente;
  }

  Logger.log('⚠️ resolverIdAgente_: no match único para "' + nombreForm + '" (' + matches.length + ' matches)');
  return null;
}

// ============================================================
// TRIGGER: INASISTENCIAS
// Sheet: "Aviso de inasistencia - 2026 (Respuestas)"
// Tabla: inasistencias(id_agente, fecha_inasistencia, motivo)
// UPSERT key: (id_agente, fecha_inasistencia)
// ============================================================
function onSubmitInasistencia(e) {
  try {
    _cacheAgentes = null; // Reset cache por ejecución
    var row = e.values;
    // [0]MarcaTemporal [1]Email [2]Residente [3]Fecha [4]Motivo
    var nombreForm = row[2];
    var fechaDB    = normalizarFecha_(row[3]);
    var motivoRaw = row[4] || '';
    
    // Mapeo DAMA para reducir cardinalidad y agregar flags booleanos
    // Valores validos en DB: 'medico', 'estudio', 'imprevisto', 'injustificada', 'otro_justificada'
    var motivoFinal = 'otro_justificada';
    var requiereCertificado = false;
    var generaDescuento = false;

    if (motivoRaw.indexOf('enfermedad') !== -1) {
      motivoFinal = 'medico';
      requiereCertificado = true;
    } else if (motivoRaw.indexOf('estudio') !== -1) {
      motivoFinal = 'estudio';
      requiereCertificado = true;
    } else if (motivoRaw.indexOf('imprevisto') !== -1) {
      motivoFinal = 'imprevisto';
    } else if (motivoRaw.indexOf('injustificada') !== -1) {
      motivoFinal = 'injustificada';
      generaDescuento = true;
    }

    var idAgente = resolverIdAgente_(nombreForm);
    if (!idAgente || !fechaDB) {
      var msg = !idAgente ? 'Residente no encontrado: ' + nombreForm : 'Fecha inválida: ' + row[3];
      Logger.log('❌ INASISTENCIA: ' + msg);
      _alertar_('No se pudo registrar inasistencia', msg);
      return;
    }

    var res = upsertRecord('inasistencias', {
      id_agente:            idAgente,
      fecha_inasistencia:   fechaDB,
      motivo:               motivoFinal,
      requiere_certificado: requiereCertificado,
      genera_descuento:     generaDescuento,
      fecha_aviso:          new Date().toISOString(),
      estado:               'pendiente'
    }, ['id_agente', 'fecha_inasistencia']);

    if (res.success) {
      Logger.log('✅ Inasistencia: ' + nombreForm + ' - ' + fechaDB);
    } else {
      Logger.log('❌ Supabase inasistencias: ' + res.error);
      _alertar_('Error al registrar inasistencia', res.error);
    }
  } catch(err) {
    Logger.log('❌ Excepción onSubmitInasistencia: ' + err.message);
    _alertar_('Excepción sync inasistencias', err.message);
  }
}

// ============================================================
// TRIGGER: TARDANZAS
// Sheet: "Tardanzas Residencias Molino 2026 (Respuestas)"
// Tabla: tardanzas(id_agente, fecha)
// UPSERT key: (id_agente, fecha)
// ============================================================
function onSubmitTardanza(e) {
  try {
    _cacheAgentes = null;
    var row = e.values;
    // [0]MarcaTemporal [1]Email [2]Fecha [3]Residente
    var fechaDB    = normalizarFecha_(row[2]);
    var nombreForm = row[3];

    var idAgente = resolverIdAgente_(nombreForm);
    if (!idAgente || !fechaDB) {
      var msg = !idAgente ? 'Residente no encontrado: ' + nombreForm : 'Fecha inválida: ' + row[2];
      Logger.log('❌ TARDANZA: ' + msg);
      _alertar_('No se pudo registrar tardanza', msg);
      return;
    }

    var res = upsertRecord('tardanzas', {
      id_agente:    idAgente,
      fecha:        fechaDB,
      observaciones: 'Registrado automáticamente desde formulario'
    }, ['id_agente', 'fecha']);

    if (res.success) {
      Logger.log('✅ Tardanza: ' + nombreForm + ' - ' + fechaDB);
    } else {
      Logger.log('❌ Supabase tardanzas: ' + res.error);
      _alertar_('Error al registrar tardanza', res.error);
    }
  } catch(err) {
    Logger.log('❌ Excepción onSubmitTardanza: ' + err.message);
    _alertar_('Excepción sync tardanzas', err.message);
  }
}

// ============================================================
// TRIGGER: DESCANSOS
// Sheet: "Pedido de fin de semana - 2026 (Respuestas)"
// Tabla: descansos(id_agente, dia_solicitado, mes_solicitado)
// UPSERT key: (id_agente, dia_solicitado)
// ============================================================
function onSubmitDescanso(e) {
  try {
    _cacheAgentes = null;
    var row = e.values;
    // [0]MarcaTemporal [1]Email [2]Residente [3..N]Fechas
    var nombreForm = row[2];
    var fechasRaw  = row.slice(3);

    var idAgente = resolverIdAgente_(nombreForm);
    if (!idAgente) {
      Logger.log('❌ DESCANSO: Residente no encontrado: ' + nombreForm);
      _alertar_('No se pudo registrar descanso', 'Residente no encontrado: ' + nombreForm);
      return;
    }

    var registrados = 0;
    fechasRaw.forEach(function(fechaRaw) {
      if (!fechaRaw && fechaRaw !== 0) return;
      var fechaDB = normalizarFecha_(fechaRaw);
      if (!fechaDB) return;

      var mes = parseInt(fechaDB.split('-')[1]); // Extrae mes del YYYY-MM-DD

      var res = upsertRecord('descansos', {
        id_agente:        idAgente,
        dia_solicitado:   fechaDB,
        mes_solicitado:   mes,
        estado:           'pendiente',
        fecha_solicitud:  new Date().toISOString()
      }, ['id_agente', 'dia_solicitado']);

      if (res.success) { registrados++; }
      else { Logger.log('❌ Descanso ' + fechaDB + ': ' + res.error); }
    });

    Logger.log('✅ Descansos: ' + nombreForm + ' - ' + registrados + ' días registrados');
  } catch(err) {
    Logger.log('❌ Excepción onSubmitDescanso: ' + err.message);
    _alertar_('Excepción sync descansos', err.message);
  }
}

// ============================================================
// INSTALADORES DE TRIGGER (ejecutar UNA SOLA VEZ por sheet)
// ============================================================
function instalarTriggerInasistencias() {
  ScriptApp.newTrigger('onSubmitInasistencia')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit().create();
  Logger.log('✅ Trigger Inasistencias instalado.');
}

function instalarTriggerTardanzas() {
  ScriptApp.newTrigger('onSubmitTardanza')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit().create();
  Logger.log('✅ Trigger Tardanzas instalado.');
}

function instalarTriggerDescansos() {
  ScriptApp.newTrigger('onSubmitDescanso')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit().create();
  Logger.log('✅ Trigger Descansos instalado.');
}

// ============================================================
// SYNC MASIVO DEL BACKLOG HISTÓRICO
// Procesa todas las filas ya existentes en el sheet.
// Idempotente: usa UPSERT, seguro correr múltiples veces.
// ============================================================
function syncMasivoInasistencias() {
  _syncMasivo_(onSubmitInasistencia, 'Inasistencias');
}
function syncMasivoTardanzas() {
  _syncMasivo_(onSubmitTardanza, 'Tardanzas');
}
function syncMasivoDescansos() {
  _syncMasivo_(onSubmitDescanso, 'Descansos');
}

function _syncMasivo_(fn, nombre) {
  var data = SpreadsheetApp.getActiveSpreadsheet()
    .getSheets()[0].getDataRange().getValues();
  var ok = 0, err = 0;
  for (var i = 1; i < data.length; i++) {
    _cacheAgentes = null; // No acumular cache entre filas en sincronía masiva
    try { fn({ values: data[i] }); ok++; }
    catch(ex) { err++; Logger.log('❌ Fila ' + (i+1) + ': ' + ex.message); }
    Utilities.sleep(80); // Evitar rate limit de Supabase
  }
  Logger.log('Sync ' + nombre + ': ' + ok + ' OK, ' + err + ' errores');
  SpreadsheetApp.getUi().alert('Sync ' + nombre + ': ' + ok + ' registrados, ' + err + ' errores.');
}

