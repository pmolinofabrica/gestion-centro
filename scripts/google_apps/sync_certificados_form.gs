/**
 * sync_certificados_form.gs
 * ============================================================
 * Integración automática: Google Forms → Supabase
 * Tabla: certificados
 *
 * Depende de: db_helpers.gs (getSupabaseConfig_, buildHeaders_,
 *             upsertRecord, fetchAll) y sync_formularios.gs (normalizarFecha_, resolverIdAgente_, _alertar_)
 *
 * INSTALACIÓN (una vez por cada sheet vinculado al form):
 *   1. Abrir el Google Sheet del formulario → Extensiones → Apps Script
 *   2. Pegar este código junto a db_helpers.gs y sync_formularios.gs
 *   3. Correr la función `instalarTriggerCertificados()`
 *   4. Autorizar permisos
 *
 * CONVENCIÓN DE NOMBRES DE COLUMNAS (índices en e.values):
 *   Certificados: [0]MarcaTemporal [1]Email [2]Fecha inasistencia [3]Residente [4]Observaciones (opcional)
 * ============================================================
 */

// ============================================================
// TRIGGER: CERTIFICADOS
// Sheet: "Carga de Certificados (Respuestas)"
// Tabla: certificados(id_agente, fecha_inasistencia_justifica, observaciones, fecha_carga)
// UPSERT key: (id_agente, fecha_inasistencia_justifica)
// ============================================================
function onSubmitCertificado(e) {
  try {
    // _cacheAgentes se define en sync_formularios.gs
    if (typeof _cacheAgentes !== 'undefined') {
      _cacheAgentes = null; // Reset cache por ejecución
    }

    var row = e.values;
    // [0]MarcaTemporal [1]Email [2]Fecha inasistencia [3]Residente [4]Observaciones

    var marcaTemporal = row[0];
    var fechaDB       = normalizarFecha_(row[2]);
    var nombreForm    = row[3];
    var observaciones = row[4] || '';

    var idAgente = resolverIdAgente_(nombreForm);
    if (!idAgente || !fechaDB) {
      var msg = !idAgente ? 'Residente no encontrado: ' + nombreForm : 'Fecha inválida: ' + row[2];
      Logger.log('❌ CERTIFICADO: ' + msg);
      _alertar_('No se pudo registrar certificado', msg);
      return;
    }

    var fechaCargaISO = '';
    try {
        // Tratar de parsear la marca temporal
        fechaCargaISO = new Date(marcaTemporal).toISOString();
    } catch(e) {
        fechaCargaISO = new Date().toISOString();
    }

    // Insert en la tabla certificados
    // Como ahora la tabla es simple y solo guarda la referencia, intentamos upsert
    // asumiendo que un agente puede presentar un certificado por día de inasistencia.
    var res = upsertRecord('certificados', {
      id_agente:                    idAgente,
      fecha_inasistencia_justifica: fechaDB,
      observaciones:                observaciones,
      fecha_carga:                  fechaCargaISO
    }, ['id_agente', 'fecha_inasistencia_justifica']);

    if (res.success) {
      Logger.log('✅ Certificado: ' + nombreForm + ' - ' + fechaDB);
    } else {
      Logger.log('❌ Supabase certificados: ' + res.error);
      _alertar_('Error al registrar certificado', res.error);
    }
  } catch(err) {
    Logger.log('❌ Excepción onSubmitCertificado: ' + err.message);
    if (typeof _alertar_ === 'function') {
        _alertar_('Excepción sync certificados', err.message);
    }
  }
}

// ============================================================
// INSTALADORES DE TRIGGER (ejecutar UNA SOLA VEZ por sheet)
// ============================================================
function instalarTriggerCertificados() {
  ScriptApp.newTrigger('onSubmitCertificado')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit().create();
  Logger.log('✅ Trigger Certificados instalado.');
}

// ============================================================
// SYNC MASIVO DEL BACKLOG HISTÓRICO
// ============================================================
function syncMasivoCertificados() {
  if (typeof _syncMasivo_ === 'function') {
      _syncMasivo_(onSubmitCertificado, 'Certificados');
  } else {
      SpreadsheetApp.getUi().alert('❌ Error: _syncMasivo_ no encontrado. Asegúrate de incluir sync_formularios.gs');
  }
}
