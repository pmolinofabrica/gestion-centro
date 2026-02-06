#!/usr/bin/env python3
"""
SCRIPT DE CARGA v3.0 - DAMA COMPLIANT
======================================

Carga datos desde Excel al nuevo diseño DAMA-compliant:
- Turnos sin numero_dia_semana (catálogo puro)
- Planificación con horarios efectivos
- Data lineage explícito

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import pandas as pd
import sqlite3
import unicodedata
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DB_PATH = 'data/gestion_rrhh.db'
EXCEL_CONV = 'data/conv.xlsx'
EXCEL_EQUIVALENCIAS = 'data/equivalencias.xlsx'
EXCEL_GLOBAL = 'data/global.xlsx'

# Colores para output
class Color:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    FIN = '\033[0m'
    BOLD = '\033[1m'

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def normalizar(texto):
    """Normaliza texto para comparación"""
    if texto is None or pd.isna(texto):
        return ''
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

def print_step(step, total, text):
    """Imprime paso actual"""
    print(f"\n{Color.AZUL}[{step}/{total}]{Color.FIN} {Color.BOLD}{text}{Color.FIN}")

def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"  {Color.VERDE}✅ {text}{Color.FIN}")

def print_error(text):
    """Imprime mensaje de error"""
    print(f"  {Color.ROJO}❌ {text}{Color.FIN}")

def print_warning(text):
    """Imprime advertencia"""
    print(f"  {Color.AMARILLO}⚠️  {text}{Color.FIN}")

def fila_vacia(row, campos_criticos):
    """Verifica si una fila está vacía en campos críticos"""
    return all(pd.isna(row.get(campo)) or str(row.get(campo)).strip() == '' 
               for campo in campos_criticos)

# ============================================================================
# FUNCIONES DE CARGA
# ============================================================================

def limpiar_datos(conn):
    """Limpia datos previos manteniendo estructura"""
    print_step(1, 9, "Limpiando datos previos...")
    cursor = conn.cursor()
    
    # Orden correcto para evitar errores de FK
    tablas = [
        'convocatoria_historial',
        'convocatoria',
        'menu',
        'inasistencias',
        'certificados',
        'saldos',
        'planificacion',
        'capacitaciones_participantes',
        'capacitaciones_dispositivos',
        'capacitaciones'
    ]
    
    for tabla in tablas:
        try:
            cursor.execute(f"DELETE FROM {tabla}")
        except:
            pass
    
    conn.commit()
    print_success("Base de datos limpiada")

def cargar_datos_personales(conn):
    """Carga residentes desde global.xlsx"""
    print_step(2, 9, "Cargando datos personales...")
    
    df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Datos personales')
    cursor = conn.cursor()
    
    insertados = 0
    for _, row in df.iterrows():
        nombre_completo = str(row.get('Nombre y apellido', '')).strip()
        if ',' not in nombre_completo:
            continue
            
        partes = nombre_completo.split(',')
        apellido = partes[0].strip()
        nombre = partes[1].strip() if len(partes) > 1 else ''
        
        dni = str(row.get('DNI', '')).strip()
        if not dni or dni == 'nan':
            continue
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO datos_personales 
                (nombre, apellido, dni, fecha_nacimiento, email, telefono)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nombre, apellido, dni,
                '1990-01-01',  # Default
                f"{normalizar(nombre)}.{normalizar(apellido)}@ejemplo.com",
                ''
            ))
            if cursor.rowcount > 0:
                insertados += 1
        except Exception as e:
            continue
    
    conn.commit()
    print_success(f"{insertados} residentes cargados")

def generar_dias_y_turnos(conn):
    """Genera días y turnos v3.0 (sin numero_dia_semana)"""
    print_step(3, 9, "Generando días y turnos...")
    
    from datetime import date, timedelta
    
    cursor = conn.cursor()
    
    # Generar días
    start_date = date(2025, 1, 1)
    end_date = date(2025, 12, 31)
    dias_insertados = 0
    
    current = start_date
    while current <= end_date:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO dias 
                (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                current.isoformat(),
                current.month,
                current.isocalendar()[1],
                current.day,
                current.weekday()
            ))
            if cursor.rowcount > 0:
                dias_insertados += 1
        except:
            pass
        
        current += timedelta(days=1)
    
    # Turnos v3.0 (catálogo DAMA)
    turnos_data = [
        ('mañana', 'Turno mañana lun-vie', '08:45', '11:15', 2.5, 1, 0),
        ('tarde', 'Turno tarde lun-vie', '13:45', '16:15', 2.5, 1, 0),
        ('intermedio', 'Turno intermedio lun-vie', '11:30', '13:30', 2.0, 1, 0),
        ('capacitacion', 'Capacitación con horario variable', None, None, None, 0, 0),
        ('apertura_publico_corto', 'Apertura al público 4.5h', '14:45', '19:15', 4.5, 0, 1),
        ('apertura_publico_largo', 'Apertura al público 5.5h', '14:45', '20:15', 5.5, 0, 1),
        ('descanso', 'Día de descanso', '00:00', '00:00', 0.0, 0, 0)
    ]
    
    turnos_insertados = 0
    for tipo, desc, inicio, fin, horas, solo_semana, solo_finde in turnos_data:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO turnos 
                (tipo_turno, descripcion, hora_inicio_default, hora_fin_default, 
                 cant_horas_default, solo_semana, solo_fines_semana)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tipo, desc, inicio, fin, horas, solo_semana, solo_finde))
            if cursor.rowcount > 0:
                turnos_insertados += 1
        except Exception as e:
            print_error(f"Error insertando turno {tipo}: {e}")
    
    conn.commit()
    print_success(f"{dias_insertados} días generados")
    print_success(f"{turnos_insertados} turnos creados")

def cargar_dispositivos(conn):
    """Carga dispositivos desde global.xlsx"""
    print_step(4, 9, "Cargando dispositivos...")
    
    try:
        df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Dispositivos')
    except:
        print_warning("Hoja 'Dispositivos' no encontrada, usando defaults")
        df = pd.DataFrame({
            'Nombre': ['Sala Papel', 'Sala Textil', 'Sala Madera'],
            'Piso': [1, 2, 3]
        })
    
    cursor = conn.cursor()
    insertados = 0
    
    for _, row in df.iterrows():
        nombre = str(row.get('Nombre', '')).strip()
        piso = int(row.get('Piso', 0))
        
        if not nombre:
            continue
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO dispositivos (nombre_dispositivo, piso_dispositivo)
                VALUES (?, ?)
            """, (nombre, piso))
            if cursor.rowcount > 0:
                insertados += 1
        except:
            pass
    
    conn.commit()
    print_success(f"{insertados} dispositivos cargados")

def cargar_convocatorias(conn):
    """Carga convocatorias con planificación automática v3.0"""
    print_step(5, 9, "Cargando convocatorias...")
    
    df = pd.read_excel(EXCEL_CONV, sheet_name='Convocatoria')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(str(r['NOMBRE Y APELLIDO'])).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025']) and pd.notna(r['NOMBRE Y APELLIDO']) 
        and ',' in str(r['NOMBRE Y APELLIDO'])
    }
    
    cursor = conn.cursor()
    
    # Obtener agentes
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    # Obtener turnos v3.0 (sin numero_dia_semana)
    cursor.execute("SELECT id_turno, tipo_turno FROM turnos")
    turnos_dict = {tipo: id_t for id_t, tipo in cursor.fetchall()}
    
    insertados = 0
    sin_fecha = 0
    sin_residente = 0
    sin_turno = 0
    filas_vacias = 0
    
    stats_turnos = {}  # Para debug
    
    for idx, row in df.iterrows():
        # Verificar fila vacía
        if fila_vacia(row, ['Dia', 'Residente', 'Turno']):
            filas_vacias += 1
            continue
        
        # Validar fecha
        fecha = pd.to_datetime(row.get('Dia'), errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha_str <= '2025-12-31'):
            sin_fecha += 1
            continue
        
        # Validar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        if not apellido or apellido not in agentes:
            sin_residente += 1
            continue
        
        id_agente = agentes[apellido]
        
        # Determinar tipo de turno (v3.0)
        turno_raw = normalizar(row.get('Turno'))
        tipo_turno = None
        
        if 'apertura' in turno_raw:
            tipo_turno = 'apertura_publico_corto'  # Default
        elif 'tarde' in turno_raw:
            tipo_turno = 'tarde'
        elif 'manana' in turno_raw or 'mañana' in turno_raw:
            tipo_turno = 'mañana'
        elif 'intermedio' in turno_raw:
            tipo_turno = 'intermedio'
        elif 'capacita' in turno_raw:
            tipo_turno = 'capacitacion'
        else:
            tipo_turno = 'capacitacion'  # Default
        
        # Obtener id_turno
        id_turno = turnos_dict.get(tipo_turno)
        if not id_turno:
            sin_turno += 1
            stats_turnos[tipo_turno] = stats_turnos.get(tipo_turno, 0) + 1
            continue
        
        # Buscar/crear día
        cursor.execute("SELECT id_dia FROM dias WHERE fecha = ?", (fecha_str,))
        d = cursor.fetchone()
        if not d:
            sin_turno += 1
            continue
        id_dia = d[0]
        
        # Crear planificación (v3.0: sin especificar horarios, el trigger los auto-completa)
        cursor.execute("""
            INSERT OR IGNORE INTO planificacion 
            (id_dia, id_turno, cant_residentes_plan, cant_visit)
            VALUES (?, ?, 3, 0)
        """, (id_dia, id_turno))
        
        cursor.execute("""
            SELECT id_plani FROM planificacion 
            WHERE id_dia = ? AND id_turno = ?
        """, (id_dia, id_turno))
        id_plani = cursor.fetchone()[0]
        
        # Insertar convocatoria
        try:
            cursor.execute("""
                INSERT INTO convocatoria 
                (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
                VALUES (?, ?, ?, ?, 'vigente')
            """, (id_plani, id_agente, id_turno, fecha_str))
            insertados += 1
        except sqlite3.IntegrityError:
            # Ya existe (trigger previene duplicados)
            pass
        except Exception as e:
            print_error(f"Error fila {idx}: {e}")
    
    conn.commit()
    
    print_success(f"{insertados} convocatorias insertadas")
    
    # Reporte detallado
    print(f"\n  📋 REPORTE DETALLADO:")
    print(f"     Total filas en Excel: {len(df)}")
    print(f"     ✅ Insertadas: {insertados}")
    print(f"     ❌ NO insertadas: {len(df) - insertados}")
    print(f"        • Filas vacías: {filas_vacias}")
    print(f"        • Sin fecha válida: {sin_fecha}")
    print(f"        • Sin residente válido: {sin_residente}")
    print(f"        • Sin turno válido: {sin_turno}")
    
    if stats_turnos:
        print(f"\n     Turnos no encontrados:")
        for tipo, cant in sorted(stats_turnos.items(), key=lambda x: -x[1]):
            print(f"        • '{tipo}': {cant} registros")

def cargar_asignaciones(conn):
    """Carga asignaciones de dispositivos (menú)"""
    print_step(6, 9, "Cargando asignaciones de dispositivos...")
    
    df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(str(r['NOMBRE Y APELLIDO'])).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025']) and pd.notna(r['NOMBRE Y APELLIDO'])
        and ',' in str(r['NOMBRE Y APELLIDO'])
    }
    
    cursor = conn.cursor()
    
    # Obtener agentes
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    # Obtener dispositivos
    cursor.execute("SELECT id_dispositivo, nombre_dispositivo FROM dispositivos")
    dispositivos = {normalizar(d): i for i, d in cursor.fetchall()}
    
    insertados = 0
    sin_fecha = 0
    sin_dispositivo = 0
    sin_residente = 0
    sin_convocatoria = 0
    filas_vacias = 0
    
    for idx, row in df.iterrows():
        # Verificar fila vacía
        if fila_vacia(row, ['Dia', 'Residente', 'Dispositivo']):
            filas_vacias += 1
            continue
        
        # Validar fecha
        fecha = pd.to_datetime(row.get('Dia'), errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha_str <= '2025-12-31'):
            sin_fecha += 1
            continue
        
        # Validar dispositivo
        dispo_raw = normalizar(row.get('Dispositivo'))
        id_dispositivo = dispositivos.get(dispo_raw)
        if not id_dispositivo:
            sin_dispositivo += 1
            continue
        
        # Validar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        if not apellido or apellido not in agentes:
            sin_residente += 1
            continue
        
        id_agente = agentes[apellido]
        
        # Buscar convocatoria correspondiente
        cursor.execute("""
            SELECT id_convocatoria FROM convocatoria
            WHERE id_agente = ? AND fecha_convocatoria = ? AND estado = 'vigente'
            LIMIT 1
        """, (id_agente, fecha_str))
        
        conv = cursor.fetchone()
        if not conv:
            sin_convocatoria += 1
            continue
        
        id_convocatoria = conv[0]
        
        # Insertar asignación
        try:
            cursor.execute("""
                INSERT INTO menu 
                (id_convocatoria, id_dispositivo, id_agente, fecha_asignacion, orden)
                VALUES (?, ?, ?, ?, 1)
            """, (id_convocatoria, id_dispositivo, id_agente, fecha_str))
            insertados += 1
        except:
            pass
    
    conn.commit()
    
    print_success(f"{insertados} asignaciones insertadas")
    
    print(f"\n  📋 REPORTE DETALLADO:")
    print(f"     Total filas en Excel: {len(df)}")
    print(f"     ✅ Insertadas: {insertados}")
    print(f"     ❌ NO insertadas: {len(df) - insertados}")
    print(f"        • Filas vacías: {filas_vacias}")
    print(f"        • Sin fecha válida: {sin_fecha}")
    print(f"        • Sin dispositivo válido: {sin_dispositivo}")
    print(f"        • Sin residente válido: {sin_residente}")
    print(f"        • Sin convocatoria correspondiente: {sin_convocatoria}")

def cargar_inasistencias(conn):
    """Carga inasistencias"""
    print_step(7, 9, "Cargando inasistencias...")
    
    df = pd.read_excel(EXCEL_CONV, sheet_name='Inasistencias')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(str(r['NOMBRE Y APELLIDO'])).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025']) and pd.notna(r['NOMBRE Y APELLIDO'])
        and ',' in str(r['NOMBRE Y APELLIDO'])
    }
    
    cursor = conn.cursor()
    
    # Obtener agentes
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    insertados = 0
    sin_fecha = 0
    sin_residente = 0
    filas_vacias = 0
    
    for idx, row in df.iterrows():
        # Verificar fila vacía
        if fila_vacia(row, ['Dia', 'Residente']):
            filas_vacias += 1
            continue
        
        # Validar fecha
        fecha = pd.to_datetime(row.get('Dia'), errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha_str <= '2025-12-31'):
            sin_fecha += 1
            continue
        
        # Validar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        if not apellido or apellido not in agentes:
            sin_residente += 1
            continue
        
        id_agente = agentes[apellido]
        
        # Insertar inasistencia
        try:
            cursor.execute("""
                INSERT INTO inasistencias 
                (id_agente, fecha_inasistencia, motivo, observaciones)
                VALUES (?, ?, 'imprevisto', ?)
            """, (id_agente, fecha_str, str(row.get('Observaciones', ''))))
            insertados += 1
        except:
            pass
    
    conn.commit()
    
    print_success(f"{insertados} inasistencias insertadas")
    
    print(f"\n  📋 REPORTE DETALLADO:")
    print(f"     Total filas en Excel: {len(df)}")
    print(f"     ✅ Insertadas: {insertados}")
    print(f"     ❌ NO insertadas: {len(df) - insertados}")
    print(f"        • Filas vacías: {filas_vacias}")
    print(f"        • Sin fecha válida: {sin_fecha}")
    print(f"        • Sin residente válido: {sin_residente}")

def verificar_triggers_saldos(conn):
    """Verifica que los triggers de saldos funcionaron"""
    print_step(8, 9, "Verificando triggers de saldos...")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT id_agente) FROM saldos")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print_success(f"Triggers funcionando ({count} agentes con saldos)")
    else:
        print_warning("No se generaron saldos (verificar triggers)")

def resumen_final(conn):
    """Muestra resumen final de carga"""
    print_step(9, 9, "Resumen final de carga")
    
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("  DATOS CARGADOS EN BASE DE DATOS")
    print("="*70)
    
    # Maestros
    cursor.execute("SELECT COUNT(*) FROM datos_personales")
    residentes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dispositivos")
    dispositivos = cursor.fetchone()[0]
    
    print(f"\n  Maestros:")
    print(f"    • Residentes: {residentes}")
    print(f"    • Dispositivos: {dispositivos}")
    
    # Operativos
    cursor.execute("SELECT COUNT(*) FROM convocatoria")
    convocatorias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM menu")
    menu = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inasistencias")
    inasistencias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM saldos")
    saldos = cursor.fetchone()[0]
    
    print(f"\n  Operativos (año 2025):")
    print(f"    • Convocatorias: {convocatorias}")
    print(f"    • Asignaciones: {menu}")
    print(f"    • Inasistencias: {inasistencias}")
    print(f"    • Saldos: {saldos}")
    
    # Turnos v3.0
    cursor.execute("SELECT COUNT(*) FROM turnos")
    turnos = cursor.fetchone()[0]
    
    print(f"\n  Catálogos:")
    print(f"    • Turnos (DAMA): {turnos}")
    
    # Planificación con horarios
    cursor.execute("SELECT COUNT(*) FROM planificacion WHERE hora_inicio IS NOT NULL")
    plani_horarios = cursor.fetchone()[0]
    
    print(f"\n  Planificación:")
    print(f"    • Con horarios: {plani_horarios}")
    
    print("\n" + "="*70)

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal de carga"""
    print("\n" + "="*70)
    print(f"  {Color.BOLD}CARGA DE DATOS v3.0 - DAMA COMPLIANT{Color.FIN}")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base de datos: {DB_PATH}")
    
    # Verificar archivos
    if not Path(DB_PATH).exists():
        print_error(f"Base de datos no encontrada: {DB_PATH}")
        print("Ejecuta primero: sqlite3 {DB_PATH} < schema_v3_DAMA_compliant.sql")
        return
    
    # Conectar
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Ejecutar pasos
        limpiar_datos(conn)
        cargar_datos_personales(conn)
        generar_dias_y_turnos(conn)
        cargar_dispositivos(conn)
        cargar_convocatorias(conn)
        cargar_asignaciones(conn)
        cargar_inasistencias(conn)
        verificar_triggers_saldos(conn)
        resumen_final(conn)
        
        print(f"\n{Color.VERDE}✅ CARGA COMPLETADA EXITOSAMENTE{Color.FIN}\n")
        
    except Exception as e:
        print_error(f"Error durante la carga: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
