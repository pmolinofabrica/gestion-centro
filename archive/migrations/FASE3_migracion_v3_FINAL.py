#!/usr/bin/env python3
"""
FASE 3: MIGRACIÓN DE DATOS SQLite → Supabase PostgreSQL (CORREGIDO)
====================================================================

Corrige:
- Conversión de booleanos (SQLite 0/1 → PostgreSQL true/false)
- Orden correcto de tablas para respetar Foreign Keys

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
import sys
import os
from datetime import datetime
from pathlib import Path

# Cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️  python-dotenv no instalado")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SQLITE_PATH = 'data/gestion_rrhh.db'

# Connection string URI
SUPABASE_USER = os.getenv('SUPABASE_DB_USER')
SUPABASE_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')
SUPABASE_HOST = os.getenv('SUPABASE_DB_HOST')
SUPABASE_PORT = os.getenv('SUPABASE_DB_PORT', '6543')
SUPABASE_DB = os.getenv('SUPABASE_DB_NAME', 'postgres')

CONN_STRING = f"postgresql://{SUPABASE_USER}:{SUPABASE_PASSWORD}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}?sslmode=require"

YEAR_TO_MIGRATE = 2025
BATCH_SIZE = 200

# Colores
class Color:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    FIN = '\033[0m'
    BOLD = '\033[1m'

# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================

def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_supabase_conn():
    return psycopg2.connect(CONN_STRING, connect_timeout=15)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def print_step(step, total, text):
    print(f"\n{Color.AZUL}[{step}/{total}]{Color.FIN} {Color.BOLD}{text}{Color.FIN}")

def print_success(text):
    print(f"  {Color.VERDE}✅ {text}{Color.FIN}")

def print_warning(text):
    print(f"  {Color.AMARILLO}⚠️  {text}{Color.FIN}")

def print_error(text):
    print(f"  {Color.ROJO}❌ {text}{Color.FIN}")

def convert_bool(value):
    """Convierte 0/1 de SQLite a True/False para PostgreSQL"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return bool(value)

def convert_row(row, bool_columns):
    """Convierte una fila, transformando columnas booleanas"""
    result = list(row)
    for idx in bool_columns:
        if idx < len(result):
            result[idx] = convert_bool(result[idx])
    return tuple(result)

def migrar_tabla_con_bool(sqlite_conn, pg_conn, query_sqlite, insert_sql, msg, bool_indices=[]):
    """Migra una tabla convirtiendo booleanos"""
    print(f"\n  📊 Migrando {msg}...")
    
    try:
        cursor_sqlite = sqlite_conn.cursor()
        cursor_sqlite.execute(query_sqlite)
        rows = cursor_sqlite.fetchall()
        
        if not rows:
            print_warning(f"Sin datos para {msg}")
            return 0
        
        print(f"     Encontrados: {len(rows)} registros")
        
    except Exception as e:
        print_error(f"Error extrayendo de SQLite: {e}")
        return 0
    
    try:
        cursor_pg = pg_conn.cursor()
        
        # Convertir filas (booleanos y a tuplas)
        if bool_indices:
            data = [convert_row(tuple(row), bool_indices) for row in rows]
        else:
            data = [tuple(row) for row in rows]
        
        # Insertar en batches
        total_insertados = 0
        for i in range(0, len(data), BATCH_SIZE):
            batch = data[i:i + BATCH_SIZE]
            execute_batch(cursor_pg, insert_sql, batch, page_size=BATCH_SIZE)
            pg_conn.commit()
            total_insertados += len(batch)
        
        print_success(f"{total_insertados} registros migrados")
        return total_insertados
        
    except Exception as e:
        pg_conn.rollback()
        print_error(f"Error insertando: {e}")
        return 0

# ============================================================================
# FUNCIONES DE MIGRACIÓN
# ============================================================================

def limpiar_tablas(pg_conn):
    """Limpia tablas de Supabase"""
    print_step(1, 8, "Limpiando tablas Supabase...")
    
    cursor = pg_conn.cursor()
    
    # Orden inverso a FKs
    tablas = [
        'menu', 'certificados', 'inasistencias',
        'convocatoria_historial', 'convocatoria', 'saldos',
        'capacitaciones_participantes', 'capacitaciones_dispositivos',
        'capacitaciones', 'disponibilidad', 'descansos',
        'cambio_validacion', 'cambio_transaccion_detalle',
        'cambio_transaccion', 'planificacion', 'dias',
        'dispositivos', 'datos_personales'
    ]
    
    for tabla in tablas:
        try:
            cursor.execute(f"DELETE FROM {tabla}")
            deleted = cursor.rowcount
            pg_conn.commit()
            if deleted > 0:
                print(f"     {tabla}: {deleted} eliminados")
        except Exception as e:
            pg_conn.rollback()
    
    print_success("Tablas limpiadas")

def migrar_datos_personales(sqlite_conn, pg_conn):
    """Migra datos_personales con conversión de booleanos"""
    query = """
        SELECT id_agente, nombre, apellido, dni, fecha_nacimiento, 
               email, telefono, domicilio, activo, fecha_alta, fecha_baja
        FROM datos_personales
    """
    insert = """
        INSERT INTO datos_personales 
        (id_agente, nombre, apellido, dni, fecha_nacimiento, 
         email, telefono, domicilio, activo, fecha_alta, fecha_baja)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_agente) DO NOTHING
    """
    # activo está en índice 8
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "datos_personales", bool_indices=[8])

def migrar_dispositivos(sqlite_conn, pg_conn):
    """Migra dispositivos"""
    query = """
        SELECT id_dispositivo, nombre_dispositivo, piso_dispositivo, 
               activo, fecha_creacion
        FROM dispositivos
    """
    insert = """
        INSERT INTO dispositivos 
        (id_dispositivo, nombre_dispositivo, piso_dispositivo, activo, fecha_creacion)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id_dispositivo) DO NOTHING
    """
    # activo está en índice 3
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "dispositivos", bool_indices=[3])

def migrar_dias(sqlite_conn, pg_conn):
    """Migra dias"""
    query = """
        SELECT id_dia, fecha, mes, semana, dia, numero_dia_semana, 
               es_feriado, nombre_feriado
        FROM dias
    """
    insert = """
        INSERT INTO dias 
        (id_dia, fecha, mes, semana, dia, numero_dia_semana, es_feriado, nombre_feriado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_dia) DO NOTHING
    """
    # es_feriado está en índice 6
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "dias", bool_indices=[6])

def migrar_planificacion(sqlite_conn, pg_conn):
    """Migra planificación"""
    # Verificar columnas
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(planificacion)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if 'hora_inicio' in columnas:
        # Schema v3.0
        query = """
            SELECT id_plani, id_dia, id_turno, hora_inicio, hora_fin, cant_horas,
                   usa_horario_custom, motivo_horario_custom, cant_residentes_plan, 
                   cant_visit, plani_notas, fecha_creacion
            FROM planificacion
        """
        insert = """
            INSERT INTO planificacion 
            (id_plani, id_dia, id_turno, hora_inicio, hora_fin, cant_horas,
             usa_horario_custom, motivo_horario_custom, cant_residentes_plan,
             cant_visit, plani_notas, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_plani) DO NOTHING
        """
        # usa_horario_custom está en índice 6
        migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "planificacion", bool_indices=[6])
    else:
        # Schema v2.0
        query = """
            SELECT id_plani, id_dia, id_turno, cant_residentes_plan, 
                   cant_visit, plani_notas, fecha_creacion
            FROM planificacion
        """
        insert = """
            INSERT INTO planificacion 
            (id_plani, id_dia, id_turno, cant_residentes_plan, 
             cant_visit, plani_notas, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_plani) DO NOTHING
        """
        migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "planificacion")

def migrar_convocatorias(sqlite_conn, pg_conn):
    """Migra convocatorias"""
    query = f"""
        SELECT id_convocatoria, id_plani, id_agente, id_turno, fecha_convocatoria,
               estado, id_convocatoria_origen, fecha_registro, fecha_modificacion,
               motivo_cambio, usuario_modificacion
        FROM convocatoria
        WHERE strftime('%Y', fecha_convocatoria) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO convocatoria 
        (id_convocatoria, id_plani, id_agente, id_turno, fecha_convocatoria,
         estado, id_convocatoria_origen, fecha_registro, fecha_modificacion,
         motivo_cambio, usuario_modificacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_convocatoria) DO NOTHING
    """
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "convocatoria")

def migrar_inasistencias(sqlite_conn, pg_conn):
    """Migra inasistencias"""
    query = f"""
        SELECT id_inasistencia, id_agente, fecha_aviso, fecha_inasistencia,
               motivo, requiere_certificado, estado, observaciones,
               fecha_actualizacion_estado, usuario_actualizo_estado
        FROM inasistencias
        WHERE strftime('%Y', fecha_inasistencia) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO inasistencias 
        (id_inasistencia, id_agente, fecha_aviso, fecha_inasistencia,
         motivo, requiere_certificado, estado, observaciones,
         fecha_actualizacion_estado, usuario_actualizo_estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_inasistencia) DO NOTHING
    """
    # requiere_certificado está en índice 5
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "inasistencias", bool_indices=[5])

def migrar_certificados(sqlite_conn, pg_conn):
    """Migra certificados"""
    query = f"""
        SELECT c.id_certificado, c.id_inasistencia, c.id_agente, 
               c.fecha_entrega_certificado, c.fecha_inasistencia_justifica,
               c.tipo_certificado, c.estado_certificado, c.observaciones,
               c.motivo_rechazo, c.fecha_revision, c.usuario_reviso
        FROM certificados c
        JOIN inasistencias i ON c.id_inasistencia = i.id_inasistencia
        WHERE strftime('%Y', i.fecha_inasistencia) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO certificados 
        (id_certificado, id_inasistencia, id_agente, fecha_entrega_certificado,
         fecha_inasistencia_justifica, tipo_certificado, estado_certificado,
         observaciones, motivo_rechazo, fecha_revision, usuario_reviso)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_certificado) DO NOTHING
    """
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "certificados")

def migrar_menu(sqlite_conn, pg_conn):
    """Migra asignaciones de menú"""
    # Verificar columnas
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(menu)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    has_acompana = 'acompaña_grupo' in columnas
    has_fecha_reg = 'fecha_registro' in columnas
    
    # Construir query dinámicamente
    cols = ['id_menu', 'id_convocatoria', 'id_dispositivo', 'id_agente', 
            'fecha_asignacion', 'orden']
    bool_idx = []
    
    if has_acompana:
        cols.append('acompaña_grupo')
        bool_idx.append(6)  # índice de acompaña_grupo
    if has_fecha_reg:
        cols.append('fecha_registro')
    
    query = f"""
        SELECT {', '.join(cols)} FROM menu 
        WHERE strftime('%Y', fecha_asignacion) = '{YEAR_TO_MIGRATE}'
    """
    
    placeholders = ', '.join(['%s'] * len(cols))
    insert = f"""
        INSERT INTO menu ({', '.join(cols)})
        VALUES ({placeholders})
        ON CONFLICT (id_menu) DO NOTHING
    """
    
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "menu", bool_indices=bool_idx)

def migrar_saldos(sqlite_conn, pg_conn):
    """Migra saldos"""
    query = f"""
        SELECT id_saldo, id_agente, mes, anio, horas_mes, 
               horas_anuales, fecha_actualizacion
        FROM saldos
        WHERE anio = {YEAR_TO_MIGRATE}
    """
    insert = """
        INSERT INTO saldos 
        (id_saldo, id_agente, mes, anio, horas_mes, horas_anuales, fecha_actualizacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_saldo) DO NOTHING
    """
    migrar_tabla_con_bool(sqlite_conn, pg_conn, query, insert, "saldos")

def verificar_migracion(pg_conn):
    """Verifica conteos finales"""
    print_step(8, 8, "Verificando migración...")
    
    cursor = pg_conn.cursor()
    
    tablas = [
        ('datos_personales', 35),
        ('dispositivos', 37),
        ('dias', 184),
        ('turnos', 7),
        ('planificacion', 202),
        ('convocatoria', 2850),
        ('inasistencias', 304),
        ('menu', 1776),
        ('saldos', 201)
    ]
    
    print("\n📊 Registros en Supabase:")
    total_ok = 0
    for tabla, esperado in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cursor.fetchone()[0]
        if count >= esperado * 0.9:  # 90% tolerancia
            status = f"{Color.VERDE}✅{Color.FIN}"
            total_ok += 1
        elif count > 0:
            status = f"{Color.AMARILLO}⚠️{Color.FIN}"
        else:
            status = f"{Color.ROJO}❌{Color.FIN}"
        print(f"   {status} {tabla}: {count} (esperado: ~{esperado})")
    
    return total_ok

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    print(f"\n{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"{Color.BOLD}FASE 3: MIGRACIÓN SQLite → Supabase (CORREGIDO){Color.FIN}")
    print(f"{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Año a migrar: {YEAR_TO_MIGRATE}")
    
    print(f"\n🔧 Configuración:")
    print(f"   SQLite: {SQLITE_PATH}")
    print(f"   Host: {SUPABASE_HOST}")
    print(f"   Usuario: {SUPABASE_USER}")
    
    if not SUPABASE_PASSWORD:
        print_error("SUPABASE_DB_PASSWORD no configurado")
        sys.exit(1)
    
    print(f"\n{Color.AMARILLO}⚠️  Esta migración reemplazará datos en Supabase{Color.FIN}")
    respuesta = input("\n¿Continuar? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Migración cancelada.")
        sys.exit(0)
    
    print(f"\n🔌 Conectando...")
    try:
        sqlite_conn = get_sqlite_conn()
        print_success("SQLite OK")
        
        pg_conn = get_supabase_conn()
        print_success("Supabase OK")
        
    except Exception as e:
        print_error(f"Error de conexión: {e}")
        sys.exit(1)
    
    try:
        # 1. Limpiar
        limpiar_tablas(pg_conn)
        
        # 2. Migrar maestros (orden importante para FKs)
        print_step(2, 8, "Migrando datos maestros...")
        migrar_datos_personales(sqlite_conn, pg_conn)
        migrar_dispositivos(sqlite_conn, pg_conn)
        migrar_dias(sqlite_conn, pg_conn)
        
        # 3. Planificación (depende de dias y turnos)
        print_step(3, 8, "Migrando planificación...")
        migrar_planificacion(sqlite_conn, pg_conn)
        
        # 4. Convocatorias (depende de planificacion, datos_personales, turnos)
        print_step(4, 8, "Migrando convocatorias...")
        migrar_convocatorias(sqlite_conn, pg_conn)
        
        # 5. Inasistencias (depende de datos_personales)
        print_step(5, 8, "Migrando inasistencias...")
        migrar_inasistencias(sqlite_conn, pg_conn)
        migrar_certificados(sqlite_conn, pg_conn)
        
        # 6. Menu (depende de convocatoria, dispositivos, datos_personales)
        print_step(6, 8, "Migrando menú...")
        migrar_menu(sqlite_conn, pg_conn)
        
        # 7. Saldos (depende de datos_personales)
        print_step(7, 8, "Migrando saldos...")
        migrar_saldos(sqlite_conn, pg_conn)
        
        # 8. Verificar
        total_ok = verificar_migracion(pg_conn)
        
        if total_ok >= 7:
            print(f"\n{Color.VERDE}{'='*70}{Color.FIN}")
            print(f"{Color.VERDE}✅ MIGRACIÓN COMPLETADA EXITOSAMENTE ({total_ok}/9 tablas OK){Color.FIN}")
            print(f"{Color.VERDE}{'='*70}{Color.FIN}")
        else:
            print(f"\n{Color.AMARILLO}{'='*70}{Color.FIN}")
            print(f"{Color.AMARILLO}⚠️  MIGRACIÓN PARCIAL ({total_ok}/9 tablas OK){Color.FIN}")
            print(f"{Color.AMARILLO}{'='*70}{Color.FIN}")
        
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
