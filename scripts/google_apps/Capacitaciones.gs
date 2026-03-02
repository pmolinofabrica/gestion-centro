/**
 * Módulo de Capacitaciones (Backend)
 * Gestiona la sincronización con Supabase y la UI de Sheets para Capacitaciones.
 * Dependencias: db_helpers.gs
 */

// CONSTANTES DINÁMICAS
const SCRIPT_PROP_ANIO = "CAPACITACIONES_ANIO_ACTIVO";

function getAnioContexto() {
  const props = PropertiesService.getScriptProperties();
  const stored = props.getProperty(SCRIPT_PROP_ANIO);
  return stored ? parseInt(stored) : new Date().getFullYear();
}

function setAnioContexto(anio) {
  PropertiesService.getScriptProperties().setProperty(SCRIPT_PROP_ANIO, String(anio));
}

function getHojaMaestro(anio) { return `capacitaciones ${anio}`; }
function getHojaMatrizDisp(anio) { return `cap_disp ${anio}`; }
function getHojaMatrizRes(anio) { return `cap_residentes ${anio}`; }

function getHojaVista(anio) { return `vista_capacitados ${anio}`; }
function getHojaDispositivos(anio) { return `dispositivos ${anio}`; }

/**
 * Menú contextual
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  const anio = getAnioContexto();
  ui.createMenu(`Capacitaciones ${anio}`)
    .addItem('1. Sincronizar Maestro', 'sincronizarConPlanificacion')
    .addSeparator()
    .addItem('2. Actualizar Matriz Dispositivos', 'renderizarMatrizDispositivos')
    .addItem('3. Guardar Matriz Dispositivos', 'saveMatrizDispositivos')
    .addSeparator()
    .addItem('4. Actualizar Matriz Residentes', 'renderizarMatrizResidentes')
    .addItem('5. Guardar Matriz Residentes', 'saveMatrizResidentes')
    .addItem('6. Vista Planificación (Historial)', 'renderizarMatrizCertificaciones')
    .addItem('7. Vista Operativa (Habilidades Hoy)', 'renderizarVistaOperativa')
    .addSeparator()
    .addItem('8. Actualizar Lista Dispositivos', 'renderizarListaDispositivos')
    .addItem('9. Guardar Lista Dispositivos', 'saveListaDispositivos')
    .addSeparator()
    .addSubMenu(ui.createMenu('Admin / Avanzado')
        .addItem('Cambiar Año de Contexto', 'cambiarAnioContexto'))
    .addToUi();
}


// =============================================================================
// ADMIN: CAMBIAR AÑO
// =============================================================================

function cambiarAnioContexto() {
   const ui = SpreadsheetApp.getUi();
   const current = getAnioContexto();
   const prompt = ui.prompt('Cambiar Año de Contexto', `Año actual: ${current}\n\nIngrese el nuevo año (ej. 2026) para cambiar de espacio de trabajo.\nEsto actualizará todas las pestañas al año seleccionado.`, ui.ButtonSet.OK_CANCEL);
   
   if (prompt.getSelectedButton() !== ui.Button.OK) return;
   
   const input = prompt.getResponseText().trim();
   const nuevoAnio = parseInt(input);
   
   if (!nuevoAnio || isNaN(nuevoAnio)) {
       ui.alert('Año inválido');
       return;
   }

   setAnioContexto(nuevoAnio);
   
   // Actualizar automáticamente todas las pestañas para el nuevo año
   try {
     sincronizarConPlanificacion();
     renderizarMatrizDispositivos();
     renderizarMatrizResidentes();
     renderizarMatrizCertificaciones();
     renderizarListaDispositivos();
     ui.alert(`✅ Contexto cambiado al año ${nuevoAnio}.\n\nSe han generado/actualizado las 5 pestañas correspondientes.`);
   } catch (e) {
     ui.alert(`⚠️ Contexto cambiado a ${nuevoAnio}, pero hubo error actualizando hojas: ${e.message}`);
   }
}

// =============================================================================
// SINCRONIZACIÓN MAESTRO
// =============================================================================

function sincronizarConPlanificacion() {
  const ui = SpreadsheetApp.getUi();
  const anio = getAnioContexto();
  
  // Confirmación simple (el año ya está seleccionado por contexto)
  /* Opcional: Confirmar si el usuario quiere realmente sobreescribir */
  /* const resp = ui.alert(`¿Sincronizar año ${anio}?`, ui.ButtonSet.YES_NO);
     if (resp !== ui.Button.YES) return; */

  const sheet = getOrCreateSheet_(getHojaMaestro(anio));
  
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
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaMatrizDisp(anio));
  sheet.clear(); 

  const sheetMaestro = getOrCreateSheet_(getHojaMaestro(anio));
  const datosMaestro = sheetMaestro.getDataRange().getValues();
  if (datosMaestro.length <= 1) {
    SpreadsheetApp.getUi().alert('Primero debe sincronizar el Maestro de Capacitaciones.');
    return;
  }
  
  // Capacitaciones
  const capacitaciones = datosMaestro.slice(1).map(r => {
    let fechaStr = r[1];
    if (r[1] instanceof Date) {
        const d = r[1];
        fechaStr = `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getFullYear()).slice(-2)}`;
    }
    return { id: r[0], fecha: fechaStr, grupo: r[3], tema: r[4] };
  });

  // Dispositivos y Ordenamiento
  const todosDispositivos = fetchAll('dispositivos', 'id_dispositivo, nombre_dispositivo, piso_dispositivo, activo');
  const dispositivos = todosDispositivos.filter(d => d.activo === true || d.activo === 1);
  
  if (dispositivos.length === 0) {
      SpreadsheetApp.getUi().alert('No hay dispositivos activos.');
      return;
  }

  // Ordenar: Piso ASC, luego Nombre ASC
  dispositivos.sort((a, b) => {
      const pisoA = a.piso_dispositivo || 999;
      const pisoB = b.piso_dispositivo || 999;
      if (pisoA !== pisoB) return pisoA - pisoB;
      return a.nombre_dispositivo.localeCompare(b.nombre_dispositivo);
  });
  
  // Tiempos existentes
  const relaciones = fetchAll('capacitaciones_dispositivos', 'id_cap, id_dispositivo, tiempo_minutos');
  const mapRelaciones = new Map();
  relaciones.forEach(r => {
      mapRelaciones.set(`${r.id_cap}-${r.id_dispositivo}`, r.tiempo_minutos || 0); 
  });

  // Headers
  const headers = ["ID_Cap", "Fecha", "Grupo", "Tema"];
  const colIds = [];
  const headerColors = ["#cfe2f3", "#cfe2f3", "#cfe2f3", "#cfe2f3"]; // Default colors for first four cols

  dispositivos.forEach(d => {
      const nombre = d.nombre_dispositivo.length > 20 ? d.nombre_dispositivo.substring(0,20) + '…' : d.nombre_dispositivo;
      headers.push(nombre);
      colIds.push(d.id_dispositivo);
      
      // Color coding logic
      let color = "#ffffff";
      switch (d.piso_dispositivo) {
          case 1: color = "#fff2cc"; break; // Amarillo
          case 2: color = "#ea9999"; break; // Rojo
          case 3: color = "#a4c2f4"; break; // Azul
          case 4: color = "#b6d7a8"; break; // Verde
          default: color = "#eeeeee";
      }
      headerColors.push(color);
  });
  
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers])
       .setFontWeight("bold")
       .setWrap(true);
  
  // Aplicar colores de fondo
  headerRange.setBackgrounds([headerColors]);

  // Guardar metadata en nota
  sheet.getRange("A1").setNote(JSON.stringify(colIds));

  const outputGrid = [];
  capacitaciones.forEach((cap) => {
      const row = [cap.id, cap.fecha, cap.grupo || "-", cap.tema || ""];
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
      const inputRange = sheet.getRange(startRow, 5, outputGrid.length, dispositivos.length);
      const rule = SpreadsheetApp.newDataValidation()
        .requireNumberGreaterThanOrEqualTo(0)
        .setAllowInvalid(true)
        .setHelpText('Ingrese minutos (0 = no asignado)')
        .build();
      inputRange.setDataValidation(rule);
      inputRange.setBackground("#fff9c4"); 
  }
  
  sheet.setFrozenColumns(4);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 4);
  SpreadsheetApp.getUi().alert('Matriz generada. Dispositivos ordenados por ubicación.');
}

function saveMatrizDispositivos() {
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaMatrizDisp(anio));
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
          const val = row[4 + j]; 
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
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaMatrizRes(anio));
  sheet.clear(); 

  const sheetMaestro = getOrCreateSheet_(getHojaMaestro(anio));
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
    return { id: r[0], fecha: fechaStr, grupo: r[3], tema: r[4] };
  });

  // Residentes activos - Columna cohorte (no anio_residencia)
  const todosAgentes = fetchAll('datos_personales', 'id_agente, nombre, apellido, cohorte, activo');
  Logger.log('DEBUG - Total agentes tabla: ' + todosAgentes.length);
  
  // Filtrar por ACTIVO y por AÑO (COHORTE)
  // El usuario solicitó ver solo los del año seleccionado
  const agentes = todosAgentes.filter(a => {
      const p1 = (a.activo === true || a.activo === 1 || a.activo === 't');
      const p2 = (a.cohorte === anio);
      return p1 && p2;
  });
  Logger.log('DEBUG - Agentes filtrados (Activos + Cohorte ' + anio + '): ' + agentes.length);
  
  if (agentes.length === 0) {
      SpreadsheetApp.getUi().alert('No hay residentes activos. Total en tabla: ' + todosAgentes.length + '. Revisar logs.');
      return;
  }
  
  // Ordenar por apellido
  agentes.sort((a, b) => a.apellido.localeCompare(b.apellido));
  
  // Asignaciones persistidas y sugeridas por convocatoria
  const resultRPC = callRpc('rpc_obtener_convocados_matriz', { anio_filtro: anio });
  
  if (!resultRPC.success) {
      SpreadsheetApp.getUi().alert('Error obteniendo convocados: ' + resultRPC.error);
      return;
  }
  
  const mapAsignaciones = new Map();
  const datosConvocados = resultRPC.data || [];
  datosConvocados.forEach(r => {
      mapAsignaciones.set(`${r.id_cap}-${r.id_agente}`, true); 
  });

  // Headers
  const headers = ["ID_Cap", "Fecha", "Grupo", "Tema"];
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
      const row = [cap.id, cap.fecha, cap.grupo || "-", cap.tema || ""];
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
      sheet.getRange(startRow, 5, outputGrid.length, agentes.length).insertCheckboxes();
  }
  
  sheet.setFrozenColumns(4);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 4);
  SpreadsheetApp.getUi().alert('Matriz residentes generada. Marque checkboxes para asignar.');
}

function saveMatrizResidentes() {
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaMatrizRes(anio));
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
          const isChecked = row[4 + j]; 
          
          let asistioCheck = false;
          if (isChecked === true || isChecked === 1) {
              asistioCheck = true;
          } else if (typeof isChecked === 'string') {
              const s = isChecked.trim().toUpperCase();
              if (s === 'TRUE' || s === 'VERDADERO' || s === 'V' || s === 'SÍ' || s === 'SI' || s === 'YES') {
                  asistioCheck = true;
              }
          }
          
          participantes.push({
              "id_agente": colIds[j],
              "asistio": asistioCheck
          });
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

// =============================================================================
// VISTAS Y REPORTES
// =============================================================================

function renderizarMatrizCertificaciones() {
  // Alias: Vista Planificación / Histórica
  renderizarVistaGeneral(false);
}

function renderizarVistaOperativa() {
  // Vista Operativa (Solo Hoy + Asistió)
  renderizarVistaGeneral(true);
}

/**
 * Renderiza vista de capacitaciones.
 * @param {boolean} esOperativa - Si true, usa rpc_obtener_matriz_habilidades_hoy y formato operativo.
 */
function renderizarVistaGeneral(esOperativa) {
  const anio = getAnioContexto();
  // Nombres de hojas distintos
  const nombreHoja = esOperativa ? `vista_operativa ${anio}` : getHojaVista(anio);
  
  const sheet = getOrCreateSheet_(nombreHoja);
  sheet.clear();
  
  // Seleccionar RPC y Título
  const rpcName = esOperativa ? 'rpc_obtener_matriz_habilidades_hoy' : 'rpc_obtener_matriz_certificaciones';
  const tituloMock = esOperativa ? 'VISTA OPERATIVA (HABILIDADES AL DÍA)' : 'VISTA GENERAL (HISTORIAL COMPLETADO)';
  const colorBg = esOperativa ? '#d9ead3' : '#f4cccc'; // Verde vs Rojo suave
  
  // Llamada RPC
  const resultRPC = callRpc(rpcName, { anio_filtro: anio });
  
  if (!resultRPC.success) {
       SpreadsheetApp.getUi().alert('Error obteniendo datos: ' + resultRPC.error);
       Logger.log(resultRPC.error);
       return;
  }
  
  const datos = resultRPC.data || [];
  if (datos.length === 0) {
      SpreadsheetApp.getUi().alert(`No hay datos para la vista ${esOperativa ? 'Operativa' : 'General'}.`);
      return;
  }
  
  Logger.log(`Registros encontrados (${esOperativa ? 'Operativa' : 'General'}): ${datos.length}`);
  
  // Procesar datos para matriz (Pivoting)
  const dispositivos = [...new Map(datos.map(c => [c.id_dispositivo, {id: c.id_dispositivo, nombre: c.nombre_dispositivo}])).values()];
  const residentes = [...new Map(datos.map(c => [c.id_agente, {id: c.id_agente, nombre: c.nombre_completo}])).values()];
  
  // Ordenar
  dispositivos.sort((a, b) => a.nombre.localeCompare(b.nombre));
  residentes.sort((a, b) => a.nombre.localeCompare(b.nombre));
  
  const mapCert = new Map();
  datos.forEach(c => mapCert.set(`${c.id_dispositivo}-${c.id_agente}`, c.fecha_mas_reciente));
  
  // Headers
  const headers = ["Dispositivo", ...residentes.map(r => r.nombre.substring(0,12))];
  
  // Render Headers
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
       .setFontWeight("bold")
       .setBackground(colorBg)
       .setWrap(true)
       .setVerticalAlignment("bottom");
       
  // Nota Informativa
  sheet.getRange("A1").setNote(`${tituloMock}\nGenerado: ${new Date().toLocaleString()}`);
  
  // Grid
  const outputGrid = [];
  dispositivos.forEach(disp => {
      const row = [disp.nombre];
      residentes.forEach(res => {
          const fecha = mapCert.get(`${disp.id}-${res.id}`);
          if (fecha) {
              const partes = String(fecha).split('T')[0].split('-');
              let fechaStr = fecha;
              if (partes.length === 3) {
                  fechaStr = `${partes[2]}/${partes[1]}/${partes[0].slice(-2)}`;
              }
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
      dataRange.setHorizontalAlignment("center");
      
      // Banding
      for (let i = 0; i < outputGrid.length; i++) {
          const rowRange = sheet.getRange(2 + i, 1, 1, outputGrid[0].length);
          rowRange.setBackground(i % 2 === 0 ? "#ffffff" : "#f9f9f9");
      }
  }
  
  sheet.setFrozenColumns(1);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumn(1);
  
  SpreadsheetApp.getUi().alert(`${tituloMock} generada con ${datos.length} registros.`);
}

// =============================================================================
// GESTIÓN DE DISPOSITIVOS (CRUD)
// =============================================================================

function renderizarListaDispositivos() {
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaDispositivos(anio));
  
  // Limpiar pero mantener headers si existen? Mejor repintar todo para consistencia
  sheet.clear();
  
  // Columns: id, nombre, piso, activo, critico, min, opt
  const datos = fetchAll('dispositivos', 'id_dispositivo, nombre_dispositivo, piso_dispositivo, activo, es_critico, cupo_minimo, cupo_optimo');
  
  // Headers
  const headers = ["ID (No editar)", "Nombre Dispositivo", "Piso / Ubicación", "Activo", "Es Crítico", "Cupo Mín", "Cupo Ópt"];
  
  sheet.getRange(1, 1, 1, headers.length)
       .setValues([headers])
       .setFontWeight("bold")
       .setBackground("#d0e0e3"); // Celeste
       
  if (datos && datos.length > 0) {
      // Ordenar por Piso ASC, luego Nombre ASC
      datos.sort((a, b) => {
          const pisoA = a.piso_dispositivo || 999;
          const pisoB = b.piso_dispositivo || 999;
          if (pisoA !== pisoB) return pisoA - pisoB;
          return a.nombre_dispositivo.localeCompare(b.nombre_dispositivo);
      });
      
      const rows = datos.map(d => [
          d.id_dispositivo, 
          d.nombre_dispositivo, 
          d.piso_dispositivo || "",
          d.activo,
          d.es_critico,
          d.cupo_minimo || 0,
          d.cupo_optimo || 0
      ]);
      
      const startRow = 2;
      const numRows = rows.length;
      sheet.getRange(startRow, 1, numRows, headers.length).setValues(rows);
      
      // Colorear columna Piso (Indice 2 en rows -> Columna 3 en Sheet)
      const colorColumn = [];
      for(let i=0; i<numRows; i++) {
        const val = rows[i][2]; // piso_dispositivo
        let color = "#ffffff";
        switch(val) {
          case 1: color = "#fff2cc"; break; // Amarillo
          case 2: color = "#ea9999"; break; // Rojo
          case 3: color = "#a4c2f4"; break; // Azul
          case 4: color = "#b6d7a8"; break; // Verde
        }
        colorColumn.push([color]);
      }
      sheet.getRange(startRow, 3, numRows, 1).setBackgrounds(colorColumn);

      // Checkboxes para columna Activo (4) y Es Crítico (5)
      sheet.getRange(startRow, 4, numRows, 1).insertCheckboxes();
      sheet.getRange(startRow, 5, numRows, 1).insertCheckboxes();
  }
  
  sheet.autoResizeColumns(1, headers.length);
  SpreadsheetApp.getUi().alert(`Lista de dispositivos actualizada (${datos.length} registros). Ordenado por piso.`);
}

function saveListaDispositivos() {
  const ui = SpreadsheetApp.getUi();
  const anio = getAnioContexto();
  const sheet = getOrCreateSheet_(getHojaDispositivos(anio));
  
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return;
  
  let created = 0;
  let updated = 0;
  let errors = 0;
  
  // Empezar desde fila 2
  for (let i = 1; i < data.length; i++) {
      const row = data[i];
      // Col indices: 0:ID, 1:Nombre, 2:Piso, 3:Activo, 4:Critico, 5:Min, 6:Opt
      const id = row[0]; 
      const nombre = row[1];
      const piso = row[2];
      const activo = row[3];
      const critico = row[4];
      const min = row[5];
      const opt = row[6];
      
      if (!nombre) continue; // Skip filas vacías
      
      const payload = {
          nombre_dispositivo: nombre,
          piso_dispositivo: piso ? String(piso) : null,
          activo: activo === true || activo === 1 || activo === 'TRUE',
          es_critico: critico === true || critico === 1 || critico === 'TRUE',
          cupo_minimo: min ? parseInt(min) : 0,
          cupo_optimo: opt ? parseInt(opt) : 0
      };
      
      if (id) {
          // UPDATE
          payload.id_dispositivo = id;
          const res = upsertRecord('dispositivos', payload, 'id_dispositivo');
          if (res.success) updated++;
          else {
              errors++;
              Logger.log(`Error updating id ${id}: ${res.error}`);
          }
      } else {
          // CREATE
          const res = insertRow('dispositivos', payload);
          if (res.success) created++;
          else {
               errors++;
               Logger.log(`Error creating ${nombre}: ${res.error}`);
          }
      }
  }
  
  ui.alert(`Sincronización finalizada:\n\n🆕 Creados: ${created}\n🔄 Actualizados: ${updated}\n❌ Errores: ${errors}`);
  
  // Refrescar
  if (created > 0) {
      renderizarListaDispositivos();
  }
}


