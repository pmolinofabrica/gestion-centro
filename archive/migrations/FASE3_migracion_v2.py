#!/usr/bin/env python3
"""
FASE 3: MIGRACIÓN DE DATOS SQLite → Supabase PostgreSQL (via Pooler)
====================================================================

Migra datos desde SQLite local a Supabase.
Usa connection string URI que funciona correctamente con el pooler.

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

# Construir connection string URI (formato que funciona con pooler)
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
    """Conectar a SQLite local"""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_supabase_conn():
    """Conectar a Supabase usando connection string URI"""
    return psycopg2.connect(CONN_STRING, connect_timeout=15)

# ============================================================================
# FUNCIONES DE MIGRACIÓN
# ============================================================================

def print_step(step, total, text):
    print(f"\n{Color.AZUL}[{step}/{total}]{Color.FIN} {Color.BOLD}{text}{Color.FIN}")

def print_success(text):
    print(f"  {Color.VERDE}✅ {text}{Color.FIN}")

def print_warning(text):
    print(f"  {Color.AMARILLO}⚠️  {text}{Color.FIN}")

def print_error(text):
    print(f"  {Color.ROJO}❌ {text}{Color.FIN}")

def migrar_tabla(sqlite_conn, pg_conn, tabla, query_sqlite, insert_sql, msg):
    """Migra una tabla de SQLite a PostgreSQL"""
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
        data = [tuple(row) for row in rows]
        
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
        print_error(f"Error insertando en PostgreSQL: {e}")
        return 0

def limpiar_tablas(pg_conn):
    """Limpia tablas de Supabase antes de migrar"""
    print_step(1, 8, "Limpiando tablas Supabase...")
    
    cursor = pg_conn.cursor()
    
    # Orden inverso a Foreign Keys
    tablas_limpiar = [
        'menu',
        'certificados', 
        'inasistencias',
        'convocatoria_historial',
        'convocatoria',
        'saldos',
        'capacitaciones_participantes',
        'capacitaciones_dispositivos',
        'capacitaciones',
        'disponibilidad',
        'descansos',
        'cambio_validacion',
        'cambio_transaccion_detalle',
        'cambio_transaccion',
        'planificacion',
        'dias',
        'dispositivos',
        'datos_personales'
    ]
    
    for tabla in tablas_limpiar:
        try:
            cursor.execute(f"DELETE FROM {tabla}")
            deleted = cursor.rowcount
            pg_conn.commit()
            if deleted > 0:
                print(f"     {tabla}: {deleted} eliminados")
        except Exception as e:
            pg_conn.rollback()
            print(f"     {tabla}: (vacía o error)")
    
    print_success("Tablas limpiadas")

def migrar_maestros(sqlite_conn, pg_conn):
    """Migra tablas maestras"""
    print_step(2, 8, "Migrando datos maestros...")
    
    # datos_personales
    query = "SELECT id_agente, nombre, apellido, dni, fecha_nacimiento, email, telefono, domicilio, activo, fecha_alta, fecha_baja FROM datos_personales"
    insert = """
        INSERT INTO datos_personales 
        (id_agente, nombre, apellido, dni, fecha_nacimiento, email, telefono, domicilio, activo, fecha_alta, fecha_baja)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_agente) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'datos_personales', query, insert, "datos_personales")
    
    # dispositivos
    query = "SELECT id_dispositivo, nombre_dispositivo, piso_dispositivo, activo, fecha_creacion FROM dispositivos"
    insert = """
        INSERT INTO dispositivos 
        (id_dispositivo, nombre_dispositivo, piso_dispositivo, activo, fecha_creacion)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id_dispositivo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'dispositivos', query, insert, "dispositivos")
    
    # dias
    query = "SELECT id_dia, fecha, mes, semana, dia, numero_dia_semana, es_feriado, nombre_feriado FROM dias"
    insert = """
        INSERT INTO dias 
        (id_dia, fecha, mes, semana, dia, numero_dia_semana, es_feriado, nombre_feriado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_dia) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'dias', query, insert, "dias")

def migrar_planificacion(sqlite_conn, pg_conn):
    """Migra planificación"""
    print_step(3, 8, "Migrando planificación...")
    
    # Primero verificar columnas disponibles en SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(planificacion)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    # Construir query según columnas disponibles
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
    else:
        # Schema v2.0 - sin columnas de horario
        query = """
            SELECT id_plani, id_dia, id_turno, cant_residentes_plan, cant_visit, plani_notas, fecha_creacion
            FROM planificacion
        """
        insert = """
            INSERT INTO planificacion 
            (id_plani, id_dia, id_turno, cant_residentes_plan, cant_visit, plani_notas, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_plani) DO NOTHING
        """
    
    migrar_tabla(sqlite_conn, pg_conn, 'planificacion', query, insert, "planificacion")

def migrar_convocatorias(sqlite_conn, pg_conn):
    """Migra convocatorias e historial"""
    print_step(4, 8, "Migrando convocatorias...")
    
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
    migrar_tabla(sqlite_conn, pg_conn, 'convocatoria', query, insert, "convocatoria")

def migrar_inasistencias(sqlite_conn, pg_conn):
    """Migra inasistencias y certificados"""
    print_step(5, 8, "Migrando inasistencias...")
    
    # inasistencias
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
    migrar_tabla(sqlite_conn, pg_conn, 'inasistencias', query, insert, "inasistencias")
    
    # certificados
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
    migrar_tabla(sqlite_conn, pg_conn, 'certificados', query, insert, "certificados")

def migrar_menu(sqlite_conn, pg_conn):
    """Migra asignaciones de dispositivos"""
    print_step(6, 8, "Migrando asignaciones (menú)...")
    
    # Verificar columnas de menu
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(menu)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    # Construir query según columnas
    cols_select = ['id_menu', 'id_convocatoria', 'id_dispositivo', 'id_agente', 
                   'fecha_asignacion', 'orden']
    
    if 'acompaña_grupo' in columnas:
        cols_select.append('acompaña_grupo')
    if 'fecha_registro' in columnas:
        cols_select.append('fecha_registro')
    
    query = f"""
        SELECT {', '.join(cols_select)} FROM menu 
        WHERE strftime('%Y', fecha_asignacion) = '{YEAR_TO_MIGRATE}'
    """
    
    placeholders = ', '.join(['%s'] * len(cols_select))
    insert = f"""
        INSERT INTO menu ({', '.join(cols_select)})
        VALUES ({placeholders})
        ON CONFLICT (id_menu) DO NOTHING
    """
    
    migrar_tabla(sqlite_conn, pg_conn, 'menu', query, insert, "menu")

def migrar_saldos(sqlite_conn, pg_conn):
    """Migra saldos"""
    print_step(7, 8, "Migrando saldos...")
    
    query = f"""
        SELECT id_saldo, id_agente, mes, anio, horas_mes, horas_anuales, fecha_actualizacion
        FROM saldos
        WHERE anio = {YEAR_TO_MIGRATE}
    """
    insert = """
        INSERT INTO saldos 
        (id_saldo, id_agente, mes, anio, horas_mes, horas_anuales, fecha_actualizacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_saldo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'saldos', query, insert, "saldos")

def verificar_migracion(pg_conn):
    """Verifica conteos finales"""
    print_step(8, 8, "Verificando migración...")
    
    cursor = pg_conn.cursor()
    
    tablas = [
        'datos_personales', 'dispositivos', 'dias', 'turnos',
        'planificacion', 'convocatoria', 'inasistencias', 
        'certificados', 'menu', 'saldos'
    ]
    
    print("\n📊 Registros en Supabase después de migración:")
    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "⚠️"
        print(f"   {status} {tabla}: {count}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    print(f"\n{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"{Color.BOLD}FASE 3: MIGRACIÓN SQLite → Supabase (via Pooler URI){Color.FIN}")
    print(f"{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Año a migrar: {YEAR_TO_MIGRATE}")
    
    # Verificar configuración
    print(f"\n🔧 Configuración:")
    print(f"   SQLite: {SQLITE_PATH}")
    print(f"   Host: {SUPABASE_HOST}")
    print(f"   Usuario: {SUPABASE_USER}")
    
    if not SUPABASE_PASSWORD:
        print_error("SUPABASE_DB_PASSWORD no configurado en .env")
        sys.exit(1)
    
    # Confirmar
    print(f"\n{Color.AMARILLO}⚠️  Esta migración reemplazará datos en Supabase{Color.FIN}")
    respuesta = input("\n¿Continuar? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Migración cancelada.")
        sys.exit(0)
    
    # Conectar
    print(f"\n🔌 Conectando...")
    try:
        sqlite_conn = get_sqlite_conn()
        print_success("SQLite OK")
        
        pg_conn = get_supabase_conn()
        print_success("Supabase OK (via pooler URI)")
        
    except Exception as e:
        print_error(f"Error de conexión: {e}")
        sys.exit(1)
    
    # Ejecutar migración
    try:
        limpiar_tablas(pg_conn)
        migrar_maestros(sqlite_conn, pg_conn)
        migrar_planificacion(sqlite_conn, pg_conn)
        migrar_convocatorias(sqlite_conn, pg_conn)
        migrar_inasistencias(sqlite_conn, pg_conn)
        migrar_menu(sqlite_conn, pg_conn)
        migrar_saldos(sqlite_conn, pg_conn)
        verificar_migracion(pg_conn)
        
        print(f"\n{Color.VERDE}{'='*70}{Color.FIN}")
        print(f"{Color.VERDE}✅ MIGRACIÓN COMPLETADA EXITOSAMENTE{Color.FIN}")
        print(f"{Color.VERDE}{'='*70}{Color.FIN}")
        
    except Exception as e:
        print_error(f"Error durante migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
