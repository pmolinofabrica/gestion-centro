#!/usr/bin/env python3
"""
FASE 3: MIGRACIÓN DE DATOS SQLite → Supabase PostgreSQL (via Pooler)
====================================================================

Migra SOLO datos del año actual (2025) desde SQLite local a Supabase.
Los datos históricos permanecen en SQLite.

REQUISITOS:
- pip install psycopg2-binary python-dotenv
- Archivo .env con credenciales Supabase (ver instrucciones abajo)
- FASE 1 + FASE 2 ejecutadas en Supabase

IMPORTANTE - USO DE CONNECTION POOLER:
- Host: aws-1-sa-east-1.pooler.supabase.com
- Puerto: 6543 (NO 5432)
- Usuario: postgres.{project-ref}
- Transacciones cortas
- Batches pequeños (200 filas)

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

# Intentar cargar python-dotenv (opcional)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables de entorno del sistema.")

# ============================================================================
# CONFIGURACIÓN - USA VARIABLES DE ENTORNO
# ============================================================================

# SQLite local
SQLITE_PATH = 'data/gestion_rrhh.db'
if not Path(SQLITE_PATH).exists():
    SQLITE_PATH = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'

# Supabase PostgreSQL - Desde .env o variables de entorno
SUPABASE_HOST = os.getenv('SUPABASE_DB_HOST')
SUPABASE_DB = os.getenv('SUPABASE_DB_NAME', 'postgres')
SUPABASE_USER = os.getenv('SUPABASE_DB_USER')
SUPABASE_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')
SUPABASE_PORT = int(os.getenv('SUPABASE_DB_PORT', '6543'))

# Año a migrar
YEAR_TO_MIGRATE = 2025

# Tamaño de batch (ajustado para pooler)
BATCH_SIZE = 200

# ============================================================================
# COLORES PARA OUTPUT
# ============================================================================

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
    if not Path(SQLITE_PATH).exists():
        raise FileNotFoundError(f"❌ No se encuentra: {SQLITE_PATH}")
    
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_supabase_conn():
    """
    Conectar a Supabase PostgreSQL via Connection Pooler
    
    IMPORTANTE: Usa puerto 6543 (pooler), NO 5432 (directo)
    """
    if not SUPABASE_PASSWORD:
        raise ValueError(
            "❌ SUPABASE_DB_PASSWORD no configurado.\n"
            "   Crea archivo .env con tus credenciales (ver README)."
        )
    
    try:
        conn = psycopg2.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            database=SUPABASE_DB,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            sslmode='require',
            connect_timeout=10
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"{Color.ROJO}❌ Error conectando a Supabase:{Color.FIN}")
        print(f"   Host: {SUPABASE_HOST}")
        print(f"   Puerto: {SUPABASE_PORT}")
        print(f"   Usuario: {SUPABASE_USER}")
        print(f"\n   Error: {e}")
        print(f"\n   💡 Verifica:")
        print(f"      1. Archivo .env con credenciales correctas")
        print(f"      2. Conectividad: nc -4 -vz {SUPABASE_HOST} {SUPABASE_PORT}")
        raise

# ============================================================================
# FUNCIONES DE MIGRACIÓN
# ============================================================================

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

def migrar_tabla(sqlite_conn, pg_conn, tabla, query_sqlite, insert_sql, msg):
    """
    Función genérica para migrar una tabla
    
    IMPORTANTE: Usa batches pequeños (200) para el pooler
    """
    print(f"\n  📊 Migrando {msg}...")
    
    # Extraer de SQLite
    try:
        cursor_sqlite = sqlite_conn.cursor()
        cursor_sqlite.execute(query_sqlite)
        rows = cursor_sqlite.fetchall()
        
        if not rows:
            print_warning(f"Sin datos en SQLite para {msg}")
            return 0
        
        print(f"     Encontrados: {len(rows)} registros")
        
    except Exception as e:
        print_error(f"Error extrayendo de SQLite: {e}")
        return 0
    
    # Insertar en PostgreSQL en batches
    try:
        cursor_pg = pg_conn.cursor()
        
        # Convertir Row objects a tuplas
        data = [tuple(row) for row in rows]
        
        # Insertar en batches
        total_insertados = 0
        for i in range(0, len(data), BATCH_SIZE):
            batch = data[i:i + BATCH_SIZE]
            
            # Ejecutar batch
            execute_batch(cursor_pg, insert_sql, batch, page_size=BATCH_SIZE)
            pg_conn.commit()  # Commit por batch
            
            total_insertados += len(batch)
            print(f"     Batch {i//BATCH_SIZE + 1}: {len(batch)} registros")
        
        print_success(f"{total_insertados} registros migrados")
        return total_insertados
        
    except Exception as e:
        pg_conn.rollback()
        print_error(f"Error insertando en PostgreSQL: {e}")
        return 0

def limpiar_tablas(pg_conn):
    """Limpia tablas en orden inverso a FKs"""
    print_step(1, 9, "Limpiando tablas Supabase (solo año 2025)...")
    
    cursor = pg_conn.cursor()
    
    # Orden inverso a Foreign Keys
    tablas = [
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
        'planificacion'
    ]
    
    for tabla in tablas:
        try:
            cursor.execute(f"DELETE FROM {tabla} WHERE EXTRACT(YEAR FROM fecha_creacion) = {YEAR_TO_MIGRATE}")
            deleted = cursor.rowcount
            if deleted > 0:
                print(f"     {tabla}: {deleted} registros eliminados")
        except Exception as e:
            # Algunas tablas no tienen fecha_creacion, eliminar todo
            try:
                cursor.execute(f"DELETE FROM {tabla}")
                deleted = cursor.rowcount
                if deleted > 0:
                    print(f"     {tabla}: {deleted} registros eliminados")
            except:
                pass
    
    pg_conn.commit()
    print_success("Tablas limpiadas")

def migrar_maestros(sqlite_conn, pg_conn):
    """Migra datos maestros (activos)"""
    print_step(2, 9, "Migrando datos maestros...")
    
    # 1. datos_personales (solo activos)
    query = "SELECT * FROM datos_personales WHERE activo = 1"
    insert = """
        INSERT INTO datos_personales 
        (id_agente, nombre, apellido, dni, fecha_nacimiento, email, telefono, 
         domicilio, activo, fecha_alta, fecha_baja)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::boolean, %s, %s)
        ON CONFLICT (id_agente) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'datos_personales', query, insert, "datos_personales")
    
    # 2. dispositivos (solo activos)
    query = "SELECT * FROM dispositivos WHERE activo = 1"
    insert = """
        INSERT INTO dispositivos 
        (id_dispositivo, nombre_dispositivo, piso_dispositivo, activo, fecha_creacion)
        VALUES (%s, %s, %s, %s::boolean, %s)
        ON CONFLICT (id_dispositivo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'dispositivos', query, insert, "dispositivos")
    
    # 3. dias (año actual)
    query = f"SELECT * FROM dias WHERE strftime('%Y', fecha) = '{YEAR_TO_MIGRATE}'"
    insert = """
        INSERT INTO dias 
        (id_dia, fecha, mes, semana, dia, numero_dia_semana, es_feriado, nombre_feriado)
        VALUES (%s, %s, %s, %s, %s, %s, %s::boolean, %s)
        ON CONFLICT (id_dia) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'dias', query, insert, "dias (2025)")
    
    # 4. turnos (adaptable v2/v3)
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(turnos)")
    cols = {row['name'] for row in cursor.fetchall()}
    
    if 'numero_dia_semana' in cols:
        # Origen v2.0 (tiene numero_dia_semana)
        # CORRECCIÓN: Usar COALESCE para evitar errores NOT NULL en Supabase
        query = """
            SELECT 
                id_turno, 
                numero_dia_semana, 
                tipo_turno, 
                COALESCE(hora_inicio, '00:00'), 
                COALESCE(hora_fin, '23:59'), 
                COALESCE(cant_horas, 0),
                activo
            FROM turnos
        """
        insert = """
            INSERT INTO turnos 
            (id_turno, numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s::boolean)
            ON CONFLICT (id_turno) DO UPDATE SET
                tipo_turno = EXCLUDED.tipo_turno,
                hora_inicio = EXCLUDED.hora_inicio,
                hora_fin = EXCLUDED.hora_fin,
                cant_horas = EXCLUDED.cant_horas,
                activo = EXCLUDED.activo
        """
    else:
        # Origen v3.0 (no tiene numero_dia_semana, usa defaults)
        # CORRECCIÓN: Usar COALESCE para evitar errores NOT NULL en Supabase
        query = """
            SELECT 
                id_turno, 
                tipo_turno, 
                COALESCE(hora_inicio_default, '00:00'), 
                COALESCE(hora_fin_default, '23:59'), 
                COALESCE(cant_horas_default, 0),
                activo
            FROM turnos
        """
        insert = """
            INSERT INTO turnos 
            (id_turno, tipo_turno, hora_inicio, hora_fin, cant_horas, activo, numero_dia_semana)
            VALUES (%s, %s, %s, %s, %s, %s::boolean, 0)
            ON CONFLICT (id_turno) DO UPDATE SET
                tipo_turno = EXCLUDED.tipo_turno,
                hora_inicio = EXCLUDED.hora_inicio,
                hora_fin = EXCLUDED.hora_fin,
                cant_horas = EXCLUDED.cant_horas,
                activo = EXCLUDED.activo
        """
    migrar_tabla(sqlite_conn, pg_conn, 'turnos', query, insert, "turnos")

def migrar_planificacion(sqlite_conn, pg_conn):
    """Migra planificación (año actual)"""
    print_step(3, 9, "Migrando planificación...")

    # 1. Detectar columnas en SQLite (Origen)
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(planificacion)")
    sqlite_columns = {row['name'] for row in cursor.fetchall()}
    
    # 2. Detectar columnas en PostgreSQL (Destino)
    cursor_pg = pg_conn.cursor()
    cursor_pg.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'planificacion'")
    pg_columns = {row[0] for row in cursor_pg.fetchall()}
    
    if 'hora_inicio' in sqlite_columns and 'hora_inicio' in pg_columns:
        # Versión 3.0 (12 columnas - con horarios)
        print("     ℹ️  Detectado esquema v3.0 (con horarios)")
        query = f"""
            SELECT 
                p.id_plani, p.id_dia, p.id_turno, p.hora_inicio, p.hora_fin, p.cant_horas,
                p.usa_horario_custom, p.motivo_horario_custom, p.cant_residentes_plan, 
                p.cant_visit, p.plani_notas, p.fecha_creacion
            FROM planificacion p
            JOIN dias d ON p.id_dia = d.id_dia
            WHERE strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
        """
        insert = """
            INSERT INTO planificacion 
            (id_plani, id_dia, id_turno, hora_inicio, hora_fin, cant_horas,
             usa_horario_custom, motivo_horario_custom, cant_residentes_plan, 
             cant_visit, plani_notas, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s::boolean, %s, %s, %s, %s, %s)
            ON CONFLICT (id_plani) DO NOTHING
        """
    else:
        # Versión 2.0 (7 columnas - simple)
        if 'hora_inicio' in sqlite_columns:
            print("     ⚠️  SQLite tiene v3.0 pero Supabase es v2.0. Se omitirán horarios para evitar error.")
        else:
            print("     ℹ️  Detectado esquema v2.0 (sin horarios)")
            
        query = f"""
            SELECT 
                p.id_plani, p.id_dia, p.id_turno, p.cant_residentes_plan, 
                p.cant_visit, p.plani_notas, p.fecha_creacion
            FROM planificacion p
            JOIN dias d ON p.id_dia = d.id_dia
            WHERE strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
        """
        insert = """
            INSERT INTO planificacion 
            (id_plani, id_dia, id_turno, cant_residentes_plan, 
             cant_visit, plani_notas, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_plani) DO NOTHING
        """
    
    migrar_tabla(sqlite_conn, pg_conn, 'planificacion', query, insert, "planificacion")

def migrar_convocatorias(sqlite_conn, pg_conn):
    """Migra convocatorias + historial"""
    print_step(4, 9, "Migrando convocatorias...")
    
    # 1. convocatoria
    # CORRECCIÓN: Selección explícita de columnas
    query = f"""
        SELECT 
            c.id_convocatoria, c.id_plani, c.id_agente, c.id_turno, c.fecha_convocatoria,
            c.estado, c.id_convocatoria_origen, c.fecha_registro, c.fecha_modificacion,
            c.motivo_cambio, c.usuario_modificacion
        FROM convocatoria c
        JOIN planificacion p ON c.id_plani = p.id_plani
        JOIN dias d ON p.id_dia = d.id_dia
        WHERE strftime('%Y', c.fecha_convocatoria) = '{YEAR_TO_MIGRATE}'
        AND strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
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
    
    # 2. convocatoria_historial
    query = """
        SELECT h.* FROM convocatoria_historial h
        JOIN convocatoria c ON h.id_convocatoria = c.id_convocatoria
        JOIN planificacion p ON c.id_plani = p.id_plani
        JOIN dias d ON p.id_dia = d.id_dia
        WHERE strftime('%Y', c.fecha_convocatoria) = ?
        AND strftime('%Y', d.fecha) = ?
    """
    
    cursor = sqlite_conn.cursor()
    cursor.execute(query, (str(YEAR_TO_MIGRATE), str(YEAR_TO_MIGRATE)))
    rows = cursor.fetchall()
    
    if rows:
        insert = """
            INSERT INTO convocatoria_historial 
            (id_hist, id_convocatoria, id_agente_anterior, id_agente_nuevo,
             fecha_cambio, tipo_cambio, motivo, id_transaccion_cambio, usuario_responsable)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_hist) DO NOTHING
        """
        
        cursor_pg = pg_conn.cursor()
        data = [tuple(row) for row in rows]
        execute_batch(cursor_pg, insert, data, page_size=BATCH_SIZE)
        pg_conn.commit()
        print_success(f"convocatoria_historial: {len(data)} registros")

def migrar_inasistencias(sqlite_conn, pg_conn):
    """Migra inasistencias + certificados"""
    print_step(5, 9, "Migrando inasistencias...")
    
    # 1. inasistencias
    query = f"SELECT * FROM inasistencias WHERE strftime('%Y', fecha_inasistencia) = '{YEAR_TO_MIGRATE}'"
    insert = """
        INSERT INTO inasistencias 
        (id_inasistencia, id_agente, fecha_aviso, fecha_inasistencia, motivo,
         requiere_certificado, estado, observaciones, fecha_actualizacion_estado,
         usuario_actualizo_estado)
        VALUES (%s, %s, %s, %s, %s, %s::boolean, %s, %s, %s, %s)
        ON CONFLICT (id_inasistencia) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'inasistencias', query, insert, "inasistencias")
    
    # 2. certificados
    query = f"""
        SELECT c.* FROM certificados c
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
    print_step(6, 9, "Migrando asignaciones (menú)...")
    
    # Filtrar solo menús cuya convocatoria existe y corresponde al año migrado
    query = f"""
        SELECT 
            m.id_menu, m.id_convocatoria, m.id_dispositivo, m.id_agente, m.fecha_asignacion,
            m.orden, m.acompaña_grupo, m.fecha_registro
        FROM menu m
        JOIN convocatoria c ON m.id_convocatoria = c.id_convocatoria
        JOIN planificacion p ON c.id_plani = p.id_plani
        JOIN dias d ON p.id_dia = d.id_dia
        WHERE strftime('%Y', m.fecha_asignacion) = '{YEAR_TO_MIGRATE}'
        AND strftime('%Y', c.fecha_convocatoria) = '{YEAR_TO_MIGRATE}'
        AND strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO menu 
        (id_menu, id_convocatoria, id_dispositivo, id_agente, fecha_asignacion,
         orden, acompaña_grupo, fecha_registro)
        VALUES (%s, %s, %s, %s, %s, %s, %s::boolean, %s)
        ON CONFLICT (id_menu) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'menu', query, insert, "menu")

def migrar_capacitaciones(sqlite_conn, pg_conn):
    """Migra capacitaciones completas"""
    print_step(7, 9, "Migrando capacitaciones...")
    
    # 1. capacitaciones
    query = f"""
        SELECT c.* FROM capacitaciones c
        JOIN dias d ON c.id_dia = d.id_dia
        WHERE strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO capacitaciones 
        (id_cap, id_dia, coordinador_cap, tema, grupo, observaciones, fecha_registro)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_cap) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'capacitaciones', query, insert, "capacitaciones")
    
    # 2. capacitaciones_dispositivos
    query = f"""
        SELECT cd.* FROM capacitaciones_dispositivos cd
        JOIN capacitaciones c ON cd.id_cap = c.id_cap
        JOIN dias d ON c.id_dia = d.id_dia
        WHERE strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO capacitaciones_dispositivos 
        (id_cap_dispo, id_cap, id_dispositivo, orden)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id_cap_dispo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'capacitaciones_dispositivos', 
                 query, insert, "capacitaciones_dispositivos")
    
    # 3. capacitaciones_participantes
    query = f"""
        SELECT cp.* FROM capacitaciones_participantes cp
        JOIN capacitaciones c ON cp.id_cap = c.id_cap
        JOIN dias d ON c.id_dia = d.id_dia
        WHERE strftime('%Y', d.fecha) = '{YEAR_TO_MIGRATE}'
    """
    insert = """
        INSERT INTO capacitaciones_participantes 
        (id_participante, id_cap, id_agente, fecha_inscripcion, asistio,
         aprobado, calificacion, observaciones, fecha_certificado)
        VALUES (%s, %s, %s, %s, %s::boolean, %s::boolean, %s, %s, %s)
        ON CONFLICT (id_participante) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'capacitaciones_participantes',
                 query, insert, "capacitaciones_participantes")

def migrar_descansos(sqlite_conn, pg_conn):
    """Migra descansos + disponibilidad"""
    print_step(8, 9, "Migrando descansos...")
    
    # 1. descansos
    query = f"SELECT * FROM descansos WHERE mes_solicitado >= 1 AND mes_solicitado <= 12"
    insert = """
        INSERT INTO descansos 
        (id_desc, id_agente, dia_solicitado, mes_solicitado, estado,
         fecha_solicitud, fecha_respuesta, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_desc) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'descansos', query, insert, "descansos")
    
    # 2. disponibilidad (toda, sin filtro de año)
    query = "SELECT * FROM disponibilidad"
    insert = """
        INSERT INTO disponibilidad 
        (id_dispo, id_agente, id_turno, estado, prioridad, fecha_declaracion)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_dispo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'disponibilidad', query, insert, "disponibilidad")

def migrar_saldos(sqlite_conn, pg_conn):
    """Migra saldos (año actual)"""
    print_step(9, 9, "Migrando saldos...")
    
    query = f"SELECT * FROM saldos WHERE anio = {YEAR_TO_MIGRATE}"
    insert = """
        INSERT INTO saldos 
        (id_saldo, id_agente, mes, anio, horas_mes, horas_anuales, fecha_actualizacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_saldo) DO NOTHING
    """
    migrar_tabla(sqlite_conn, pg_conn, 'saldos', query, insert, "saldos")

def verificar_migracion(pg_conn):
    """Verifica conteos finales"""
    print(f"\n{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"{Color.BOLD}VERIFICACIÓN DE MIGRACIÓN{Color.FIN}")
    print(f"{Color.AZUL}{'='*70}{Color.FIN}")
    
    cursor = pg_conn.cursor()
    
    tablas = [
        'datos_personales',
        'dispositivos',
        'dias',
        'planificacion',
        'convocatoria',
        'inasistencias',
        'certificados',
        'menu',
        'capacitaciones',
        'saldos'
    ]
    
    print("\n📊 Registros en Supabase:")
    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cursor.fetchone()[0]
        print(f"   • {tabla}: {count}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta la migración completa"""
    print(f"\n{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"{Color.BOLD}MIGRACIÓN DATOS SQLite → Supabase PostgreSQL (via Pooler){Color.FIN}")
    print(f"{Color.AZUL}{'='*70}{Color.FIN}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Año a migrar: {YEAR_TO_MIGRATE}")
    print(f"Batch size: {BATCH_SIZE}")
    
    # Verificar configuración
    print(f"\n🔧 Configuración:")
    print(f"   SQLite: {SQLITE_PATH}")
    print(f"   Supabase Host: {SUPABASE_HOST}")
    print(f"   Supabase Port: {SUPABASE_PORT}")
    print(f"   Supabase User: {SUPABASE_USER}")
    print(f"   Password: {'***configurado***' if SUPABASE_PASSWORD else '❌ NO CONFIGURADO'}")
    
    if not SUPABASE_PASSWORD:
        print(f"\n{Color.ROJO}{'='*70}{Color.FIN}")
        print(f"{Color.ROJO}❌ ERROR: SUPABASE_DB_PASSWORD no configurado{Color.FIN}")
        print(f"{Color.ROJO}{'='*70}{Color.FIN}")
        print(f"\n📝 Instrucciones:")
        print(f"   1. Crea archivo .env en la raíz del proyecto:")
        print(f"      SUPABASE_DB_HOST=aws-1-sa-east-1.pooler.supabase.com")
        print(f"      SUPABASE_DB_PORT=6543")
        print(f"      SUPABASE_DB_NAME=postgres")
        print(f"      SUPABASE_DB_USER=postgres.zgzqeusbpobrwanvktyz")
        print(f"      SUPABASE_DB_PASSWORD=tu_password_real")
        print(f"\n   2. O exporta variables de entorno:")
        print(f"      export SUPABASE_DB_PASSWORD='tu_password'")
        print(f"\n   3. Reinstala python-dotenv si es necesario:")
        print(f"      pip install python-dotenv")
        sys.exit(1)
    
    # Confirmar
    print(f"\n{Color.AMARILLO}⚠️  ADVERTENCIA:{Color.FIN}")
    print(f"   Esta migración eliminará datos del año {YEAR_TO_MIGRATE} en Supabase")
    print(f"   y los reemplazará con los datos de SQLite local.")
    
    respuesta = input(f"\n¿Continuar? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Migración cancelada.")
        sys.exit(0)
    
    # Conectar
    print(f"\n🔌 Conectando a bases de datos...")
    try:
        sqlite_conn = get_sqlite_conn()
        print_success("Conectado a SQLite local")
    except Exception as e:
        print_error(f"Error con SQLite: {e}")
        sys.exit(1)
    
    try:
        pg_conn = get_supabase_conn()
        print_success("Conectado a Supabase PostgreSQL (via pooler)")
    except Exception as e:
        print_error(f"Error con Supabase: {e}")
        sys.exit(1)
    
    # Ejecutar migración
    try:
        limpiar_tablas(pg_conn)
        migrar_maestros(sqlite_conn, pg_conn)
        migrar_planificacion(sqlite_conn, pg_conn)
        migrar_convocatorias(sqlite_conn, pg_conn)
        migrar_inasistencias(sqlite_conn, pg_conn)
        migrar_menu(sqlite_conn, pg_conn)
        migrar_capacitaciones(sqlite_conn, pg_conn)
        migrar_descansos(sqlite_conn, pg_conn)
        migrar_saldos(sqlite_conn, pg_conn)
        
        verificar_migracion(pg_conn)
        
        print(f"\n{Color.VERDE}{'='*70}{Color.FIN}")
        print(f"{Color.VERDE}{Color.BOLD}✅ MIGRACIÓN COMPLETADA EXITOSAMENTE{Color.FIN}")
        print(f"{Color.VERDE}{'='*70}{Color.FIN}")
        
    except Exception as e:
        print(f"\n{Color.ROJO}{'='*70}{Color.FIN}")
        print(f"{Color.ROJO}❌ ERROR DURANTE LA MIGRACIÓN{Color.FIN}")
        print(f"{Color.ROJO}{'='*70}{Color.FIN}")
        print(f"\n{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
