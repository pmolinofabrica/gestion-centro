/**
 * Módulo de Capacitaciones (Backend)
 * Gestiona la sincronización con Supabase y la UI de Sheets para Capacitaciones.
 * Dependencias: db_helpers.gs
 */

const HOJA_MAESTRO = "MAESTRO_CAPACITACIONES";
const HOJA_MATRIZ_DISP = "cap_disp";
const HOJA_MATRIZ_RES = "cap_residentes";

/**
 * Menú contextual
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Capacitaciones 2026')
    .addItem('1. Sincronizar Maestro', 'sincronizarConPlanificacion')
    .addSeparator()
    .addItem('2. Actualizar Matriz Dispositivos', 'renderizarMatrizDispositivos')
    .addItem('3. Guardar Matriz Dispositivos', 'saveMatrizDispositivos')
    .addSeparator()
    .addItem('4. Actualizar Matriz Residentes', 'renderizarMatrizResidentes')
    .addItem('5. Guardar Matriz Residentes', 'saveMatrizResidentes')
    .addSeparator()
    .addItem('6. Ver Vista Capacitados (Solo Lectura)', 'renderizarMatrizCertificaciones')
    .addToUi();
}

// =============================================================================
// SINCRONIZACIÓN MAESTRO
// =============================================================================

function sincronizarConPlanificacion() {
  const ui = SpreadsheetApp.getUi();
  
  const currentYear = new Date().getFullYear();
  const prompt = ui.prompt('Sincronizar Capacitaciones', 'Ingrese el año a sincronizar:', ui.ButtonSet.OK_CANCEL);
  
  if (prompt.getSelectedButton() !== ui.Button.OK) return;
  
  const anioInput = prompt.getResponseText().trim();
  const anio = anioInput ? parseInt(anioInput) : currentYear;
  
  if (isNaN(anio)) {
      ui.alert('Año inválido.');
      return;
  }

  const sheet = getOrCreateSheet_(HOJA_MAESTRO);
  
  // Headers
  const headers = ["ID_Cap", "Fecha", "Turno", "Grupo", "Tema", "Observaciones", "Tiempo Total (min)", "Residentes Asignados"];
  
  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).clearContent();
  }
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight("bold").setBackground("#E0E0E0");

  const dias = fetchAllWithFilters('dias', 'id_dia, fecha', { anio: anio });
  
  if (!dias || dias.length === 0) {
      ui.alert(`No se encontraron días registrados para el año ${anio}.`);
      return;
  }
  
  const mapDias = new Map();
  dias.forEach(d => mapDias.set(d.id_dia, d.fecha));
  
  const todasCapacitaciones = fetchAll('capacitaciones', '*');
  
  if (!todasCapacitaciones || todasCapacitaciones.length === 0) {
      ui.alert('No hay capacitaciones registradas en la base de datos.');
      return;
  }

  const turnos = fetchAll('turnos', 'id_turno, tipo_turno');
  const mapTurnos = new Map(turnos.map(t => [t.id_turno, t.tipo_turno]));

  // Tiempos por capacitación
  const tiemposDisp = fetchAll('capacitaciones_dispositivos', 'id_cap, tiempo_minutos');
  const mapTiempos = new Map();
  tiemposDisp.forEach(t => {
      const current = mapTiempos.get(t.id_cap) || 0;
      mapTiempos.set(t.id_cap, current + (t.tiempo_minutos || 0));
  });

  // Residentes por capacitación
  const participantes = fetchAll('capacitaciones_participantes', 'id_cap');
  const mapResidentes = new Map();
  participantes.forEach(p => {
      const current = mapResidentes.get(p.id_cap) || 0;
      mapResidentes.set(p.id_cap, current + 1);
  });

  const filasParaInsertar = [];
  
  todasCapacitaciones.forEach(c => {
       if (mapDias.has(c.id_dia)) {
           const fecha = mapDias.get(c.id_dia);
           const turno = mapTurnos.get(c.id_turno);
           const totalTiempo = mapTiempos.get(c.id_cap) || 0;
           const totalResidentes = mapResidentes.get(c.id_cap) || 0;
           
           filasParaInsertar.push([
             c.id_cap,
             fecha, 
             turno,
             c.grupo || "-", 
             c.tema || "", 
             c.observaciones || "", 
             totalTiempo,
             totalResidentes
           ]);
       }
  });
  
  filasParaInsertar.sort((a, b) => new Date(a[1]) - new Date(b[1]));

  if (filasParaInsertar.length > 0) {
      sheet.getRange(2, 1, filasParaInsertar.length, filasParaInsertar[0].length).setValues(filasParaInsertar);
      ui.alert('Sincronización completada. ' + filasParaInsertar.length + ' capacitaciones cargadas.');
  } else {
      ui.alert('No hay capacitaciones para el año ' + anio);
  }
}

// =============================================================================
// MATRIZ DISPOSITIVOS (cap_disp)
// =============================================================================

function renderizarMatrizDispositivos() {
  const sheet = getOrCreateSheet_(HOJA_MATRIZ_DISP);
  sheet.clear(); 

  const sheetMaestro = getOrCreateSheet_(HOJA_MAESTRO);
  const datosMaestro = sheetMaestro.getDataRange().getValues();
  if (datosMaestro.length <= 1) {
    SpreadsheetApp.getUi().alert('Primero debe sincronizar el Maestro de Capacitaciones.');
    return;
  }
  
  // Capacitaciones con formato fecha DD/MM/AA
  const capacitaciones = datosMaestro.slice(1).map(r => {
    let fechaStr = r[1];
    if (r[1] instanceof Date) {
        const d = r[1];
        fechaStr = `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getFullYear()).slice(-2)}`;
    }
    return { id: r[0], label: `${fechaStr} - ${r[4]} (G:${r[3]})` };
  });

  // Dispositivos
  const todosDispositivos = fetchAll('dispositivos', 'id_dispositivo, nombre_dispositivo, activo');
  const dispositivos = todosDispositivos.filter(d => d.activo === true || d.activo === 1);
  
  if (dispositivos.length === 0) {
      SpreadsheetApp.getUi().alert('No hay dispositivos activos.');
      return;
  }
  
  // Tiempos existentes
  const relaciones = fetchAll('capacitaciones_dispositivos', 'id_cap, id_dispositivo, tiempo_minutos');
  const mapRelaciones = new Map();
  relaciones.forEach(r => {
      mapRelaciones.set(`${r.id_cap}-${r.id_dispositivo}`, r.tiempo_minutos || 0); 
  });

  // Headers: ID_Cap, Capacitacion, luego por cada dispositivo: [NOMBRE_CORTO]
  // El usuario ingresa tiempo directamente. Si hay tiempo > 0, está asignado.
  const headers = ["ID_Cap", "Capacitación"];
  const colIds = [];
  dispositivos.forEach(d => {
      // Nombre corto (primeras 15 chars)
      const nombre = d.nombre_dispositivo.length > 15 ? d.nombre_dispositivo.substring(0,15) + '…' : d.nombre_dispositivo;
      headers.push(nombre);
      colIds.push(d.id_dispositivo);
  });
  
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
       .setFontWeight("bold")
       .setBackground("#cfe2f3")
       .setWrap(true);

  // Guardar metadata en nota
  sheet.getRange("A1").setNote(JSON.stringify(colIds));

  const outputGrid = [];
  capacitaciones.forEach((cap) => {
      const row = [cap.id, cap.label];
      dispositivos.forEach(disp => {
          const tiempo = mapRelaciones.get(`${cap.id}-${disp.id_dispositivo}`);
          row.push(tiempo > 0 ? tiempo : "");
      });
      outputGrid.push(row);
  });

  if (outputGrid.length > 0) {
      const startRow = 2;
      sheet.getRange(startRow, 1, outputGrid.length, outputGrid[0].length).setValues(outputGrid);
      
      // Validación numérica
      const inputRange = sheet.getRange(startRow, 3, outputGrid.length, dispositivos.length);
      const rule = SpreadsheetApp.newDataValidation()
        .requireNumberGreaterThanOrEqualTo(0)
        .setAllowInvalid(true)
        .setHelpText('Ingrese minutos (0 = no asignado)')
        .build();
      inputRange.setDataValidation(rule);
      inputRange.setBackground("#fff9c4"); // Amarillo claro para indicar zona editable
  }
  
  sheet.setFrozenColumns(2);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 2);
  SpreadsheetApp.getUi().alert('Matriz generada. Ingrese minutos en las celdas amarillas.');
}

function saveMatrizDispositivos() {
  const sheet = getOrCreateSheet_(HOJA_MATRIZ_DISP);
  const data = sheet.getDataRange().getValues();
  
  if (data.length < 2) return; 

  const note = sheet.getRange("A1").getNote();
  if (!note) {
      SpreadsheetApp.getUi().alert('Error: No se encuentran metadatos.');
      return;
  }
  const colIds = JSON.parse(note);
  
  const payload = [];
  
  for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const idCap = row[0];
      
      for (let j = 0; j < colIds.length; j++) {
          const val = row[2 + j]; 
          const idDisp = colIds[j];
          let tiempo = 0;
          
          if (typeof val === 'number') {
              tiempo = Math.floor(val);
          } else if (val && !isNaN(val)) {
              tiempo = parseInt(val);
          }
          
          payload.push({
              "id_cap": idCap,
              "id_dispositivo": idDisp,
              "tiempo": tiempo 
          });
      }
  }
  
  const result = callRpc('rpc_guardar_matriz_dispositivos', { payload: payload });
  
  if (result.success && result.data && result.data.success) {
      SpreadsheetApp.getUi().alert('Guardado OK: ' + result.data.message);
  } else {
      SpreadsheetApp.getUi().alert('Error: ' + JSON.stringify(result));
  }
}

// =============================================================================
// MATRIZ RESIDENTES (cap_residentes)
// =============================================================================

function renderizarMatrizResidentes() {
  const sheet = getOrCreateSheet_(HOJA_MATRIZ_RES);
  sheet.clear(); 

  const sheetMaestro = getOrCreateSheet_(HOJA_MAESTRO);
  const datosMaestro = sheetMaestro.getDataRange().getValues();
  if (datosMaestro.length <= 1) {
    SpreadsheetApp.getUi().alert('Primero debe sincronizar el Maestro.');
    return;
  }
  
  // Capacitaciones
  const capacitaciones = datosMaestro.slice(1).map(r => {
    let fechaStr = r[1];
    if (r[1] instanceof Date) {
        const d = r[1];
        fechaStr = `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getFullYear()).slice(-2)}`;
    }
    return { id: r[0], label: `${fechaStr} - G:${r[3]}`, grupo: r[3] };
  });

  // Residentes activos - Columna cohorte (no anio_residencia)
  const todosAgentes = fetchAll('datos_personales', 'id_agente, nombre, apellido, cohorte, activo');
  Logger.log('DEBUG - Total agentes tabla: ' + todosAgentes.length);
  
  const agentes = todosAgentes.filter(a => a.activo === true || a.activo === 1 || a.activo === 't');
  Logger.log('DEBUG - Agentes activos filtrados: ' + agentes.length);
  
  if (agentes.length === 0) {
      SpreadsheetApp.getUi().alert('No hay residentes activos. Total en tabla: ' + todosAgentes.length + '. Revisar logs.');
      return;
  }
  
  // Ordenar por apellido
  agentes.sort((a, b) => a.apellido.localeCompare(b.apellido));
  
  // Asignaciones existentes
  const asignaciones = fetchAll('capacitaciones_participantes', 'id_cap, id_agente, asistio');
  const mapAsignaciones = new Map();
  asignaciones.forEach(r => {
      mapAsignaciones.set(`${r.id_cap}-${r.id_agente}`, r.asistio === true || r.asistio === 1 ? 'S' : 'N'); 
  });

  // Headers
  const headers = ["ID_Cap", "Capacitación"];
  const colIds = [];
  agentes.forEach(a => {
      // Apellido + inicial + cohorte
      const nombre = `${a.apellido.substring(0,10)}, ${a.nombre.charAt(0)}. (${a.cohorte || ''})`;
      headers.push(nombre);
      colIds.push(a.id_agente);
  });
  
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
       .setFontWeight("bold")
       .setBackground("#d9ead3")
       .setWrap(true)
       .setVerticalAlignment("bottom");

  sheet.getRange("A1").setNote(JSON.stringify(colIds));

  const outputGrid = [];
  capacitaciones.forEach((cap) => {
      const row = [cap.id, cap.label];
      agentes.forEach(ag => {
          const asignado = mapAsignaciones.has(`${cap.id}-${ag.id_agente}`);
          row.push(asignado); // Checkbox true/false
      });
      outputGrid.push(row);
  });

  if (outputGrid.length > 0) {
      const startRow = 2;
      sheet.getRange(startRow, 1, outputGrid.length, outputGrid[0].length).setValues(outputGrid);
      
      // Insertar checkboxes
      sheet.getRange(startRow, 3, outputGrid.length, agentes.length).insertCheckboxes();
  }
  
  sheet.setFrozenColumns(2);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 2);
  SpreadsheetApp.getUi().alert('Matriz residentes generada. Marque checkboxes para asignar.');
}

function saveMatrizResidentes() {
  const sheet = getOrCreateSheet_(HOJA_MATRIZ_RES);
  const data = sheet.getDataRange().getValues();
  
  if (data.length < 2) return; 

  const note = sheet.getRange("A1").getNote();
  if (!note) {
      SpreadsheetApp.getUi().alert('Error: No se encuentran metadatos.');
      return;
  }
  const colIds = JSON.parse(note);
  
  // Agrupar por id_cap
  const porCapacitacion = new Map();
  
  for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const idCap = row[0];
      const participantes = [];
      
      for (let j = 0; j < colIds.length; j++) {
          const isChecked = row[2 + j]; 
          if (isChecked === true) {
              participantes.push(colIds[j]);
          }
      }
      porCapacitacion.set(idCap, participantes);
  }
  
  // Llamar RPC por cada capacitación
  let errores = 0;
  let exitos = 0;
  
  porCapacitacion.forEach((participantes, idCap) => {
      // IMPORTANTE: La función SQL espera un parámetro "payload" de tipo JSONB
      const result = callRpc('rpc_guardar_participantes_grupo', {
          payload: {
              id_cap: idCap,
              grupo: 'A',
              participantes: participantes
          }
      });
      if (result.success && result.data && result.data.success) {
          exitos++;
      } else {
          errores++;
          Logger.log('Error en cap ' + idCap + ': ' + JSON.stringify(result));
      }
  });
  
  SpreadsheetApp.getUi().alert(`Guardado: ${exitos} capacitaciones OK, ${errores} con error.`);
}

// =============================================================================
// MATRIZ DE CERTIFICACIONES (Solo Lectura)
// =============================================================================

function renderizarMatrizCertificaciones() {
  const HOJA_CERT = "vista_capacitados";
  const sheet = getOrCreateSheet_(HOJA_CERT);
  sheet.clear();
  
  // Usar RPC Security Definer para evitar problemas de permisos con tablas unidas (como 'dias')
  const resultRPC = callRpc('rpc_obtener_vista_capacitados', {});
  
  if (!resultRPC.success) {
       SpreadsheetApp.getUi().alert('Error obteniendo vista: ' + resultRPC.error);
       Logger.log(resultRPC.error);
       return;
  }
  
  const certificaciones = resultRPC.data;
  Logger.log('Registros encontrados: ' + (certificaciones ? certificaciones.length : 0));
  
  if (!certificaciones || certificaciones.length === 0) {
      SpreadsheetApp.getUi().alert('No hay certificaciones registradas. Asegúrate de haber ejecutado el script CORREGIR_VISTA_CAPACITADOS.sql');
      return;
  }
  
  // Obtener listas únicas de dispositivos y residentes
  const dispositivos = [...new Map(certificaciones.map(c => [c.id_dispositivo, {id: c.id_dispositivo, nombre: c.nombre_dispositivo}])).values()];
  const residentes = [...new Map(certificaciones.map(c => [c.id_agente, {id: c.id_agente, nombre: c.nombre_completo}])).values()];
  
  // Ordenar
  dispositivos.sort((a, b) => a.nombre.localeCompare(b.nombre));
  residentes.sort((a, b) => a.nombre.localeCompare(b.nombre));
  
  // Crear mapa de certificaciones con fechas
  const mapCert = new Map();
  certificaciones.forEach(c => {
      if (c.asistio === true || c.asistio === 1) {
          const key = `${c.id_dispositivo}-${c.id_agente}`;
          // Si hay múltiples capacitaciones, guardar la más reciente
          const fechaActual = mapCert.get(key);
          if (!fechaActual || new Date(c.fecha_capacitacion) > new Date(fechaActual)) {
              mapCert.set(key, c.fecha_capacitacion);
          }
      }
  });
  
  // Headers
  const headers = ["Dispositivo", ...residentes.map(r => {
      const partes = r.nombre.split(' ');
      return partes.length > 1 ? `${partes[partes.length-1]}, ${partes[0].charAt(0)}.` : r.nombre.substring(0,12);
  })];
  
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
       .setFontWeight("bold")
       .setBackground("#f4cccc")
       .setWrap(true)
       .setVerticalAlignment("bottom");
  
  // Datos
  const outputGrid = [];
  dispositivos.forEach(disp => {
      const row = [disp.nombre];
      residentes.forEach(res => {
          const fecha = mapCert.get(`${disp.id}-${res.id}`);
          if (fecha) {
              // Formatear fecha como DD/MM/AA
              const d = new Date(fecha);
              const fechaStr = `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getFullYear()).slice(-2)}`;
              row.push(fechaStr);
          } else {
              row.push("");
          }
      });
      outputGrid.push(row);
  });
  
  if (outputGrid.length > 0) {
      const dataRange = sheet.getRange(2, 1, outputGrid.length, outputGrid[0].length);
      dataRange.setValues(outputGrid);
      
      // Formatear checkmarks
      dataRange.setHorizontalAlignment("center");
      
      // Colorear filas alternadas
      for (let i = 0; i < outputGrid.length; i++) {
          const rowRange = sheet.getRange(2 + i, 1, 1, outputGrid[0].length);
          rowRange.setBackground(i % 2 === 0 ? "#ffffff" : "#f9f9f9");
      }
  }
  
  sheet.setFrozenColumns(1);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumn(1);
  
  // Proteger hoja (solo lectura)
  const protection = sheet.protect().setDescription('Vista de capacitados - Solo lectura');
  protection.setWarningOnly(true);
  
  SpreadsheetApp.getUi().alert(`Vista generada: ${dispositivos.length} dispositivos × ${residentes.length} residentes.\n\nMuestra fechas de capacitación. Hoja SOLO LECTURA.`);
}

// =============================================================================
// UTILIDADES
// =============================================================================

function getOrCreateSheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
