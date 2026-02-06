#!/usr/bin/env python3
"""
SCRIPT MAESTRO DE CARGA COMPLETA - Versión Simplificada
Carga todos los datos del segundo semestre 2025
Funciona con archivos: global.xlsx y conv.xlsx
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import sys

# Configuración - NOMBRES SIMPLIFICADOS
DB_PATH = 'data/gestion_rrhh.db'
EXCEL_GLOBAL = 'data/global.xlsx'
EXCEL_CONV = 'data/conv.xlsx'

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, total, text):
    print(f"\n[{step}/{total}] {text}")

def activar_foreign_keys(conn):
    """Activa las Foreign Keys"""
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.execute("PRAGMA foreign_keys")
    status = cursor.fetchone()[0]
    if status:
        print("  ✅ Foreign Keys activadas")
    else:
        print("  ⚠️  Foreign Keys NO activadas")
    return status

def cargar_datos_personales(conn):
    """Carga residentes desde Excel"""
    print_step(1, 7, "Cargando datos personales...")
    
    try:
        # Leer Excel
        df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Datos personales')
        
        cursor = conn.cursor()
        insertados = 0
        
        for _, row in df.iterrows():
            try:
                dni = str(row['DNI']).strip()
                nombre = str(row['Nombre']).strip()
                apellido = str(row['Apellido']).strip()
                email = str(row['E-mail']).strip() if pd.notna(row['E-mail']) else f"{nombre.lower()}.{apellido.lower()}@ejemplo.com"
                
                cursor.execute("""
                    INSERT INTO datos_personales (nombre, apellido, dni, fecha_nacimiento, email, activo)
                    VALUES (?, ?, ?, '1990-01-01', ?, 1)
                """, (nombre, apellido, dni, email))
                
                insertados += 1
            except sqlite3.IntegrityError:
                continue  # Ya existe
            except Exception as e:
                print(f"    ⚠️  Error en fila: {e}")
                continue
        
        conn.commit()
        print(f"  ✅ {insertados} residentes cargados")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"  💡 Verifica que el archivo {EXCEL_GLOBAL} tenga una hoja llamada 'Datos personales'")
        return 0

def cargar_dias_y_turnos(conn):
    """Genera días y carga turnos base"""
    print_step(2, 7, "Generando días y turnos...")
    
    cursor = conn.cursor()
    
    # Generar días jul-dic 2025
    start_date = date(2025, 7, 1)
    end_date = date(2025, 12, 31)
    
    dias_generados = 0
    current = start_date
    while current <= end_date:
        try:
            cursor.execute("""
                INSERT INTO dias (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                current.isoformat(),
                current.month,
                current.isocalendar()[1],
                current.day,
                current.weekday()
            ))
            dias_generados += 1
        except sqlite3.IntegrityError:
            pass
        
        current += timedelta(days=1)
    
    # Turnos base
    turnos = [
        (1, 'mañana', '09:00', '13:00', 4.0),
        (1, 'tarde', '14:00', '18:00', 4.0),
        (1, 'capacitacion', '09:00', '13:00', 4.0),
        (2, 'mañana', '09:00', '13:00', 4.0),
        (2, 'tarde', '14:00', '18:00', 4.0),
        (2, 'capacitacion', '09:00', '13:00', 4.0),
        (3, 'mañana', '09:00', '13:00', 4.0),
        (3, 'tarde', '14:00', '18:00', 4.0),
        (3, 'capacitacion', '09:00', '13:00', 4.0),
        (4, 'mañana', '09:00', '13:00', 4.0),
        (4, 'tarde', '14:00', '18:00', 4.0),
        (4, 'capacitacion', '09:00', '13:00', 4.0),
        (5, 'mañana', '09:00', '13:00', 4.0),
        (5, 'tarde', '14:00', '18:00', 4.0),
        (5, 'capacitacion', '09:00', '13:00', 4.0),
        (6, 'apertura_publico', '10:00', '14:00', 4.0),
        (6, 'capacitacion', '09:00', '13:00', 4.0),
        (0, 'descanso', '00:00', '00:00', 0.0),
        (7, 'descanso', '00:00', '00:00', 0.0),
        (8, 'descanso', '00:00', '00:00', 0.0),
    ]
    
    turnos_insertados = 0
    for dia, tipo, inicio, fin, horas in turnos:
        try:
            cursor.execute("""
                INSERT INTO turnos (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas, activo)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (dia, tipo, inicio, fin, horas))
            turnos_insertados += 1
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    print(f"  ✅ {dias_generados} días generados")
    print(f"  ✅ {turnos_insertados} turnos creados")
    return dias_generados, turnos_insertados

def cargar_dispositivos(conn):
    """Carga dispositivos desde Excel"""
    print_step(3, 7, "Cargando dispositivos...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
        
        # Extraer dispositivos únicos
        dispositivos_unicos = df['Dispositivo'].dropna().unique()
        
        cursor = conn.cursor()
        insertados = 0
        
        for disp in dispositivos_unicos:
            try:
                cursor.execute("""
                    INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo, activo)
                    VALUES (?, 1, 1)
                """, (str(disp).strip(),))
                insertados += 1
            except sqlite3.IntegrityError:
                continue
        
        conn.commit()
        print(f"  ✅ {insertados} dispositivos cargados")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"  💡 Verifica que el archivo {EXCEL_CONV} tenga una hoja llamada 'Menu'")
        return 0

def parsear_fecha(fecha_str):
    """Parsea fechas del formato del Excel"""
    if pd.isna(fecha_str):
        return None
    
    fecha_str = str(fecha_str).strip().lower()
    
    # Formato: "lunes - 1, jul"
    meses = {
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    for mes_nombre, mes_num in meses.items():
        if mes_nombre in fecha_str:
            # Extraer el día
            partes = fecha_str.split(',')
            if len(partes) >= 1:
                dia_parte = partes[0].split('-')[-1].strip()
                try:
                    dia = int(dia_parte)
                    return f"2025-{mes_num:02d}-{dia:02d}"
                except:
                    pass
    
    return None

def cargar_convocatorias(conn):
    """Carga convocatorias desde Excel"""
    print_step(4, 7, "Cargando convocatorias...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Todas')
        
        cursor = conn.cursor()
        
        # Crear mapeo de agentes
        cursor.execute("SELECT id_agente, apellido, nombre FROM datos_personales")
        agentes = {}
        alias_map = {}
        
        for row in cursor.fetchall():
            id_agente, apellido, nombre = row
            # Nombre completo
            nombre_completo = f"{apellido}, {nombre}".lower()
            agentes[nombre_completo] = id_agente
            
            # Alias por apellido
            alias_map[apellido.lower()] = id_agente
            
            # Alias por primer nombre
            primer_nombre = nombre.split()[0] if nombre else ""
            if primer_nombre:
                alias_map[primer_nombre.lower()] = id_agente
        
        insertados = 0
        sin_match = 0
        
        print(f"    Procesando {len(df)} filas...")
        
        for idx, row in df.iterrows():
            fecha = parsear_fecha(row.get('Fecha'))
            if not fecha or fecha < '2025-07-01':
                continue
            
            residente = str(row.get('Nombre residente', '')).strip()
            if not residente:
                continue
            
            # Buscar agente
            id_agente = None
            residente_lower = residente.lower()
            
            # Buscar en alias
            for key, id_ag in alias_map.items():
                if key in residente_lower:
                    id_agente = id_ag
                    break
            
            if not id_agente:
                sin_match += 1
                continue
            
            # Determinar tipo de turno
            turno_str = str(row.get('Turno', '')).lower()
            tipo_turno = 'capacitacion'
            if 'apertura' in turno_str or 'público' in turno_str or 'publico' in turno_str:
                tipo_turno = 'apertura_publico'
            elif 'tarde' in turno_str:
                tipo_turno = 'tarde'
            elif 'mañana' in turno_str or 'manana' in turno_str:
                tipo_turno = 'mañana'
            elif 'descanso' in turno_str:
                tipo_turno = 'descanso'
            
            # Obtener día de la semana
            cursor.execute("SELECT numero_dia_semana, id_dia FROM dias WHERE fecha = ?", (fecha,))
            dia_row = cursor.fetchone()
            if not dia_row:
                continue
            
            dia_semana, id_dia = dia_row
            
            # Buscar turno
            cursor.execute("""
                SELECT id_turno FROM turnos 
                WHERE numero_dia_semana = ? AND tipo_turno = ?
                LIMIT 1
            """, (dia_semana, tipo_turno))
            
            turno_row = cursor.fetchone()
            if not turno_row:
                # Buscar genérico
                cursor.execute("""
                    SELECT id_turno FROM turnos 
                    WHERE numero_dia_semana = 8 AND tipo_turno = ?
                    LIMIT 1
                """, (tipo_turno,))
                turno_row = cursor.fetchone()
            
            if not turno_row:
                continue
            
            id_turno = turno_row[0]
            
            # Crear planificación si no existe
            cursor.execute("""
                INSERT OR IGNORE INTO planificacion (id_dia, id_turno, cant_residentes_plan, cant_visit)
                VALUES (?, ?, 3, 0)
            """, (id_dia, id_turno))
            
            cursor.execute("""
                SELECT id_plani FROM planificacion WHERE id_dia = ? AND id_turno = ?
            """, (id_dia, id_turno))
            id_plani = cursor.fetchone()[0]
            
            # Insertar convocatoria
            try:
                cursor.execute("""
                    INSERT INTO convocatoria (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
                    VALUES (?, ?, ?, ?, 'vigente')
                """, (id_plani, id_agente, id_turno, fecha))
                insertados += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        print(f"  ✅ {insertados} convocatorias insertadas")
        if sin_match > 0:
            print(f"  ⚠️  {sin_match} registros sin match de residente (puede ser normal)")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"  💡 Verifica que el archivo {EXCEL_CONV} tenga una hoja llamada 'Todas'")
        import traceback
        traceback.print_exc()
        return 0

def cargar_menu(conn):
    """Carga asignaciones de dispositivos"""
    print_step(5, 7, "Cargando asignaciones de dispositivos...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
        
        cursor = conn.cursor()
        insertados = 0
        
        print(f"    Procesando {len(df)} filas...")
        
        for _, row in df.iterrows():
            fecha = parsear_fecha(row.get('Fecha'))
            if not fecha or fecha < '2025-07-01':
                continue
            
            dispositivo = str(row.get('Dispositivo', '')).strip()
            residente = str(row.get('Nombre residente', '')).strip()
            
            if not dispositivo or not residente:
                continue
            
            # Buscar dispositivo
            cursor.execute("""
                SELECT id_dispositivo FROM dispositivos WHERE nombre_dispositivo = ?
            """, (dispositivo,))
            disp_row = cursor.fetchone()
            if not disp_row:
                continue
            
            id_dispositivo = disp_row[0]
            
            # Buscar agente (buscar en cualquier parte del nombre)
            residente_lower = residente.lower()
            cursor.execute("""
                SELECT id_agente FROM datos_personales 
                WHERE LOWER(apellido) LIKE ? OR LOWER(nombre) LIKE ?
                LIMIT 1
            """, (f"%{residente_lower}%", f"%{residente_lower}%"))
            agente_row = cursor.fetchone()
            if not agente_row:
                continue
            
            id_agente = agente_row[0]
            
            # Buscar convocatoria
            cursor.execute("""
                SELECT id_convocatoria FROM convocatoria
                WHERE id_agente = ? AND fecha_convocatoria = ?
                LIMIT 1
            """, (id_agente, fecha))
            conv_row = cursor.fetchone()
            if not conv_row:
                continue
            
            id_convocatoria = conv_row[0]
            
            # Insertar en menú
            try:
                cursor.execute("""
                    INSERT INTO menu (id_convocatoria, id_dispositivo, id_agente, fecha_asignacion, orden)
                    VALUES (?, ?, ?, ?, 1)
                """, (id_convocatoria, id_dispositivo, id_agente, fecha))
                insertados += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        print(f"  ✅ {insertados} asignaciones insertadas")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0

def cargar_inasistencias(conn):
    """Carga inasistencias desde Excel"""
    print_step(6, 7, "Cargando inasistencias...")
    
    try:
        df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Inasistencias')
        
        cursor = conn.cursor()
        insertados = 0
        
        print(f"    Procesando {len(df)} filas...")
        
        for _, row in df.iterrows():
            fecha = row.get('Fecha de la inasistencia')
            if pd.isna(fecha):
                continue
            
            if isinstance(fecha, str):
                fecha = pd.to_datetime(fecha, errors='coerce')
            
            if pd.isna(fecha):
                continue
            
            fecha_str = fecha.strftime('%Y-%m-%d')
            if fecha_str < '2025-07-01':
                continue
            
            residente = str(row.get('Nombre residente', '')).strip()
            if not residente:
                continue
            
            # Buscar agente
            residente_lower = residente.lower()
            cursor.execute("""
                SELECT id_agente FROM datos_personales 
                WHERE LOWER(apellido) LIKE ? OR LOWER(nombre) LIKE ?
                LIMIT 1
            """, (f"%{residente_lower}%", f"%{residente_lower}%"))
            agente_row = cursor.fetchone()
            if not agente_row:
                continue
            
            id_agente = agente_row[0]
            
            # Mapear motivo
            motivo_str = str(row.get('Motivo', '')).lower()
            motivo = 'imprevisto'
            if 'enfermedad' in motivo_str or 'médico' in motivo_str or 'medico' in motivo_str:
                motivo = 'medico'
            elif 'estudio' in motivo_str or 'examen' in motivo_str:
                motivo = 'estudio'
            elif 'injustificad' in motivo_str:
                motivo = 'injustificada'
            
            # Fecha de aviso
            fecha_aviso = datetime.now().isoformat()
            if pd.notna(row.get('Marca temporal')):
                try:
                    fecha_aviso = pd.to_datetime(row['Marca temporal']).isoformat()
                except:
                    pass
            
            # Insertar
            try:
                cursor.execute("""
                    INSERT INTO inasistencias (id_agente, fecha_aviso, fecha_inasistencia, motivo, estado)
                    VALUES (?, ?, ?, ?, 'pendiente')
                """, (id_agente, fecha_aviso, fecha_str, motivo))
                insertados += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        print(f"  ✅ {insertados} inasistencias insertadas")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"  💡 Verifica que el archivo {EXCEL_GLOBAL} tenga una hoja llamada 'Inasistencias'")
        return 0

def verificar_saldos(conn):
    """Verifica que los triggers de saldos funcionaron"""
    print_step(7, 7, "Verificando saldos automáticos...")
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id_agente) FROM convocatoria
        WHERE fecha_convocatoria >= '2025-07-01'
    """)
    agentes_con_conv = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id_agente) FROM saldos
        WHERE anio = 2025 AND mes >= 7
    """)
    agentes_con_saldo = cursor.fetchone()[0]
    
    print(f"  • Agentes con convocatorias: {agentes_con_conv}")
    print(f"  • Agentes con saldos: {agentes_con_saldo}")
    
    if agentes_con_conv == agentes_con_saldo:
        print(f"  ✅ Triggers de saldos funcionando correctamente")
        return True
    else:
        print(f"  ⚠️  Discrepancia en saldos (puede ser normal si algunos agentes no tienen convocatorias)")
        return False

def mostrar_resumen(conn):
    """Muestra resumen de datos cargados"""
    print_header("RESUMEN DE CARGA")
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM datos_personales WHERE activo = 1")
    residentes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dispositivos WHERE activo = 1")
    dispositivos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM convocatoria WHERE fecha_convocatoria >= '2025-07-01'")
    convocatorias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM planificacion p JOIN dias d ON p.id_dia = d.id_dia WHERE d.fecha >= '2025-07-01'")
    planificaciones = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM saldos WHERE anio = 2025 AND mes >= 7")
    saldos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM menu WHERE fecha_asignacion >= '2025-07-01'")
    asignaciones = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inasistencias WHERE fecha_inasistencia >= '2025-07-01'")
    inasistencias = cursor.fetchone()[0]
    
    print(f"""
✅ CARGA COMPLETADA

Datos maestros:
  • Residentes activos: {residentes}
  • Dispositivos: {dispositivos}

Datos operativos (jul-dic 2025):
  • Convocatorias: {convocatorias}
  • Planificaciones: {planificaciones}
  • Saldos: {saldos}
  • Asignaciones: {asignaciones}
  • Inasistencias: {inasistencias}

Próximos pasos:
  1. python3 verificacion_final_migracion.py
  2. python3 generar_reporte_html.py
  3. open REPORTE_MIGRACION.html
""")

def main():
    """Función principal"""
    print_header("CARGA COMPLETA DE DATOS - SISTEMA RRHH v2.0")
    print("Archivos esperados: data/global.xlsx y data/conv.xlsx")
    
    # Verificar archivos
    if not Path(DB_PATH).exists():
        print(f"\n❌ No se encuentra: {DB_PATH}")
        print("   Asegúrate de tener la base de datos creada")
        return False
    
    if not Path(EXCEL_GLOBAL).exists():
        print(f"\n❌ No se encuentra: {EXCEL_GLOBAL}")
        print("   Renombra tu archivo Excel de datos personales a 'global.xlsx'")
        print("   y cópialo a la carpeta data/")
        return False
    
    if not Path(EXCEL_CONV).exists():
        print(f"\n❌ No se encuentra: {EXCEL_CONV}")
        print("   Renombra tu archivo Excel de convocatorias a 'conv.xlsx'")
        print("   y cópialo a la carpeta data/")
        return False
    
    print(f"\n✅ Base de datos encontrada: {DB_PATH}")
    print(f"✅ Archivo global encontrado: {EXCEL_GLOBAL}")
    print(f"✅ Archivo conv encontrado: {EXCEL_CONV}")
    
    try:
        # Conectar
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Activar Foreign Keys
        activar_foreign_keys(conn)
        
        # Ejecutar carga
        cargar_datos_personales(conn)
        cargar_dias_y_turnos(conn)
        cargar_dispositivos(conn)
        cargar_convocatorias(conn)
        cargar_menu(conn)
        cargar_inasistencias(conn)
        verificar_saldos(conn)
        
        # Resumen
        mostrar_resumen(conn)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
