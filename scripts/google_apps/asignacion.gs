/**
 * ASIGNACIÓN DE RESIDENTES - Google Apps Script
 * Módulo para gestionar asignaciones de residentes a dispositivos
 * 
 * Basado en Schema Real:
 * - calendario_dispositivos: fecha, id_turno, id_dispositivo, cupo_objetivo
 * - asignaciones: id_agente, id_dispositivo, fecha, id_turno, es_doble_turno, es_capacitacion_servicio
 * - capacitaciones_participantes: id_agente, id_cap, asistio
 * - capacitaciones_dispositivos: id_cap, id_dispositivo
 * - convocatoria: id_agente, fecha_convocatoria, id_turno, estado
 * 
 * CAMBIO v2.1: Capacitación es SOFT CONSTRAINT (Capacitación en Servicio)
 * CAMBIO v2.2: Soporte para CRUD Dispositivos y Carga Matriz de Calendario
 * 
 * @author Pablo (Data Analyst)
 * @version 2.2.0 - Matrix UI & Devices CRUD
 */

// ============================================================================
// OBTENER RESIDENTES DISPONIBLES
// ============================================================================

/**
 * Obtiene TODOS los residentes convocados para una fecha y turno.
 * @param {string} fecha - Fecha en formato 'YYYY-MM-DD'
 * @param {number} idTurno - ID del turno
 * @returns {Object} { dispositivos: [], residentes: [] }
 */
function obtenerDisponibles(fecha, idTurno) {
    try {
        Logger.log('🔍 Buscando disponibles para ' + fecha + ' turno ' + idTurno);

        // 1. Obtener dispositivos del calendario para esa fecha/turno
        const calendario = fetchAllWithFilters('calendario_dispositivos',
            'id_dispositivo, cupo_objetivo', {
            fecha: fecha,
            id_turno: idTurno
        });

        if (calendario.length === 0) {
            Logger.log('⚠️ No hay dispositivos programados para ' + fecha + ' turno ' + idTurno);
            return { dispositivos: [], residentes: [], mensaje: 'No hay dispositivos programados' };
        }

        const idsDispositivos = calendario.map(c => c.id_dispositivo);
        
        // 2. Obtener TODOS los convocados vigentes
        const convocados = fetchAllWithFilters('convocatoria', 'id_agente', {
            fecha_convocatoria: fecha,
            id_turno: idTurno,
            estado: 'vigente'
        });

        if (convocados.length === 0) {
            return { dispositivos: calendario, residentes: [], mensaje: 'No hay residentes convocados' };
        }

        const idsConvocados = convocados.map(c => c.id_agente);
        
        // 3. Obtener capacitados
        const capacitados = obtenerCapacitadosParaDispositivos_(idsDispositivos);

        // 4. Obtener datos personales
        const residentes = [];
        idsConvocados.forEach(idAgente => {
            try {
                const persona = fetchOne('datos_personales', 'id_agente, nombre, apellido, dni', {
                    id_agente: idAgente
                });

                if (persona) {
                    const asignacionesDia = fetchAllWithFilters('asignaciones', 'id', {
                        id_agente: idAgente,
                        fecha: fecha
                    });

                    const estaCapacitado = capacitados.includes(idAgente);

                    residentes.push({
                        id_agente: persona.id_agente,
                        nombre: persona.nombre,
                        apellido: persona.apellido,
                        dni: persona.dni,
                        nombre_completo: persona.apellido + ', ' + persona.nombre,
                        es_doble_turno: asignacionesDia.length > 0,
                        turnos_dia: asignacionesDia.length,
                        esta_capacitado: estaCapacitado,
                        requiere_capacitacion_servicio: !estaCapacitado,
                        icono_alerta: estaCapacitado ? '' : '⚠️ En Servicio'
                    });
                }
            } catch (e) {}
        });

        residentes.sort((a, b) => a.apellido.localeCompare(b.apellido));

        return {
            dispositivos: calendario,
            residentes: residentes,
            mensaje: 'OK'
        };

    } catch (e) {
        Logger.log('❌ Error en obtenerDisponibles: ' + e.message);
        throw e;
    }
}

/**
 * Obtiene IDs de agentes capacitados para una lista de dispositivos
 * @private
 */
function obtenerCapacitadosParaDispositivos_(idsDispositivos) {
    try {
        const capsDispositivo = [];
        idsDispositivos.forEach(idDisp => {
            const caps = fetchAllWithFilters('capacitaciones_dispositivos', 'id_cap', {
                id_dispositivo: idDisp
            });
            caps.forEach(c => {
                if (!capsDispositivo.includes(c.id_cap)) capsDispositivo.push(c.id_cap);
            });
        });

        if (capsDispositivo.length === 0) return [];

        const agentesCapacitados = [];
        capsDispositivo.forEach(idCap => {
            const participantes = fetchAllWithFilters('capacitaciones_participantes', 'id_agente', {
                id_cap: idCap,
                asistio: true
            });
            participantes.forEach(p => {
                if (!agentesCapacitados.includes(p.id_agente)) agentesCapacitados.push(p.id_agente);
            });
        });

        return agentesCapacitados;
    } catch (e) {
        return [];
    }
}

// ============================================================================
// GUARDAR ASIGNACIÓN
// ============================================================================

function guardarAsignacion(idAgente, idDispositivo, fecha, idTurno) {
    try {
        const convocatoria = fetchOne('convocatoria', 'id_convocatoria', {
            id_agente: idAgente,
            fecha_convocatoria: fecha,
            id_turno: idTurno,
            estado: 'vigente'
        });

        if (!convocatoria) {
            return {
                success: false,
                error: '❌ BLOQUEO: El residente no está convocado para esa fecha/turno',
                tipo: 'hard_constraint'
            };
        }

        const capacitados = obtenerCapacitadosParaDispositivos_([idDispositivo]);
        const estaCapacitado = capacitados.includes(idAgente);
        const esCapacitacionServicio = !estaCapacitado;

        const asignacionesPrevias = fetchAllWithFilters('asignaciones', 'id', {
            id_agente: idAgente,
            fecha: fecha
        });
        const esDobleTurno = asignacionesPrevias.length > 0;

        const nuevaAsignacion = {
            id_agente: idAgente,
            id_dispositivo: idDispositivo,
            fecha: fecha,
            id_turno: idTurno,
            es_doble_turno: esDobleTurno,
            es_capacitacion_servicio: esCapacitacionServicio
        };

        const resultado = insertRow('asignaciones', nuevaAsignacion);

        if (resultado.error) {
            return { success: false, error: '❌ Error: ' + resultado.error, tipo: 'database_error' };
        }

        const response = {
            success: true,
            id: resultado.data[0].id,
            es_doble_turno: esDobleTurno,
            es_capacitacion_servicio: esCapacitacionServicio,
            mensaje: '✅ Asignación guardada',
            alertas: []
        };

        if (esDobleTurno) response.alertas.push('⚠️ DOBLE TURNO');
        if (esCapacitacionServicio) response.alertas.push('⚠️ CAPACITACIÓN EN SERVICIO');

        return response;

    } catch (e) {
        return { success: false, error: e.message, tipo: 'exception' };
    }
}

// ============================================================================
// CRUD DISPOSITIVOS (MAESTRO)
// ============================================================================

function downloadDispositivos() {
    const ui = SpreadsheetApp.getUi();
    try {
        // Campos exactos según CSV (excluyendo fecha_creacion)
        const columns = 'id_dispositivo,nombre_dispositivo,piso_dispositivo,activo,es_critico,cupo_minimo,cupo_optimo';
        
        // Fetch data
        const data = fetchAllWithFilters('dispositivos', columns, { activo: true });
        
        const sheet = getOrCreateSheet_('REF_DISPOSITIVOS');
        sheet.clear();
        
        // Headers visuales
        const headers = ['id_dispositivo', 'nombre_dispositivo', 'piso', 'activo', 'es_critico', 'cupo_min', 'cupo_opt', 'sync_status'];
        // Keys del objeto JSON retornado por Supabase
        const keys = ['id_dispositivo', 'nombre_dispositivo', 'piso_dispositivo', 'activo', 'es_critico', 'cupo_minimo', 'cupo_optimo'];
        
        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#E6E6E6');
        
        if (data.length > 0) {
            // Ordenar por ID
            data.sort((a,b) => a.id_dispositivo - b.id_dispositivo);
            
            const rows = data.map(d => {
                return keys.map(k => d[k]); // Map exacto ordenado
            });
            
            // Agregar columna vacía para sync_status
            const finalRows = rows.map(r => [...r, '']);
            
            sheet.getRange(2, 1, finalRows.length, finalRows[0].length).setValues(finalRows);
        }
        
        sheet.autoResizeColumns(1, headers.length);
        ui.alert('✅ ' + data.length + ' dispositivos descargados.');
        
    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}

function uploadDispositivos() {
    const ui = SpreadsheetApp.getUi();
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('REF_DISPOSITIVOS');
    if (!sheet) {
        ui.alert('No existe la hoja REF_DISPOSITIVOS');
        return;
    }
    
    // Asumimos formato simple: Insertar nuevos o Update existentes (UPSERT simplificado)
    // Para simplificar, usamos insertRow. Supabase devolverá error si ID duplicado (salvo que hagamos UPSERT real en helpers)
    // Para DAMA compliance real, deberíamos usar upsertRecord del helper.
    // Usaremos insertRow, si falla es porque ya existe.
    
    const data = sheet.getDataRange().getValues();
    const headers = data[0].map(h => String(h).toLowerCase());
    const results = { ok: 0, err: 0 };
    
    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        if (!row[1]) continue; // Sin nombre
        
        if (row[headers.indexOf('sync_status')] && row[headers.indexOf('sync_status')].toString().includes('✅')) continue; // Ya sync

        const record = {
            nombre_dispositivo: row[1],
            piso_dispositivo: row[2] ? parseInt(row[2]) : null,
            activo: row[3] === '' ? true : (row[3] === true || row[3] === 'TRUE' || row[3] === 1),
            es_critico: row[4] === true || row[4] === 'TRUE' || row[4] === 1,
            cupo_minimo: row[5] ? parseInt(row[5]) : 0,
            cupo_optimo: row[6] ? parseInt(row[6]) : 0
        };
        
        const id_existente = row[0];
        
        // Si tiene ID, significa que ya está en uso o es un update.
        // Omitimos update por ahora (asignacion.gs se enfoca en inserts básicos),
        // el update completo de Dispositivos está en Capacitaciones.gs.
        if (id_existente) {
             continue; 
        }
        
        const res = insertRow('dispositivos', record);
        if (res.success) {
            sheet.getRange(i+1, headers.indexOf('sync_status')+1).setValue('✅ OK ' + res.data[0].id_dispositivo);
            sheet.getRange(i+1, 1).setValue(res.data[0].id_dispositivo); // Escribir ID generado
            results.ok++;
        } else {
             sheet.getRange(i+1, headers.indexOf('sync_status')+1).setValue('❌ ' + res.error);
             results.err++;
        }
    }
    
    ui.alert(`Proceso finalizado.\n✅ OK: ${results.ok}\n❌ Errores: ${results.err}`);
}

// ============================================================================
// CARGA MASIVA DE CALENDARIO (PARSER COMPACTO)
// ============================================================================

function uploadCalendarioCompacto() {
    const ui = SpreadsheetApp.getUi();
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('CARGA_CALENDARIO');
    
    if (!sheet) {
        const newSheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('CARGA_CALENDARIO');
        newSheet.appendRow(['Fecha (YYYY-MM-DD)', 'Turno (ID)', 'Configuración (Format: "ID:Cupo, ID, ID:Cupo")', 'Status']);
        newSheet.getRange('A1:D1').setFontWeight('bold');
        ui.alert('Hoja CARGA_CALENDARIO creada. Por favor completa los datos e intenta de nuevo.');
        return;
    }
    
    const data = sheet.getDataRange().getValues();
    const payload = [];
    const rowsToUpdate = [];
    
    // Recolectar datos
    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        const fechaRaw = row[0];
        const idTurno = row[1];
        const configStr = String(row[2]).trim();
        const currentStatus = row[3];
        
        if (!fechaRaw || !idTurno || !configStr) continue;
        if (String(currentStatus).includes('✅')) continue; // Skip ya procesados
        
        const fecha = formatDate_(fechaRaw);
        
        payload.push({
            fecha: fecha,
            id_turno: idTurno,
            config_raw: configStr
        });
        rowsToUpdate.push(i + 1);
    }
    
    if (payload.length === 0) {
        ui.alert('No hay nuevos datos para cargar.');
        return;
    }
    
    // RPC Call
    try {
        const res = callRpc('rpc_importar_calendario', { payload: payload });
        
        if (res.success && res.data && res.data.success) {
            const msg = '✅ Lote Enviado';
            rowsToUpdate.forEach(rowIndex => {
                sheet.getRange(rowIndex, 4).setValue(msg);
            });
            ui.alert(`Carga completada.\nItems procesados: ${res.data.inserted_items}`);
        } else {
             const errMsg = res.error || (res.data ? res.data.error : 'Unknown Error');
             rowsToUpdate.forEach(rowIndex => {
                sheet.getRange(rowIndex, 4).setValue('❌ Error Lote');
            });
            ui.alert(`❌ Error en carga masiva: ${errMsg}`);
        }
        
    } catch (e) {
        ui.alert('❌ Exception: ' + e.message);
    }
}


/**
 * Parsea "1:2, 5, 8:3" -> Objetos
 * @private
 * @deprecated ELT architecture moves parsing to SQL
 */
function parseDispositivosString_(str) {
    // Deprecated by ELT Architecture
    return [];
}

// ============================================================================
// UI MATRIZ VISUAL (DISEÑO)
// ============================================================================

/**
 * Genera la hoja DISEÑO_CALENDARIO con dispositivos como columnas.
 * Facilita la carga manual visual.
 */

function generarPlantillaDiseño() {
  const ui = SpreadsheetApp.getUi();
  const filters = getActiveFilters();
  
  try {
    const anio = filters.año_activo;
    const mes = filters.mes_activo;
    
    // 1. Obtener Dispositivos Activos
    const dispositivos = fetchAllWithFilters('dispositivos', 'id_dispositivo, nombre_dispositivo, piso_dispositivo', { activo: true });
    
    if (dispositivos.length === 0) {
      ui.alert('No hay dispositivos activos para generar la plantilla.');
      return;
    }
    
    // Ordenar: Piso ASC, luego Nombre ASC
    dispositivos.sort((a, b) => {
        const pisoA = a.piso_dispositivo || 999;
        const pisoB = b.piso_dispositivo || 999;
        if (pisoA !== pisoB) return pisoA - pisoB;
        return a.nombre_dispositivo.localeCompare(b.nombre_dispositivo);
    });

    const sheet = getOrCreateSheet_('DISEÑO_CALENDARIO');
    sheet.clear();
    
    // 2. Preparar Datos Pre-llenados
    const fechaInicio = new Date(anio, mes - 1, 1);
    const fechaFin = new Date(anio, mes, 0);
    const fechaInicioStr = formatDate_(fechaInicio);
    const fechaFinStr = formatDate_(fechaFin);
    
    // 2.1 Demanda Planificada (Base para las filas)
    // Usamos vista_demanda_planificada para obtener SOLO los turnos que existen realmente
    const demandaRaw = fetchAllWithFilters('vista_demanda_planificada', 'fecha,id_turno,nombre_turno,cantidad_personas', {
        fecha: { operator: 'gte', value: fechaInicioStr }
    });
    
    // Filtrar por fecha tope (el filtro API fue solo >= inicio)
    const demandaMes = demandaRaw.filter(d => {
        const f = formatDate_(d.fecha);
        return f <= fechaFinStr;
    });
    
    if (demandaMes.length === 0) {
         ui.alert(`⚠️ No hay planificación cargada para ${mes}/${anio}. Primero carga la planificación.`);
         return;
    }
    
    // Ordenar por Fecha y Turno
    demandaMes.sort((a, b) => {
        if (a.fecha !== b.fecha) return a.fecha.localeCompare(b.fecha);
        return a.id_turno - b.id_turno;
    });

    // 2.2 Calendario Existente (Para pre-llenar cupos)
    const calendarioRaw = fetchAllWithFilters('calendario_dispositivos', 'fecha,id_turno,id_dispositivo,cupo_objetivo', {
        fecha: { operator: 'gte', value: fechaInicioStr }
    });
    
    // Indexar Calendario: "AAAA-MM-DD_TurnoID_DispID" -> cupo
    const mapCupos = {};
    if (calendarioRaw && calendarioRaw.length > 0) {
        calendarioRaw.forEach(c => {
            const fRaw = formatDate_(c.fecha); 
            if (fRaw <= fechaFinStr) { // Solo mes actual
               const key = `${fRaw}_${c.id_turno}_${c.id_dispositivo}`;
               mapCupos[key] = c.cupo_objetivo;
            }
        });
    }

    // 3. Generar Headers
    const headersIds = ['META_FECHA', 'META_TURNO_ID', 'META_TURNO_NOMBRE', 'META_CONVOCADOS'];
    const headersNombres = ['Fecha (YYYY-MM-DD)', 'ID Turno', 'Nombre Turno', '👥 Convocados'];
    const headerColors = ["#E6E6E6", "#E6E6E6", "#E6E6E6", "#E6E6E6"];
    
    dispositivos.forEach(d => {
        headersIds.push(d.id_dispositivo);
        const nombre = d.nombre_dispositivo.length > 20 ? d.nombre_dispositivo.substring(0,20) + '…' : d.nombre_dispositivo;
        headersNombres.push(nombre);
        
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
    
    sheet.getRange(1, 1, 1, headersIds.length).setValues([headersIds]).setFontColor('#CCCCCC'); 
    
    const headerRange = sheet.getRange(2, 1, 1, headersNombres.length);
    headerRange.setValues([headersNombres]).setFontWeight('bold');
    headerRange.setBackgrounds([headerColors]);
    sheet.setFrozenRows(2);
    sheet.setFrozenColumns(4); 
    sheet.hideRows(1); 
    
    // 4. Generar Filas BASADAS EN DEMANDA REAL
    const rows = [];
    
    demandaMes.forEach(demanda => {
        const fechaStr = formatDate_(demanda.fecha);
        const idTurno = demanda.id_turno;
        
        // Construir fila
        const row = [
            fechaStr, 
            idTurno, 
            demanda.nombre_turno || ('Turno ' + idTurno), 
            demanda.cantidad_personas || 0
        ];
        
        dispositivos.forEach(disp => {
            // Buscar si ya existe configuración para este Slot + Dispositivo
            const key = `${fechaStr}_${idTurno}_${disp.id_dispositivo}`;
            const val = mapCupos[key] !== undefined ? mapCupos[key] : '';
            row.push(val);
        });
        
        rows.push(row);
    });
    
    if (rows.length > 0) {
        sheet.getRange(3, 1, rows.length, rows[0].length).setValues(rows);
        // Estilo: Centrar cupos, colorear convocados
        sheet.getRange(3, 5, rows.length, dispositivos.length).setHorizontalAlignment('center');
        sheet.getRange(3, 4, rows.length, 1).setBackground('#E8F5E9').setHorizontalAlignment('center').setFontWeight('bold');
    }
    
    sheet.autoResizeColumns(1, headersNombres.length);
    ui.alert(`✅ Plantilla generada para ${mes}/${anio}.\nFilas creadas: ${rows.length} (Basado en Planificación real).`);

  } catch (e) {
    ui.alert('❌ Error: ' + e.message);
  }
}

/**
 * Lee la matriz visual y sube datos al Staging de Supabase
 */
function uploadDiseñoMatriz() {
    const ui = SpreadsheetApp.getUi();
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('DISEÑO_CALENDARIO');
    if (!sheet) {
        ui.alert('No se encuentra la hoja DISEÑO_CALENDARIO');
        return;
    }
    
    const data = sheet.getDataRange().getValues();
    if (data.length < 3) {
        ui.alert('Hoja vacía o sin datos.');
        return;
    }
    
    // Fila 1 oculta tiene los IDs
    const headerIds = data[0];
    const colOffset = 4; 
    
    const mapColToId = {};
    let countDisps = 0;
    for (let c = colOffset; c < headerIds.length; c++) {
        const idDisp = headerIds[c];
        if (idDisp && !isNaN(idDisp)) {
            mapColToId[c] = idDisp;
            countDisps++;
        }
    }
    
    if (countDisps === 0) {
        ui.alert('❌ Error: No se encontraron IDs de dispositivos en la fila 1 (oculta). Regenera la plantilla.');
        return;
    }
    
    const logColumnIndex = headerIds.length + 1;
    const payload = [];
    const rowsToUpdate = [];

    // Iterar filas de datos (desde fila 3, índice 2)
    for (let r = 2; r < data.length; r++) {
        const row = data[r];
        const fecha = row[0];
        const idTurno = row[1];
        
        if (!fecha || !idTurno) continue;
        
        const entries = [];
        let hasData = false;
        
        for (let c = colOffset; c < row.length; c++) {
            const cupoVal = row[c];
            if (cupoVal !== '' && cupoVal !== null && !isNaN(cupoVal) && cupoVal > 0) {
                const idDisp = mapColToId[c];
                if (idDisp) {
                    entries.push(idDisp + ':' + cupoVal);
                    hasData = true;
                }
            }
        }
        
        if (!hasData) continue;
        
        const configStr = entries.join(', ');
        
        payload.push({
            fecha: formatDate_(fecha),
            id_turno: idTurno,
            config_raw: configStr
        });
        rowsToUpdate.push(r + 1);
    }
    
    if (payload.length === 0) {
         ui.alert('No hay datos válidos para subir (asegúrate de poner cupos > 0).');
         return;
    }
    
     try {
        const res = callRpc('rpc_importar_calendario', { payload: payload });
        
        if (res.success && res.data && res.data.success) {
            const msg = '✅ OK Lote RPC';
            rowsToUpdate.forEach(rowIndex => {
                 sheet.getRange(rowIndex, logColumnIndex).setValue(msg);
            });
            ui.alert(`Carga completada.\nItems Procesados: ${res.data.inserted_items}`);
        } else {
            const errMsg = res.error || (res.data ? res.data.error : 'Unknown');
            rowsToUpdate.forEach(rowIndex => {
                 sheet.getRange(rowIndex, logColumnIndex).setValue('❌ Error');
            });
            ui.alert(`❌ Error en carga: ${errMsg}`);
        }
    } catch (e) {
        ui.alert('❌ Excepción: ' + e.message);
    }
}


function downloadAsignaciones() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();

    try {
        const anio = filters.año_activo;
        const mes = filters.mes_activo;

        const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFin = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;

        const data = fetchAllWithFilters('asignaciones', '*'); 
        const datosMes = data.filter(a => a.fecha >= fechaInicio && a.fecha <= fechaFin);

        if (datosMes.length === 0) {
            ui.alert('ℹ️ No hay asignaciones para ' + mes + '/' + anio);
            return;
        }

        const sheet = getOrCreateSheet_('ASIGNACIONES');
        sheet.clear();

        const headers = [
            'id', 'id_agente', 'id_dispositivo', 'fecha',
            'id_turno', 'es_doble_turno', 'es_capacitacion_servicio', 'created_at'
        ];

        const rows = datosMes.map(a => [
            a.id,
            a.id_agente,
            a.id_dispositivo,
            a.fecha,
            a.id_turno,
            a.es_doble_turno ? '⚠️ SÍ' : '',
            a.es_capacitacion_servicio ? '⚠️ En Servicio' : '',
            a.created_at
        ]);

        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
        if (rows.length > 0) {
            sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
            for (let i = 0; i < rows.length; i++) {
                if (datosMes[i].es_doble_turno) sheet.getRange(i + 2, 1, 1, headers.length).setBackground('#FFF3CD');
                if (datosMes[i].es_capacitacion_servicio) sheet.getRange(i + 2, 7, 1, 1).setBackground('#FFE5CC');
            }
        }
        sheet.setFrozenRows(1);
        sheet.autoResizeColumns(1, headers.length);
        ui.alert('✅ ' + rows.length + ' asignaciones descargadas');

    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}


function downloadEstadoCalendario() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();
    try {
        const anio = filters.año_activo;
        const mes = filters.mes_activo;
        const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFin = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;

        // Fetching view
        const data = fetchAllWithFilters('vista_estado_calendario', '*'); 
        const datosMes = data.filter(r => r.fecha >= fechaInicio && r.fecha <= fechaFin);

        if (datosMes.length === 0) {
            ui.alert('ℹ️ No hay planificación para ' + mes + '/' + anio);
            return;
        }

        const sheet = getOrCreateSheet_('ESTADO_CALENDARIO');
        sheet.clear();
        
        const headers = ['fecha', 'id_turno', 'nombre_turno', 'dispositivos_configurados', 'personas_asignadas', 'estado'];
        const rows = datosMes.map(r => [
            r.fecha,
            r.id_turno,
            r.nombre_turno,
            r.dispositivos_configurados,
            r.personas_asignadas,
            r.estado
        ]);

        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
        
        // Formato condicional
        const range = sheet.getRange(2, 6, rows.length, 1);
        const rulePend = SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('PENDIENTE').setBackground('#ffcdd2').setRanges([range]).build();
        const ruleConf = SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('CONFIGURADO').setBackground('#fff9c4').setRanges([range]).build();
        const ruleAsig = SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('ASIGNADO').setBackground('#c8e6c9').setRanges([range]).build();
        sheet.setConditionalFormatRules([rulePend, ruleConf, ruleAsig]);

        sheet.setFrozenRows(1);
        sheet.autoResizeColumns(1, headers.length);
        ui.alert('✅ ' + rows.length + ' registros de estado descargados');
        
    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}

function downloadCalendarioDispositivos() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();
    try {
        const anio = filters.año_activo;
        const mes = filters.mes_activo;
        const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFin = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;

        const data = fetchAllWithFilters('calendario_dispositivos', '*');
        const datosMes = data.filter(c => c.fecha >= fechaInicio && c.fecha <= fechaFin);

        if (datosMes.length === 0) {
            ui.alert('ℹ️ No hay calendario para ' + mes + '/' + anio);
            return;
        }

        const sheet = getOrCreateSheet_('CALENDARIO_DISPOSITIVOS');
        sheet.clear();
        const headers = ['id', 'fecha', 'id_turno', 'id_dispositivo', 'cupo_objetivo'];
        const rows = datosMes.map(c => [c.id, c.fecha, c.id_turno, c.id_dispositivo, c.cupo_objetivo]);

        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
        sheet.setFrozenRows(1);
        sheet.autoResizeColumns(1, headers.length);
        ui.alert('✅ ' + rows.length + ' registros descargados');
    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}

// Helpers privados
function getOrCreateSheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function getActiveFilters() {
    const ui = SpreadsheetApp.getUi();
    try {
        if (typeof getConfigValue === 'function') {
            const anio = getConfigValue('año_activo');
            const mes = getConfigValue('mes_activo');
            if (anio && mes) return { año_activo: anio, mes_activo: mes };
        }
    } catch (e) {}

    const fechaActual = new Date();
    const result = ui.prompt('Filtro Fecha', `Mes/Año (MM/YYYY) para descargar:\nEj: ${fechaActual.getMonth()+1}/${fechaActual.getFullYear()}`, ui.ButtonSet.OK_CANCEL);
    if (result.getSelectedButton() !== ui.Button.OK) throw new Error('Cancelado');
    
    const parts = result.getResponseText().trim().split('/');
    if (parts.length !== 2) throw new Error('Formato MM/YYYY requerido');
    return { año_activo: parseInt(parts[1]), mes_activo: parseInt(parts[0]) };
}

function formatDate_(dateValue) {
    if (dateValue instanceof Date) {
        return Utilities.formatDate(dateValue, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    }
    return String(dateValue).split('T')[0];
}

// ============================================================================
// ASIGNACIÓN DIARIA (Pestaña Operativa)
// ============================================================================

function generarPlantillaAsignacionDiaria() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();
    
    try {
        const anio = filters.año_activo;
        const mes = filters.mes_activo;
        const fechaInicioStr = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFinStr = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;
        
        // 1. Obtener Datos
        const calendario = fetchAllWithFilters('calendario_dispositivos', 'fecha, id_turno, id_dispositivo, cupo_objetivo', {
            fecha: { operator: 'gte', value: fechaInicioStr }
        }).filter(c => c.fecha <= fechaFinStr);
        
        if (calendario.length === 0) {
            ui.alert(`No hay dispositivos planificados cargados para ${mes}/${anio}.`);
            return;
        }
        
        const turnos = fetchAllWithFilters('turnos', 'id_turno, tipo_turno');
        const mapTurnos = new Map(turnos.map(t => [t.id_turno, t.tipo_turno]));
        
        // ¡Importante solicitar piso_dispositivo para colorear!
        const dispositivos = fetchAllWithFilters('dispositivos', 'id_dispositivo, nombre_dispositivo, piso_dispositivo');
        const mapDisp = new Map(dispositivos.map(d => [d.id_dispositivo, d]));
        
        // Ordenar calendario por Fecha, Turno, Dispositivo Decimal/Alfabético
        calendario.sort((a,b) => {
            if (a.fecha !== b.fecha) return a.fecha.localeCompare(b.fecha);
            if (a.id_turno !== b.id_turno) return a.id_turno - b.id_turno;
            
            // Ordenar por Piso, luego alfabético
            const dispA = mapDisp.get(a.id_dispositivo);
            const dispB = mapDisp.get(b.id_dispositivo);
            const pisoA = dispA ? (dispA.piso_dispositivo || 999) : 999;
            const pisoB = dispB ? (dispB.piso_dispositivo || 999) : 999;
            
            if (pisoA !== pisoB) return pisoA - pisoB;
            const nomA = dispA ? dispA.nombre_dispositivo : '';
            const nomB = dispB ? dispB.nombre_dispositivo : '';
            return nomA.localeCompare(nomB);
        });
        
        const sheet = getOrCreateSheet_('ASIGNACION_DIARIA');
        // Limpiamos SOLO las columnas de la A a la I (las primeras 9) para no borrar tus notas manuales
        sheet.getRange("A:I").clear();
        sheet.getRange("A:I").clearDataValidations();
        
        const headers = ['Fecha', 'Tipo de Turno', 'Dispositivo', 'Cantidad de Residentes', 'Residente 1', 'Residente 2', 'Residente 3', 'Residente 4', 'Residente 5'];
        
        const rows = calendario.map(c => [
            c.fecha,
            mapTurnos.get(c.id_turno) || c.id_turno,
            mapDisp.get(c.id_dispositivo) ? mapDisp.get(c.id_dispositivo).nombre_dispositivo : c.id_dispositivo,
            c.cupo_objetivo,
            '', '', '', '', ''
        ]);
        
        // Formato Cabecera
        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#E6E6E6');
        
        // Rellenar Datos
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
        
        // Pintar columna de Dispositivos (Columna C es index 3)
        const coloresPiso = rows.map((row, index) => {
            const dispName = row[2];
            // Buscar que dispositivo matchea este nombre
            const dispObj = dispositivos.find(d => d.nombre_dispositivo === dispName);
            if (!dispObj) return ['#ffffff'];
            
            switch (dispObj.piso_dispositivo) {
                case 1: return ["#fff2cc"]; // Amarillo
                case 2: return ["#ea9999"]; // Rojo
                case 3: return ["#a4c2f4"]; // Azul
                case 4: return ["#b6d7a8"]; // Verde
                default: return ["#ffffff"];
            }
        });
        sheet.getRange(2, 3, rows.length, 1).setBackgrounds(coloresPiso).setFontWeight('bold');
        
        // Regla de validación (Dropdowns) para residentes (Solo activos de la cohorte actual)
        const residentesRaw = fetchAllWithFilters('datos_personales', 'nombre, apellido, cohorte', { activo: true });
        const residentesDelAnio = residentesRaw.filter(r => r.cohorte == anio);
        
        // Formatear APELLIDO, Nombre EXACTO como viene de la base de datos (vital para el formato condicional)
        const residentesLista = residentesDelAnio.map(r => {
             return r.apellido + ', ' + r.nombre;
        }).sort();
        
        const validationRule = SpreadsheetApp.newDataValidation()
            .requireValueInList(residentesLista, true)
            .setAllowInvalid(true)
            .build();
            
        // Aplicar validación a las 5 columnas de residentes (E a I, es decir: 5 a 9)
        const rangeResidentes = sheet.getRange(2, 5, rows.length, 5);
        rangeResidentes.setDataValidation(validationRule); // Sin fondo quemado para permitir formato condicional
        
        // Reglas de Formato Condicional usando la hoja HISTORIAL_CAPACITACION
        // ROJO: El residente NO tiene ninguna capacitación en este dispositivo (COUNTIFS == 0)
        // OJO: E2 es la celda inicial relativa. Al no tener $, se moverá hacia F, G, etc. $C2 asegura que siempre mire el dispositivo en la columna C.
        const ruleRed = SpreadsheetApp.newConditionalFormatRule()
            .whenFormulaSatisfied(`=AND(E2<>"", COUNTIFS(INDIRECT("HISTORIAL_CAPACITACION!$C:$C"), E2, INDIRECT("HISTORIAL_CAPACITACION!$B:$B"), $C2)=0)`)
            .setBackground('#f4c7c3') // Rojo suavizado
            .setRanges([rangeResidentes])
            .build();
            
        // AMARILLO: El residente tiene capacitación en este dispositivo, pero figura como "No" asistió
        const ruleYellow = SpreadsheetApp.newConditionalFormatRule()
            .whenFormulaSatisfied(`=AND(E2<>"", COUNTIFS(INDIRECT("HISTORIAL_CAPACITACION!$C:$C"), E2, INDIRECT("HISTORIAL_CAPACITACION!$B:$B"), $C2, INDIRECT("HISTORIAL_CAPACITACION!$D:$D"), "No")>0)`)
            .setBackground('#fce8b2') // Amarillo suavizado
            .setRanges([rangeResidentes])
            .build();
            
        // VERDE: El residente está agendado (Sí o Pendiente) y su fecha de capa es <= a la apertura
        const ruleGreen = SpreadsheetApp.newConditionalFormatRule()
            .whenFormulaSatisfied(`=AND(E2<>"", COUNTIFS(INDIRECT("HISTORIAL_CAPACITACION!$C:$C"), E2, INDIRECT("HISTORIAL_CAPACITACION!$B:$B"), $C2, INDIRECT("HISTORIAL_CAPACITACION!$A:$A"), "<="&$A2, INDIRECT("HISTORIAL_CAPACITACION!$D:$D"), "<>No")>0)`)
            .setBackground('#b7e1cd') // Verde suavizado
            .setRanges([rangeResidentes])
            .build();
            
        // Aplicamos en orden (Verde, Amarillo, Rojo)
        sheet.setConditionalFormatRules([ruleGreen, ruleYellow, ruleRed]);
        
        // Estilos finales
        sheet.getRange(2, 1, rows.length, 1).setHorizontalAlignment('center'); // Fecha
        sheet.getRange(2, 4, rows.length, 1).setHorizontalAlignment('center'); // Cantidad

        sheet.autoResizeColumns(1, headers.length);
        sheet.setFrozenRows(1);
        
        ui.alert(`✅ Plantilla de Asignación generada.\nFilas: ${rows.length}\nPisos coloreados y Dropdowns de Nombres creados.`);

    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}

// ============================================================================
// HISTORIAL DE CAPACITACIONES (VISTA PLANA)
// ============================================================================

function downloadHistorialCapacitaciones() {
    const ui = SpreadsheetApp.getUi();
    
    try {
        const datos = fetchAllWithFilters('vista_historial_capacitaciones', '*');
        
        if (datos.length === 0) {
            ui.alert('ℹ️ El historial de capacitaciones está vacío.');
            return;
        }
        
        const sheet = getOrCreateSheet_('HISTORIAL_CAPACITACION');
        sheet.clear();
        
        const headers = ['Fecha Capacitación', 'Dispositivo Capacitado', 'Residente Capacitado', 'Asistió'];
        
        const rows = datos.map(r => [
            r.fecha_capacitacion,
            r.dispositivo_capacitado,
            r.residente_capacitado,
            r.estado_asistencia
        ]);
        
        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#E1BEE7');
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
        
        sheet.autoResizeColumns(1, headers.length);
        sheet.setFrozenRows(1);
        
        ui.alert(`✅ Historial (Convocatorias + Asistencias) descargado con éxito.\nTotal de registros: ${rows.length}`);

    } catch(e) {
        ui.alert('❌ Error al descargar historial: ' + e.message);
    }
}
