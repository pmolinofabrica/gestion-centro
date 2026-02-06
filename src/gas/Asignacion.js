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
 *   - Si no tiene capacitación formal, se marca es_capacitacion_servicio = true
 *   - No bloquea la asignación
 * 
 * @author Pablo (Data Analyst)
 * @version 2.1.0 - Capacitación como Soft Constraint
 */

// ============================================================================
// OBTENER RESIDENTES DISPONIBLES
// ============================================================================

/**
 * Obtiene TODOS los residentes convocados para una fecha y turno.
 * Ya NO filtra por capacitación (Cambio v2.1).
 * Marca visualmente quiénes están capacitados y quiénes no.
 * 
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
        Logger.log('✅ Dispositivos en calendario: ' + idsDispositivos.length);

        // 2. Obtener TODOS los convocados vigentes para esa fecha/turno
        const convocados = fetchAllWithFilters('convocatoria',
            'id_agente', {
            fecha_convocatoria: fecha,
            id_turno: idTurno,
            estado: 'vigente'
        });

        if (convocados.length === 0) {
            Logger.log('⚠️ No hay convocados vigentes');
            return { dispositivos: calendario, residentes: [], mensaje: 'No hay residentes convocados' };
        }

        const idsConvocados = convocados.map(c => c.id_agente);
        Logger.log('✅ Convocados: ' + idsConvocados.length);

        // 3. Obtener lista de capacitados (para marcar, NO para filtrar)
        const capacitados = obtenerCapacitadosParaDispositivos_(idsDispositivos);

        // 4. Obtener datos personales de TODOS los convocados
        const residentes = [];
        idsConvocados.forEach(idAgente => {
            try {
                const persona = fetchOne('datos_personales', 'id_agente, nombre, apellido, dni', {
                    id_agente: idAgente
                });

                if (persona) {
                    // Verificar si ya tiene asignación ese día
                    const asignacionesDia = fetchAllWithFilters('asignaciones', 'id', {
                        id_agente: idAgente,
                        fecha: fecha
                    });

                    // Verificar si está capacitado (para marcar visualmente)
                    const estaCapacitado = capacitados.includes(idAgente);

                    residentes.push({
                        id_agente: persona.id_agente,
                        nombre: persona.nombre,
                        apellido: persona.apellido,
                        dni: persona.dni,
                        nombre_completo: persona.apellido + ', ' + persona.nombre,
                        es_doble_turno: asignacionesDia.length > 0,
                        turnos_dia: asignacionesDia.length,
                        // NUEVO v2.1: Indicadores de capacitación
                        esta_capacitado: estaCapacitado,
                        requiere_capacitacion_servicio: !estaCapacitado,
                        icono_alerta: estaCapacitado ? '' : '⚠️ En Servicio'
                    });
                }
            } catch (e) {
                Logger.log('Error obteniendo datos de agente ' + idAgente + ': ' + e.message);
            }
        });

        // Ordenar por apellido
        residentes.sort((a, b) => a.apellido.localeCompare(b.apellido));

        Logger.log('✅ Total residentes (todos los convocados): ' + residentes.length);
        Logger.log('   - Capacitados: ' + residentes.filter(r => r.esta_capacitado).length);
        Logger.log('   - En Servicio: ' + residentes.filter(r => r.requiere_capacitacion_servicio).length);

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
        // Paso 1: Obtener id_cap de capacitaciones que cubren estos dispositivos
        const capsDispositivo = [];
        idsDispositivos.forEach(idDisp => {
            const caps = fetchAllWithFilters('capacitaciones_dispositivos', 'id_cap', {
                id_dispositivo: idDisp
            });
            caps.forEach(c => {
                if (!capsDispositivo.includes(c.id_cap)) {
                    capsDispositivo.push(c.id_cap);
                }
            });
        });

        if (capsDispositivo.length === 0) return [];

        // Paso 2: Obtener agentes que asistieron a esas capacitaciones
        const agentesCapacitados = [];
        capsDispositivo.forEach(idCap => {
            const participantes = fetchAllWithFilters('capacitaciones_participantes', 'id_agente', {
                id_cap: idCap,
                asistio: true
            });
            participantes.forEach(p => {
                if (!agentesCapacitados.includes(p.id_agente)) {
                    agentesCapacitados.push(p.id_agente);
                }
            });
        });

        return agentesCapacitados;

    } catch (e) {
        Logger.log('Error en obtenerCapacitadosParaDispositivos_: ' + e.message);
        return [];
    }
}

// ============================================================================
// GUARDAR ASIGNACIÓN
// ============================================================================

/**
 * Guarda una asignación de residente a dispositivo.
 * Cambio v2.1: Capacitación ya NO bloquea. Si no tiene, marca es_capacitacion_servicio = true.
 * 
 * @param {number} idAgente - ID del residente (datos_personales.id_agente)
 * @param {number} idDispositivo - ID del dispositivo
 * @param {string} fecha - Fecha en formato 'YYYY-MM-DD'
 * @param {number} idTurno - ID del turno
 * @returns {Object} Resultado de la operación
 */
function guardarAsignacion(idAgente, idDispositivo, fecha, idTurno) {
    try {
        // 1. HARD CONSTRAINT: Verificar que está convocado (ÚNICO bloqueo)
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

        // 2. SOFT CONSTRAINT: Verificar capacitación (ya NO bloquea)
        const capacitados = obtenerCapacitadosParaDispositivos_([idDispositivo]);
        const estaCapacitado = capacitados.includes(idAgente);
        const esCapacitacionServicio = !estaCapacitado;

        // 3. SOFT CONSTRAINT: Verificar doble turno
        const asignacionesPrevias = fetchAllWithFilters('asignaciones', 'id', {
            id_agente: idAgente,
            fecha: fecha
        });
        const esDobleTurno = asignacionesPrevias.length > 0;

        // 4. Insertar asignación con TODOS los flags
        const nuevaAsignacion = {
            id_agente: idAgente,
            id_dispositivo: idDispositivo,
            fecha: fecha,
            id_turno: idTurno,
            es_doble_turno: esDobleTurno,
            es_capacitacion_servicio: esCapacitacionServicio  // NUEVO v2.1
        };

        const resultado = insertRow('asignaciones', nuevaAsignacion);

        if (resultado.error) {
            return {
                success: false,
                error: '❌ Error al guardar: ' + resultado.error,
                tipo: 'database_error'
            };
        }

        // 5. Retornar resultado con alertas
        const response = {
            success: true,
            id: resultado.data[0].id,
            es_doble_turno: esDobleTurno,
            es_capacitacion_servicio: esCapacitacionServicio,
            mensaje: '✅ Asignación guardada correctamente',
            alertas: []
        };

        if (esDobleTurno) {
            response.alertas.push('⚠️ DOBLE TURNO: Este es el turno #' + (asignacionesPrevias.length + 1) + ' del día');
        }

        if (esCapacitacionServicio) {
            response.alertas.push('⚠️ CAPACITACIÓN EN SERVICIO: El residente aprenderá durante el turno');
        }

        Logger.log('✅ Asignación guardada: ' + JSON.stringify(response));
        return response;

    } catch (e) {
        Logger.log('❌ Error en guardarAsignacion: ' + e.message);
        return {
            success: false,
            error: e.message,
            tipo: 'exception'
        };
    }
}

// ============================================================================
// FUNCIONES DE DESCARGA Y UI
// ============================================================================

/**
 * Descarga asignaciones del mes activo a hoja ASIGNACIONES
 */
function downloadAsignaciones() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();

    try {
        const anio = filters.año_activo || new Date().getFullYear();
        const mes = filters.mes_activo || new Date().getMonth() + 1;

        // Construir rango de fechas
        const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFin = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;

        // Fetch asignaciones
        const data = fetchAll('asignaciones', '*');
        const datosMes = data.filter(a => a.fecha >= fechaInicio && a.fecha <= fechaFin);

        if (datosMes.length === 0) {
            ui.alert('ℹ️ No hay asignaciones para ' + mes + '/' + anio);
            return;
        }

        const sheet = getOrCreateSheet_('ASIGNACIONES');
        sheet.clear();

        // Headers actualizados con nueva columna
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
            a.es_doble_turno ? '⚠️ Doble' : '',
            a.es_capacitacion_servicio ? '⚠️ En Servicio' : '',
            a.created_at
        ]);

        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
        if (rows.length > 0) {
            sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);

            // Formateo condicional
            for (let i = 0; i < rows.length; i++) {
                // Amarillo para doble turno
                if (datosMes[i].es_doble_turno) {
                    sheet.getRange(i + 2, 1, 1, headers.length).setBackground('#FFF3CD');
                }
                // Naranja claro para capacitación en servicio
                if (datosMes[i].es_capacitacion_servicio) {
                    sheet.getRange(i + 2, 7, 1, 1).setBackground('#FFE5CC');
                }
            }
        }

        sheet.setFrozenRows(1);
        sheet.autoResizeColumns(1, headers.length);

        ui.alert('✅ ' + rows.length + ' asignaciones descargadas');

    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}

/**
 * Descarga calendario de dispositivos del mes
 */
function downloadCalendarioDispositivos() {
    const ui = SpreadsheetApp.getUi();
    const filters = getActiveFilters();

    try {
        const anio = filters.año_activo || new Date().getFullYear();
        const mes = filters.mes_activo || new Date().getMonth() + 1;

        const fechaInicio = anio + '-' + String(mes).padStart(2, '0') + '-01';
        const ultimoDia = new Date(anio, mes, 0).getDate();
        const fechaFin = anio + '-' + String(mes).padStart(2, '0') + '-' + ultimoDia;

        const data = fetchAll('calendario_dispositivos', '*');
        const datosMes = data.filter(c => c.fecha >= fechaInicio && c.fecha <= fechaFin);

        if (datosMes.length === 0) {
            ui.alert('ℹ️ No hay calendario para ' + mes + '/' + anio);
            return;
        }

        const sheet = getOrCreateSheet_('CALENDARIO_DISPOSITIVOS');
        sheet.clear();

        const headers = ['id', 'fecha', 'id_turno', 'id_dispositivo', 'cupo_objetivo'];

        const rows = datosMes.map(c => [
            c.id,
            c.fecha,
            c.id_turno,
            c.id_dispositivo,
            c.cupo_objetivo
        ]);

        sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
        sheet.setFrozenRows(1);
        sheet.autoResizeColumns(1, headers.length);

        ui.alert('✅ ' + rows.length + ' registros de calendario descargados');

    } catch (e) {
        ui.alert('❌ Error: ' + e.message);
    }
}
