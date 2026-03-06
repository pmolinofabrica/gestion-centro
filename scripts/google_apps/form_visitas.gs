/**
 * form_visitas.gs
 * ============================================================
 * Integración automática: Google Forms (Visitas) → Supabase
 * Tabla: solicitudes
 *
 * Depende de: db_helpers.gs (getSupabaseConfig_, buildHeaders_,
 *             insertRow)
 *
 * INSTALACIÓN:
 *   1. Abrir el Google Sheet del formulario → Extensiones → Apps Script
 *   2. Pegar este código junto a db_helpers.gs
 *   3. Correr la función `instalarTriggerSolicitudes()`
 *   4. Autorizar permisos
 * ============================================================
 */

/**
 * TRIGGER: SOLICITUDES DE VISITA
 * Mapeo de 24 columnas según el XLSX "Turnero 2025"
 */
function onSubmitSolicitud(e) {
  try {
    var row = e.values;
    if (!row || row.length < 24) {
      Logger.log('⚠️ onSubmitSolicitud: Fila incompleta o inválida');
      return;
    }

    // Mapeo exacto según el esquema aprobado
    var payload = {
      marca_temporal:               formatTimestamp_(row[0]), // Asegura formato ISO para Postgres
      direccion_email:              row[1],
      tipo_institucion:             row[2],
      nombre_institucion:           row[3],
      provincia:                    row[4],
      departamento:                 row[5],
      agenda_amplia:                row[6],
      quien_coordina:               row[7],
      nombre_coordinador_viaje:     row[8],
      nombre_empresa_organizacion:  row[9],
      telefono_contacto_coordinador:row[10],
      email_contacto_coordinador:   row[11],
      nombre_referente:              row[12],
      cargo_institucion:            row[13],
      telefono_referente:           row[14],
      telefono_institucion:         row[15],
      email_referente:              row[16],
      mes_visita_preferido:         row[17],
      dias_turnos_preferencia:      row[18],
      disponibilidad_llamados:      row[19],
      rango_etario:                 row[20],
      cantidad_visitantes:          parseInt(row[21]) || 0,
      requerimientos_accesibilidad: row[22],
      comentarios_observaciones:    row[23],
      estado_actual:                'Pendiente'
    };

    // Inserción en Supabase
    var res = insertRow('solicitudes', payload);

    if (res.success) {
      Logger.log('✅ Solicitud registrada: ' + payload.nombre_institucion);
    } else {
      Logger.log('❌ Supabase solicitudes: ' + res.error);
      _alertar_('Error en Solicitud Visita', res.error);
    }

  } catch (err) {
    Logger.log('❌ Excepción onSubmitSolicitud: ' + err.message);
    _alertar_('Excepción sync solicitudes', err.message);
  }
}

/**
 * Instalador del trigger
 */
function instalarTriggerSolicitudes() {
  ScriptApp.newTrigger('onSubmitSolicitud')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit().create();
  Logger.log('✅ Trigger Solicitudes instalado.');
}

/**
 * Sincronización masiva del backlog histórico
 */
function syncMasivoSolicitudes() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var data = sheet.getDataRange().getValues();
  var ok = 0, err = 0;
  
  // Empezar en i=1 para saltar encabezados
  for (var i = 1; i < data.length; i++) {
    try {
      // Simular el evento e.values
      onSubmitSolicitud({ values: data[i].map(String) });
      ok++;
    } catch (ex) {
      err++;
      Logger.log('❌ Fila ' + (i + 1) + ': ' + ex.message);
    }
    if (i % 10 === 0) Utilities.sleep(100); // Pequeño respiro
  }
  
  var msg = 'Sync Solicitudes: ' + ok + ' OK, ' + err + ' errores';
  Logger.log(msg);
  SpreadsheetApp.getUi().alert(msg);
}
