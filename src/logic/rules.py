"""
REGLAS DE NEGOCIO - MÓDULO DE ASIGNACIÓN DE RESIDENTES
========================================================

Basado en Schema Real de Supabase:
- capacitaciones_participantes: id_agente, id_cap, asistio
- capacitaciones_dispositivos: id_cap, id_dispositivo
- convocatoria: id_agente, fecha_convocatoria, id_turno, estado
- dispositivos: id_dispositivo, nombre_dispositivo
- datos_personales: id_agente (PK)
- turnos: id_turno (PK)

Tipos de Reglas:
    - HARD CONSTRAINTS (Bloqueos): Retornan False si no se cumple → Impiden asignación
    - SOFT CONSTRAINTS (Alertas): Retornan True si hay advertencia → No impiden

CAMBIO v2.1: La capacitación ahora es SOFT CONSTRAINT (Capacitación en Servicio)
    - Si no tiene capacitación formal, se marca es_capacitacion_servicio = True
    - No bloquea la asignación

Author: Pablo (Data Analyst)
Version: 2.1.0 - Capacitación como Soft Constraint
"""

from typing import Tuple
from datetime import date


# ============================================================================
# HARD CONSTRAINTS (Reglas Bloqueantes)
# ============================================================================

def es_convocado(id_agente: int, fecha: date, id_turno: int, supabase_client) -> Tuple[bool, str]:
    """
    Verifica si el residente fue convocado para esa fecha y turno.
    
    HARD CONSTRAINT: Si retorna False, NO se puede asignar.
    
    Args:
        id_agente: ID del residente (datos_personales.id_agente)
        fecha: Fecha de la asignación
        id_turno: ID del turno (turnos.id_turno)
        supabase_client: Cliente de Supabase conectado
        
    Returns:
        Tuple[bool, str]: (True si está convocado, mensaje descriptivo)
    """
    try:
        response = supabase_client.table('convocatoria') \
            .select('id_convocatoria') \
            .eq('id_agente', id_agente) \
            .eq('fecha_convocatoria', str(fecha)) \
            .eq('id_turno', id_turno) \
            .eq('estado', 'vigente') \
            .limit(1) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return (True, "✅ Residente convocado para este turno")
        else:
            return (False, "❌ BLOQUEO: El residente NO está convocado para esta fecha/turno")
            
    except Exception as e:
        print(f"Error en es_convocado: {e}")
        return (False, f"❌ ERROR: {str(e)}")


# ============================================================================
# SOFT CONSTRAINTS (Reglas de Alerta - NO bloquean)
# ============================================================================

def esta_capacitado(id_agente: int, id_dispositivo: int, supabase_client) -> Tuple[bool, str]:
    """
    Verifica si el residente tiene capacitación formal para el dispositivo.
    
    SOFT CONSTRAINT (v2.1): Ya NO bloquea. Si retorna False, se marca como 
    "Capacitación en Servicio" y el residente aprenderá durante el turno.
    
    Lógica: Busca en capacitaciones_participantes donde:
        - id_agente coincida
        - asistio = TRUE
        - id_cap esté vinculado al id_dispositivo en capacitaciones_dispositivos
    
    Args:
        id_agente: ID del residente (datos_personales.id_agente)
        id_dispositivo: ID del dispositivo (dispositivos.id_dispositivo)
        supabase_client: Cliente de Supabase conectado
        
    Returns:
        Tuple[bool, str]: (True si está capacitado, mensaje descriptivo)
    """
    try:
        # Paso 1: Obtener id_cap de capacitaciones que cubren este dispositivo
        caps_dispositivo = supabase_client.table('capacitaciones_dispositivos') \
            .select('id_cap') \
            .eq('id_dispositivo', id_dispositivo) \
            .execute()
        
        if not caps_dispositivo.data or len(caps_dispositivo.data) == 0:
            return (False, "⚠️ ALERTA: No hay capacitaciones registradas para este dispositivo → En Servicio")
        
        ids_cap = [c['id_cap'] for c in caps_dispositivo.data]
        
        # Paso 2: Verificar si el agente asistió a alguna de esas capacitaciones
        participacion = supabase_client.table('capacitaciones_participantes') \
            .select('id_agente') \
            .eq('id_agente', id_agente) \
            .eq('asistio', True) \
            .in_('id_cap', ids_cap) \
            .limit(1) \
            .execute()
        
        if participacion.data and len(participacion.data) > 0:
            return (True, "✅ Residente capacitado formalmente")
        else:
            return (False, "⚠️ ALERTA: Sin capacitación formal → Capacitación en Servicio")
            
    except Exception as e:
        print(f"Error en esta_capacitado: {e}")
        return (False, f"⚠️ No se pudo verificar capacitación: {str(e)}")


def detectar_doble_turno(id_agente: int, fecha: date, supabase_client) -> Tuple[bool, int, str]:
    """
    Detecta si el residente ya tiene otra asignación en el mismo día.
    
    SOFT CONSTRAINT: No impide la asignación, retorna indicador para
    que el Frontend pinte la celda de color (alerta visual).
    
    Args:
        id_agente: ID del residente
        fecha: Fecha de la asignación
        supabase_client: Cliente de Supabase
        
    Returns:
        Tuple[bool, int, str]: (hay_doble_turno, cantidad_turnos_previos, mensaje)
    """
    try:
        response = supabase_client.table('asignaciones') \
            .select('id', count='exact') \
            .eq('id_agente', id_agente) \
            .eq('fecha', str(fecha)) \
            .execute()
        
        cantidad = response.count or 0
        
        if cantidad > 0:
            return (True, cantidad, f"⚠️ ALERTA: El residente ya tiene {cantidad} turno(s) este día")
        else:
            return (False, 0, "✅ Sin conflictos de turno")
            
    except Exception as e:
        print(f"Error en detectar_doble_turno: {e}")
        return (False, 0, f"⚠️ No se pudo verificar: {str(e)}")


# ============================================================================
# VALIDACIÓN COMPLETA
# ============================================================================

def validar_asignacion(
    id_agente: int,
    id_dispositivo: int,
    fecha: date,
    id_turno: int,
    supabase_client
) -> dict:
    """
    Ejecuta todas las validaciones para una asignación.
    
    Returns:
        dict: {
            'puede_asignar': bool,                    # True solo si pasa TODOS los hard constraints
            'es_doble_turno': bool,                   # True si tiene otro turno ese día
            'requiere_capacitacion_servicio': bool,   # True si NO tiene capacitación formal
            'bloqueos': list[str],                    # Lista de mensajes de bloqueo (hard)
            'alertas': list[str]                      # Lista de mensajes de alerta (soft)
        }
    """
    resultado = {
        'puede_asignar': True,
        'es_doble_turno': False,
        'requiere_capacitacion_servicio': False,
        'bloqueos': [],
        'alertas': []
    }
    
    # === HARD CONSTRAINTS (Bloquean) ===
    
    # 1. ¿Está convocado? (ÚNICO hard constraint)
    convocado, msg_convocado = es_convocado(id_agente, fecha, id_turno, supabase_client)
    if not convocado:
        resultado['puede_asignar'] = False
        resultado['bloqueos'].append(msg_convocado)
    
    # === SOFT CONSTRAINTS (Alertas - NO bloquean) ===
    
    # 2. ¿Está capacitado? (Ahora es SOFT)
    capacitado, msg_capacitado = esta_capacitado(id_agente, id_dispositivo, supabase_client)
    if not capacitado:
        resultado['requiere_capacitacion_servicio'] = True
        resultado['alertas'].append(msg_capacitado)
    
    # 3. ¿Ya tiene otro turno ese día?
    doble, cantidad, msg_doble = detectar_doble_turno(id_agente, fecha, supabase_client)
    if doble:
        resultado['es_doble_turno'] = True
        resultado['alertas'].append(msg_doble)
    
    return resultado


# ============================================================================
# OBTENER DISPOSITIVOS DEL CALENDARIO
# ============================================================================

def obtener_dispositivos_turno(fecha: date, id_turno: int, supabase_client) -> list:
    """
    Consulta calendario_dispositivos para ver qué dispositivos hay en un turno.
    
    Returns:
        list[dict]: Lista de dispositivos con id, nombre y cupo_objetivo
    """
    try:
        response = supabase_client.table('calendario_dispositivos') \
            .select('id_dispositivo, cupo_objetivo, dispositivos(nombre_dispositivo)') \
            .eq('fecha', str(fecha)) \
            .eq('id_turno', id_turno) \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Error en obtener_dispositivos_turno: {e}")
        return []
