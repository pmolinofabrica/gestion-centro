/**
 * DOWNLOAD DATA - Funciones de descarga para hojas de trabajo
 * Permite ver planificación y convocatoria existentes
 * @author Pablo (Data Analyst)
 * @version 1.2.0 - Fixed: planificacion filter, convocatoria fecha from planificacion
 */

// ============================================================================
// MÓDULO: DESCARGA DE PLANIFICACION
// ============================================================================

/**
 * Descarga planificación SIN filtrar por año (trae TODO)
 * Luego el usuario puede filtrar en Sheets si lo desea
 */
/**
 * Descarga planificación SIN filtrar por año (trae TODO)
 * Luego el usuario puede filtrar en Sheets si lo desea
 */
function downloadPlanificacion() {
  // Traer planificación completa
  const data = fetchAll('planificacion', 'id_plani,id_dia,id_turno,cant_residentes_plan,cant_visit,hora_inicio,hora_fin,cant_horas,lugar,plani_notas,grupo');
  
  if (!data || data.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️ No hay planificación en Supabase');
    return;
  }
  
  // Cargar mapeos inversos
  const diasMap = fetchAll('dias', 'id_dia,fecha,anio');
  const turnosMap = fetchAll('turnos', 'id_turno,tipo_turno');
  
  const idDiaData = {};
  diasMap.forEach(d => { 
    idDiaData[d.id_dia] = { fecha: d.fecha, anio: d.anio }; 
  });
  
  const idTurnoToTipo = {};
  turnosMap.forEach(t => { idTurnoToTipo[t.id_turno] = t.tipo_turno; });
  
  // Obtener filtro de año si existe
  const filters = getActiveFilters();
  const añoFiltro = filters.año_activo;
  
  // Filtrar datos si hay año configurado
  let filteredData = data;
  if (añoFiltro) {
    filteredData = data.filter(r => {
      const diaInfo = idDiaData[r.id_dia];
      return diaInfo && diaInfo.anio == añoFiltro;
    });
  }
  
  const sheet = getOrCreateSheet_('PLANIFICACION');
  const headers = ['sincronizar', 'id_plani', 'fecha', 'anio', 'tipo_turno', 'cant_residentes_plan', 
                   'cant_visit', 'hora_inicio', 'hora_fin', 'cant_horas', 'lugar', 'grupo', 'plani_notas', 'sync_status'];
  
  const rows = filteredData.map(r => {
    const diaInfo = idDiaData[r.id_dia] || {};
    return [
      false, // Checkbox inicial (desmarcado)
      r.id_plani,
      diaInfo.fecha || r.id_dia,
      diaInfo.anio || '',
      idTurnoToTipo[r.id_turno] || r.id_turno,
      r.cant_residentes_plan,
      r.cant_visit || 0,
      r.hora_inicio || '',
      r.hora_fin || '',
      r.cant_horas || '',
      r.lugar || '',
      r.grupo || '',
      r.plani_notas || '',
      '✅' // sync_status default OK en descarga
    ];
  });
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#fbbc04')
    .setFontColor('#ffffff');
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    
    // Agregar validación Checkbox a la columna 1
    const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
    const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
    checkboxRange.setDataValidation(rule);
  }
  
  sheet.setFrozenRows(1);
  
  Logger.log('✅ PLANIFICACION descargada: ' + rows.length + ' registros');
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' planificaciones descargadas');
}

// ============================================================================
// MÓDULO: DESCARGA DE CONVOCATORIA (MEJORADO)
// ============================================================================

/**
 * Descarga convocatoria con fecha REAL desde planificacion→dias
 * NO usa fecha_convocatoria directamente, sino la fecha del turno planificado
 */
function downloadConvocatoria() {
  const filters = getActiveFilters();
  const añoFiltro = filters.año_activo;
  
  // Traer toda la data necesaria
  const convData = fetchAll('convocatoria', 'id_convocatoria,id_plani,id_agente,id_turno,estado,motivo_cambio,turno_cancelado');
  
  if (!convData || convData.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️ No hay convocatorias en Supabase');
    return;
  }
  
  // Cargar mapeos
  const planiData = fetchAll('planificacion', 'id_plani,id_dia,id_turno');
  const diasData = fetchAll('dias', 'id_dia,fecha,anio');
  const agentesData = fetchAll('datos_personales', 'id_agente,dni,nombre,apellido');
  const turnosData = fetchAll('turnos', 'id_turno,tipo_turno');
  
  // Crear mapeos
  const planiMap = {};
  planiData.forEach(p => { planiMap[p.id_plani] = { id_dia: p.id_dia, id_turno: p.id_turno }; });
  
  const diasMap = {};
  diasData.forEach(d => { diasMap[d.id_dia] = { fecha: d.fecha, anio: d.anio }; });
  
  const agentesMap = {};
  agentesData.forEach(a => { agentesMap[a.id_agente] = a.apellido + ', ' + a.nombre; });
  
  const turnosMap = {};
  turnosData.forEach(t => { turnosMap[t.id_turno] = t.tipo_turno; });
  
  // Filtrar por año si está configurado
  let filteredData = convData;
  if (añoFiltro) {
    filteredData = convData.filter(c => {
      const plani = planiMap[c.id_plani];
      if (!plani) return false;
      const dia = diasMap[plani.id_dia];
      return dia && dia.anio == añoFiltro;
    });
  }
  
  const sheet = getOrCreateSheet_('CONVOCATORIA');
  const headers = ['sincronizar', 'id_convocatoria', 'agente', 'fecha_turno', 'anio', 'tipo_turno', 
                   'estado', 'turno_cancelado', 'motivo_cambio', 'id_plani', 'sync_status'];
  
  const rows = filteredData.map(c => {
    const plani = planiMap[c.id_plani] || {};
    const dia = diasMap[plani.id_dia] || {};
    return [
      false, // Checkbox
      c.id_convocatoria,
      agentesMap[c.id_agente] || c.id_agente,
      dia.fecha || 'N/A',  // FECHA REAL del turno planificado
      dia.anio || '',
      turnosMap[c.id_turno] || c.id_turno,
      c.estado,
      c.turno_cancelado ? 'Sí' : 'No',
      c.motivo_cambio || '',
      c.id_plani,  // Incluido para referencia
      '✅' // sync_status
    ];
  });
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#ea4335')
    .setFontColor('#ffffff');
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    
    // Agregar validación Checkbox a la columna 1
    const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
    const rule = SpreadsheetApp.newDataValidation().requireCheckbox().build();
    checkboxRange.setDataValidation(rule);
  }
  
  sheet.setFrozenRows(1);
  
  // Aplicar formato condicional para turno_cancelado (resaltar cancelados en rojo)
  // Nota: Ajustamos el índice de columna por el nuevo checkbox (antes 7, ahora 8)
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    const canceladoRange = sheet.getRange(2, 8, lastRow - 1, 1);
    const rule = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Sí')
      .setBackground('#f8d7da')
      .setFontColor('#721c24')
      .setRanges([canceladoRange])
      .build();
    const rules = sheet.getConditionalFormatRules();
    rules.push(rule);
    sheet.setConditionalFormatRules(rules);
  }
  
  Logger.log('✅ CONVOCATORIA descargada: ' + rows.length + ' registros');
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' convocatorias descargadas' + 
                                (añoFiltro ? ' (año ' + añoFiltro + ')' : ' (todos los años)') +
                                '\n\nNota: La columna "fecha_turno" muestra la fecha del turno planificado.');
}

/**
 * Función auxiliar para descargar saldos (si no existe en otro archivo)
 */
function downloadSaldos() {
  const filters = getActiveFilters();
  const año = filters.año_activo;
  
  let query = '?select=*';
  if (año) {
    query += '&anio=eq.' + año;
  }
  
  const result = supabaseRequest_('saldos', query, 'GET');
  
  if (!result.success || !result.data || result.data.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️ No hay saldos' + (año ? ' para el año ' + año : ''));
    return;
  }
  
  // Cargar mapeo de agentes
  const agentesData = fetchAll('datos_personales', 'id_agente,dni,nombre,apellido');
  const agentesMap = {};
  agentesData.forEach(a => { agentesMap[a.id_agente] = a.apellido + ', ' + a.nombre; });
  
  const sheet = getOrCreateSheet_('SALDOS');
  const headers = ['id_saldo', 'agente', 'mes', 'anio', 'horas_asignadas', 'horas_cumplidas', 'saldo', 'sync_status'];
  
  const rows = result.data.map(s => [
    s.id_saldo,
    agentesMap[s.id_agente] || s.id_agente,
    s.mes,
    s.anio,
    s.horas_asignadas || 0,
    s.horas_cumplidas || 0,
    s.saldo || 0,
    ''
  ]);
  
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#673ab7')
    .setFontColor('#ffffff');
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  
  sheet.setFrozenRows(1);
  
  SpreadsheetApp.getUi().alert('✅ ' + rows.length + ' saldos descargados');
}
