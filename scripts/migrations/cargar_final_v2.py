#!/usr/bin/env python3
"""
SCRIPT DE CARGA FINAL v2.2 (COMPLETO + REPORTE DETALLADO)
==========================================================

Incluye:
- Normalización centralizada
- Carga completa: dispositivos, convocatorias, menu, inasistencias
- Reporte detallado de registros NO cargados (diferenciando datos vs nulos)

Archivos:
- Convocatorias y Menu: data/conv.xlsx
- Datos personales e Inasistencias: data/global.xlsx
- Equivalencias: data/equivalencias.xlsx
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import sys
import unicodedata

# ==========================
# CONFIGURACIÓN
# ==========================
DB_PATH = 'data/gestion_rrhh.db'
EXCEL_CONV = 'data/conv.xlsx'
EXCEL_GLOBAL = 'data/global.xlsx'
EXCEL_EQUIVALENCIAS = 'data/equivalencias.xlsx'

# Variables globales para reporte
REPORTE = {
    'convocatorias': {'total': 0, 'insertadas': 0, 'sin_fecha': 0, 'sin_residente': 0, 'sin_turno': 0, 'filas_vacias': 0},
    'menu': {'total': 0, 'insertadas': 0, 'sin_fecha': 0, 'sin_dispositivo': 0, 'sin_residente': 0, 'sin_convocatoria': 0, 'filas_vacias': 0},
    'inasistencias': {'total': 0, 'insertadas': 0, 'sin_fecha': 0, 'sin_residente': 0, 'fuera_rango': 0, 'filas_vacias': 0}
}

# ==========================
# UTILIDADES
# ==========================

def normalizar(texto: str) -> str:
    """Normaliza texto: lowercase, sin acentos, trim"""
    if texto is None:
        return ''
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto


def resolver_agente(residente: str, agentes: dict):
    """Resuelve agente por apellido (soporta apellidos compuestos)"""
    if not residente:
        return None

    texto = normalizar(residente)

    # Caso "Apellido, Nombre"
    if ',' in texto:
        apellido = texto.split(',')[0].strip()
        return agentes.get(apellido)

    # Caso "Apellido Nombre"
    tokens = texto.split()
    if not tokens:
        return None

    # 1) Apellido compuesto completo
    apellido_compuesto = ' '.join(tokens[:-1])
    if apellido_compuesto in agentes:
        return agentes[apellido_compuesto]

    # 2) Primer token
    return agentes.get(tokens[0])


def fila_vacia(row, columnas_clave):
    """Verifica si una fila está completamente vacía en columnas clave"""
    for col in columnas_clave:
        if col in row and pd.notna(row[col]) and str(row[col]).strip() != '':
            return False
    return True


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step, total, text):
    print(f"\n[{step}/{total}] {text}")

# ==========================
# BASE DE DATOS
# ==========================

def activar_foreign_keys(conn):
    """Activa Foreign Keys en SQLite"""
    conn.execute("PRAGMA foreign_keys = ON")


def limpiar_base_datos(conn):
    """Limpia todas las tablas antes de cargar"""
    print_step(1, 9, "Limpiando datos previos...")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    for tabla in [
        'menu', 'inasistencias', 'convocatoria', 'planificacion',
        'saldos', 'disponibilidad', 'dispositivos',
        'datos_personales', 'turnos', 'dias'
    ]:
        cursor.execute(f"DELETE FROM {tabla}")
    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON")
    print("  ✅ Base de datos limpiada")

# ==========================
# CARGAS
# ==========================

def cargar_datos_personales(conn):
    """Carga residentes desde global.xlsx"""
    print_step(2, 9, "Cargando datos personales...")
    df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Datos personales')
    cursor = conn.cursor()
    insertados = 0

    for _, row in df.iterrows():
        nombre = row.get('Nombre')
        apellido = row.get('Apellido')
        if pd.isna(nombre) or pd.isna(apellido):
            continue

        nombre = str(nombre).strip()
        apellido = str(apellido).strip()
        dni = str(row.get('DNI', '00000000')).strip()
        email = row.get('MAIL')
        if pd.isna(email) or not str(email).strip():
            email = f"{normalizar(nombre)}.{normalizar(apellido)}@ejemplo.com"

        try:
            cursor.execute(
                """
                INSERT INTO datos_personales
                (nombre, apellido, dni, fecha_nacimiento, email, activo)
                VALUES (?, ?, ?, '1990-01-01', ?, 1)
                """,
                (nombre, apellido, dni, email)
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    print(f"  ✅ {insertados} residentes cargados")


def cargar_dias_y_turnos(conn):
    """Genera días y turnos para jul-dic 2025"""
    print_step(3, 9, "Generando días y turnos...")
    cursor = conn.cursor()

    start_date = date(2025, 7, 1)
    end_date = date(2025, 12, 31)
    current = start_date
    dias = 0

    while current <= end_date:
        try:
            cursor.execute(
                """
                INSERT INTO dias (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    current.isoformat(),
                    current.month,
                    current.isocalendar()[1],
                    current.day,
                    current.weekday(),
                ),
            )
            dias += 1
        except sqlite3.IntegrityError:
            pass
        current += timedelta(days=1)

    turnos = [
        (1, 'mañana'), (1, 'tarde'), (1, 'capacitacion'),
        (2, 'mañana'), (2, 'tarde'), (2, 'capacitacion'),
        (3, 'mañana'), (3, 'tarde'), (3, 'capacitacion'),
        (4, 'mañana'), (4, 'tarde'), (4, 'capacitacion'),
        (5, 'mañana'), (5, 'tarde'), (5, 'capacitacion'),
        (6, 'apertura_publico'), (6, 'capacitacion'),
        (0, 'descanso'),
    ]

    for dia, tipo in turnos:
        try:
            cursor.execute(
                """
                INSERT INTO turnos
                (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas, activo)
                VALUES (?, ?, '09:00', '13:00', 4.0, 1)
                """,
                (dia, tipo),
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    print(f"  ✅ {dias} días generados")
    print(f"  ✅ {len(turnos)} turnos creados")


def cargar_dispositivos(conn):
    """Carga dispositivos únicos desde Menu"""
    print_step(4, 9, "Cargando dispositivos...")
    df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
    
    dispositivos_unicos = df['Dispositivo'].dropna().unique()
    cursor = conn.cursor()
    insertados = 0
    
    for disp in dispositivos_unicos:
        disp = str(disp).strip()
        if not disp:
            continue
        try:
            cursor.execute(
                "INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo, activo) VALUES (?, 1, 1)",
                (disp,)
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    print(f"  ✅ {insertados} dispositivos cargados")


def cargar_convocatorias(conn):
    """Carga convocatorias desde conv.xlsx con reporte detallado"""
    print_step(5, 9, "Cargando convocatorias...")
    df = pd.read_excel(EXCEL_CONV, sheet_name='Convocatoria')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)

    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(r['NOMBRE Y APELLIDO']).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025'])
    }

    cursor = conn.cursor()
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}

    insertados = 0
    sin_fecha = 0
    sin_residente = 0
    sin_turno = 0
    filas_vacias = 0

    for idx, row in df.iterrows():
        # Verificar si la fila está vacía
        if fila_vacia(row, ['Dia', 'Residente', 'Turno']):
            filas_vacias += 1
            continue

        # Validar fecha
        fecha = pd.to_datetime(row.get('Dia'), errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue
        
        fecha = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha <= '2025-12-31'):
            sin_fecha += 1
            continue

        # Validar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        if not apellido or apellido not in agentes:
            sin_residente += 1
            continue

        id_agente = agentes[apellido]
        
        # Determinar tipo de turno
        turno_raw = normalizar(row.get('Turno'))
        tipo = 'capacitacion'
        if 'apertura' in turno_raw:
            tipo = 'apertura_publico'
        elif 'tarde' in turno_raw:
            tipo = 'tarde'
        elif 'manana' in turno_raw:
            tipo = 'mañana'

        # Buscar día y turno
        cursor.execute("SELECT id_dia, numero_dia_semana FROM dias WHERE fecha = ?", (fecha,))
        d = cursor.fetchone()
        if not d:
            sin_turno += 1
            continue
        id_dia, dia_sem = d

        cursor.execute(
            "SELECT id_turno FROM turnos WHERE numero_dia_semana = ? AND tipo_turno = ?",
            (dia_sem, tipo),
        )
        t = cursor.fetchone()
        if not t:
            sin_turno += 1
            continue

        id_turno = t[0]
        
        # Crear planificación
        cursor.execute(
            """INSERT OR IGNORE INTO planificacion (id_dia, id_turno, cant_residentes_plan, cant_visit)
             VALUES (?, ?, 3, 0)""",
            (id_dia, id_turno),
        )
        cursor.execute(
            """SELECT id_plani FROM planificacion WHERE id_dia = ? AND id_turno = ?""",
            (id_dia, id_turno),
        )
        id_plani = cursor.fetchone()[0]

        # Insertar convocatoria
        try:
            cursor.execute(
                """
                INSERT INTO convocatoria
                (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
                VALUES (?, ?, ?, ?, 'vigente')
                """,
                (id_plani, id_agente, id_turno, fecha),
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    
    # Guardar reporte
    REPORTE['convocatorias'] = {
        'total': len(df),
        'insertadas': insertados,
        'sin_fecha': sin_fecha,
        'sin_residente': sin_residente,
        'sin_turno': sin_turno,
        'filas_vacias': filas_vacias
    }
    
    print(f"  ✅ {insertados} convocatorias insertadas")


def cargar_menu(conn):
    """Carga asignaciones de dispositivos desde Menu con reporte detallado"""
    print_step(6, 9, "Cargando asignaciones de dispositivos...")
    df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(r['NOMBRE Y APELLIDO']).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025'])
    }
    
    cursor = conn.cursor()
    
    # Mapeo agentes
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    # Mapeo dispositivos
    cursor.execute("SELECT id_dispositivo, nombre_dispositivo FROM dispositivos")
    dispositivos = {normalizar(d): i for i, d in cursor.fetchall()}
    
    insertados = 0
    sin_fecha = 0
    sin_dispositivo = 0
    sin_residente = 0
    sin_convocatoria = 0
    filas_vacias = 0
    
    for _, row in df.iterrows():
        # Verificar si la fila está vacía
        if fila_vacia(row, ['Fecha', 'Residente', 'Dispositivo']):
            filas_vacias += 1
            continue

        # Validar fecha
        fecha = pd.to_datetime(row.get('Fecha'), errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue
        fecha = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha <= '2025-12-31'):
            sin_fecha += 1
            continue
        
        # Validar dispositivo
        disp_raw = normalizar(row.get('Dispositivo'))
        id_dispositivo = dispositivos.get(disp_raw)
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
        
        # Buscar convocatoria
        cursor.execute(
            "SELECT id_convocatoria FROM convocatoria WHERE id_agente = ? AND fecha_convocatoria = ? LIMIT 1",
            (id_agente, fecha)
        )
        conv = cursor.fetchone()
        if not conv:
            sin_convocatoria += 1
            continue
        id_convocatoria = conv[0]
        
        # Orden y acompaña
        orden = 1
        if pd.notna(row.get('Orden')):
            try:
                orden = int(row['Orden'])
            except:
                pass
        
        acompana = 0
        if pd.notna(row.get('Acom. al grupo')):
            val = str(row['Acom. al grupo']).lower()
            if val in ['si', 'sí', 's', '1', 'true']:
                acompana = 1
        
        try:
            cursor.execute(
                """INSERT INTO menu (id_convocatoria, id_dispositivo, id_agente, fecha_asignacion, orden, acompaña_grupo)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (id_convocatoria, id_dispositivo, id_agente, fecha, orden, acompana)
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    
    # Guardar reporte
    REPORTE['menu'] = {
        'total': len(df),
        'insertadas': insertados,
        'sin_fecha': sin_fecha,
        'sin_dispositivo': sin_dispositivo,
        'sin_residente': sin_residente,
        'sin_convocatoria': sin_convocatoria,
        'filas_vacias': filas_vacias
    }
    
    print(f"  ✅ {insertados} asignaciones insertadas")


def cargar_inasistencias(conn):
    """Carga inasistencias desde global.xlsx con reporte detallado"""
    print_step(7, 9, "Cargando inasistencias...")
    df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Inasistencias')
    cursor = conn.cursor()

    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}

    insertados = 0
    sin_fecha = 0
    sin_residente = 0
    fuera_rango = 0
    filas_vacias = 0

    for _, row in df.iterrows():
        # Verificar si la fila está vacía
        if fila_vacia(row, ['Fecha de la inasistencia', 'Fecha', 'Residente', 'Residente cultural ']):
            filas_vacias += 1
            continue

        # Validar fecha
        fecha_raw = row.get('Fecha de la inasistencia') or row.get('Fecha')
        fecha = pd.to_datetime(fecha_raw, errors='coerce')
        if pd.isna(fecha):
            sin_fecha += 1
            continue

        fecha = fecha.strftime('%Y-%m-%d')
        if not ('2025-01-01' <= fecha <= '2025-12-31'):
            fuera_rango += 1
            continue

        # Validar residente
        residente = row.get('Residente') or row.get('Residente cultural ')
        id_agente = resolver_agente(residente, agentes)
        if not id_agente:
            sin_residente += 1
            continue

        # Determinar motivo
        motivo_raw = normalizar(row.get('Motivo de la ausencia'))
        motivo = 'imprevisto'
        if 'medic' in motivo_raw:
            motivo = 'medico'
        elif 'estudio' in motivo_raw:
            motivo = 'estudio'
        elif 'injustific' in motivo_raw:
            motivo = 'injustificada'

        # Fecha de aviso
        fecha_aviso = datetime.now().isoformat()
        if pd.notna(row.get('Marca temporal')):
            ts = pd.to_datetime(row['Marca temporal'], errors='coerce')
            if pd.notna(ts):
                fecha_aviso = ts.isoformat()

        try:
            cursor.execute(
                """
                INSERT INTO inasistencias
                (id_agente, fecha_aviso, fecha_inasistencia, motivo, estado)
                VALUES (?, ?, ?, ?, 'pendiente')
                """,
                (id_agente, fecha_aviso, fecha, motivo),
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    
    # Guardar reporte
    REPORTE['inasistencias'] = {
        'total': len(df),
        'insertadas': insertados,
        'sin_fecha': sin_fecha,
        'sin_residente': sin_residente,
        'fuera_rango': fuera_rango,
        'filas_vacias': filas_vacias
    }
    
    print(f"  ✅ {insertados} inasistencias insertadas")


def verificar_saldos(conn):
    """Verifica que los triggers de saldos funcionaron"""
    print_step(8, 9, "Verificando triggers de saldos...")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(DISTINCT id_agente) FROM convocatoria WHERE fecha_convocatoria >= '2025-07-01'")
    agentes_conv = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT id_agente) FROM saldos WHERE anio = 2025 AND mes >= 7")
    agentes_saldo = cursor.fetchone()[0]
    
    if agentes_conv > 0 and agentes_saldo > 0:
        print(f"  ✅ Triggers funcionando ({agentes_saldo} agentes con saldos)")
    else:
        print(f"  ⚠️  Verificar triggers (convocatorias: {agentes_conv}, saldos: {agentes_saldo})")


def mostrar_resumen_final(conn):
    """Muestra resumen de carga y estadísticas finales"""
    print_step(9, 9, "Resumen final de carga")
    
    cursor = conn.cursor()
    
    # Datos en BD
    cursor.execute("SELECT COUNT(*) FROM datos_personales WHERE activo = 1")
    residentes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dispositivos WHERE activo = 1")
    dispositivos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM convocatoria WHERE fecha_convocatoria >= '2025-07-01'")
    convocatorias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM menu WHERE fecha_asignacion >= '2025-07-01'")
    asignaciones = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inasistencias WHERE fecha_inasistencia >= '2025-07-01'")
    inasistencias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM saldos WHERE anio = 2025 AND mes >= 7")
    saldos = cursor.fetchone()[0]
    
    print("\n" + "="*70)
    print("  DATOS CARGADOS EN BASE DE DATOS")
    print("="*70)
    print(f"""
  Maestros:
    • Residentes: {residentes}
    • Dispositivos: {dispositivos}
    
  Operativos (jul-dic 2025):
    • Convocatorias: {convocatorias}
    • Asignaciones: {asignaciones}
    • Inasistencias: {inasistencias}
    • Saldos: {saldos}
""")
    
    # Reporte detallado de registros NO cargados
    print("="*70)
    print("  REPORTE DE REGISTROS NO CARGADOS")
    print("="*70)
    
    # CONVOCATORIAS
    conv = REPORTE['convocatorias']
    print(f"\n  📋 CONVOCATORIAS:")
    print(f"     Total filas en Excel: {conv['total']}")
    print(f"     ✅ Insertadas: {conv['insertadas']}")
    print(f"     ❌ NO insertadas: {conv['total'] - conv['insertadas'] - conv['filas_vacias']}")
    if conv['filas_vacias'] > 0:
        print(f"        • Filas vacías (sin datos): {conv['filas_vacias']}")
    if conv['sin_fecha'] > 0:
        print(f"        • Sin fecha válida o fuera de rango: {conv['sin_fecha']}")
    if conv['sin_residente'] > 0:
        print(f"        • Sin residente válido: {conv['sin_residente']}")
    if conv['sin_turno'] > 0:
        print(f"        • Sin turno válido: {conv['sin_turno']}")
    
    datos_reales_conv = conv['total'] - conv['filas_vacias']
    if datos_reales_conv > 0:
        tasa_conv = (conv['insertadas'] / datos_reales_conv) * 100
        print(f"     📊 Tasa de carga (datos reales): {tasa_conv:.1f}%")
    
    # MENU
    menu = REPORTE['menu']
    print(f"\n  📋 ASIGNACIONES (MENU):")
    print(f"     Total filas en Excel: {menu['total']}")
    print(f"     ✅ Insertadas: {menu['insertadas']}")
    print(f"     ❌ NO insertadas: {menu['total'] - menu['insertadas'] - menu['filas_vacias']}")
    if menu['filas_vacias'] > 0:
        print(f"        • Filas vacías (sin datos): {menu['filas_vacias']}")
    if menu['sin_fecha'] > 0:
        print(f"        • Sin fecha válida o fuera de rango: {menu['sin_fecha']}")
    if menu['sin_dispositivo'] > 0:
        print(f"        • Sin dispositivo válido: {menu['sin_dispositivo']}")
    if menu['sin_residente'] > 0:
        print(f"        • Sin residente válido: {menu['sin_residente']}")
    if menu['sin_convocatoria'] > 0:
        print(f"        • Sin convocatoria correspondiente: {menu['sin_convocatoria']}")
    
    datos_reales_menu = menu['total'] - menu['filas_vacias']
    if datos_reales_menu > 0:
        tasa_menu = (menu['insertadas'] / datos_reales_menu) * 100
        print(f"     📊 Tasa de carga (datos reales): {tasa_menu:.1f}%")
    
    # INASISTENCIAS
    inas = REPORTE['inasistencias']
    print(f"\n  📋 INASISTENCIAS:")
    print(f"     Total filas en Excel: {inas['total']}")
    print(f"     ✅ Insertadas: {inas['insertadas']}")
    print(f"     ❌ NO insertadas: {inas['total'] - inas['insertadas'] - inas['filas_vacias']}")
    if inas['filas_vacias'] > 0:
        print(f"        • Filas vacías (sin datos): {inas['filas_vacias']}")
    if inas['sin_fecha'] > 0:
        print(f"        • Sin fecha válida: {inas['sin_fecha']}")
    if inas['fuera_rango'] > 0:
        print(f"        • Fuera del rango jul-dic 2025: {inas['fuera_rango']}")
    if inas['sin_residente'] > 0:
        print(f"        • Sin residente válido: {inas['sin_residente']}")
    
    datos_reales_inas = inas['total'] - inas['filas_vacias']
    if datos_reales_inas > 0:
        tasa_inas = (inas['insertadas'] / datos_reales_inas) * 100
        print(f"     📊 Tasa de carga (datos reales): {tasa_inas:.1f}%")
    
    print("\n" + "="*70)
    print("  ✅ CARGA COMPLETADA")
    print("="*70 + "\n")


# ==========================
# MAIN
# ==========================

def main():
    print_header("CARGA FINAL v2.2 - COMPLETA CON REPORTE DETALLADO")

    # Verificar archivos
    for f in [DB_PATH, EXCEL_CONV, EXCEL_GLOBAL, EXCEL_EQUIVALENCIAS]:
        if not Path(f).exists():
            print(f"❌ Falta archivo: {f}")
            return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    activar_foreign_keys(conn)

    # Ejecutar cargas
    limpiar_base_datos(conn)
    cargar_datos_personales(conn)
    cargar_dias_y_turnos(conn)
    cargar_dispositivos(conn)
    cargar_convocatorias(conn)
    cargar_menu(conn)
    cargar_inasistencias(conn)
    verificar_saldos(conn)
    mostrar_resumen_final(conn)

    conn.close()
    return True


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)