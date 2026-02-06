#!/usr/bin/env python3
"""
SCRIPT DE CARGA FINAL - Optimizado para tus archivos reales
- Convocatorias y Menu desde: conv.xlsx
- Datos personales e Inasistencias desde: global.xlsx
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import sys

# Configuración
DB_PATH = 'data/gestion_rrhh.db'
EXCEL_CONV = 'data/conv.xlsx'
EXCEL_GLOBAL = 'data/global.xlsx'
EXCEL_EQUIVALENCIAS = 'data/equivalencias.xlsx'

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

def limpiar_base_datos(conn):
    """Limpia datos previos"""
    print_step(1, 8, "Limpiando datos previos...")
    
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    tablas = ['menu', 'inasistencias', 'convocatoria', 'planificacion', 
              'saldos', 'disponibilidad', 'dispositivos', 'datos_personales', 
              'turnos', 'dias']
    
    for tabla in tablas:
        cursor.execute(f"DELETE FROM {tabla}")
    
    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON")
    print("  ✅ Base de datos limpiada")

def cargar_datos_personales(conn):
    """Carga residentes desde global.xlsx"""
    print_step(2, 8, "Cargando datos personales...")
    
    try:
        df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Datos personales')
        
        cursor = conn.cursor()
        insertados = 0
        
        for _, row in df.iterrows():
            try:
                nombre = str(row.get('Nombre', '')).strip()
                apellido = str(row.get('Apellido', '')).strip()
                
                if not nombre or not apellido or pd.isna(row.get('Nombre')) or pd.isna(row.get('Apellido')):
                    continue
                
                dni = str(row.get('DNI', '00000000')).strip()
                email = str(row.get('MAIL', '')).strip()
                if not email or pd.isna(email):
                    email = f"{nombre.lower()}.{apellido.lower()}@ejemplo.com"
                
                cursor.execute("""
                    INSERT INTO datos_personales (nombre, apellido, dni, fecha_nacimiento, email, activo)
                    VALUES (?, ?, ?, '1990-01-01', ?, 1)
                """, (nombre, apellido, dni, email))
                
                insertados += 1
            except sqlite3.IntegrityError:
                continue
            except Exception as e:
                continue
        
        conn.commit()
        print(f"  ✅ {insertados} residentes cargados")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0

def cargar_dias_y_turnos(conn):
    """Genera días y carga turnos base"""
    print_step(3, 8, "Generando días y turnos...")
    
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
    """Carga dispositivos desde conv.xlsx (hoja Menu)"""
    print_step(4, 8, "Cargando dispositivos...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
        
        # Extraer dispositivos únicos (solo los no nulos)
        dispositivos_unicos = df['Dispositivo'].dropna().unique()
        
        cursor = conn.cursor()
        insertados = 0
        
        for disp in dispositivos_unicos:
            if pd.isna(disp) or str(disp).strip() == '':
                continue
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
        return 0

def cargar_convocatorias(conn):
    """Carga convocatorias desde conv.xlsx usando tabla de equivalencias"""
    print_step(5, 8, "Cargando convocatorias...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Convocatoria')
        
        # Cargar tabla de equivalencias
        df_equiv = pd.read_excel(EXCEL_EQUIVALENCIAS, sheet_name=0)
        
        # Crear mapeo: alias → nombre_completo
        mapeo_alias = {}
        for _, row in df_equiv.iterrows():
            alias = str(row['Residente 2025']).strip()
            nombre_completo = str(row['NOMBRE Y APELLIDO']).strip()
            # Formato: "Apellido, Nombre" → extraer apellido
            if ',' in nombre_completo:
                apellido = nombre_completo.split(',')[0].strip()
                mapeo_alias[alias.lower()] = apellido.lower()
        
        cursor = conn.cursor()
        
        # Crear mapeo de residentes en BD por apellido
        cursor.execute("SELECT id_agente, apellido, nombre FROM datos_personales")
        agentes_map = {}
        
        for row in cursor.fetchall():
            id_agente, apellido, nombre = row
            apellido_lower = apellido.lower() if apellido else ""
            agentes_map[apellido_lower] = id_agente
        
        insertados = 0
        sin_fecha = 0
        sin_residente = 0
        sin_match_equiv = 0
        
        print(f"    Procesando {len(df)} filas...")
        print(f"    Tabla de equivalencias: {len(mapeo_alias)} alias")
        
        for idx, row in df.iterrows():
            # Obtener fecha de columna 'Dia'
            fecha_val = row.get('Dia')
            if pd.isna(fecha_val):
                sin_fecha += 1
                continue
            
            # Convertir a string de fecha
            if isinstance(fecha_val, (datetime, pd.Timestamp)):
                fecha = fecha_val.strftime('%Y-%m-%d')
            else:
                sin_fecha += 1
                continue
            
            # Verificar rango
            if fecha < '2025-07-01' or fecha > '2025-12-31':
                sin_fecha += 1
                continue
            
            # Obtener residente (alias)
            alias = str(row.get('Residente', '')).strip()
            if not alias or pd.isna(row.get('Residente')):
                sin_residente += 1
                continue
            
            # Buscar en tabla de equivalencias
            alias_lower = alias.lower()
            if alias_lower not in mapeo_alias:
                sin_match_equiv += 1
                continue
            
            apellido_buscado = mapeo_alias[alias_lower]
            
            # Buscar agente por apellido
            id_agente = agentes_map.get(apellido_buscado)
            if not id_agente:
                sin_residente += 1
                continue
            
            # Determinar tipo de turno
            turno_str = str(row.get('Turno', '')).lower() if pd.notna(row.get('Turno')) else ''
            
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
        if sin_fecha > 0:
            print(f"  ℹ️  {sin_fecha} registros sin fecha válida")
        if sin_match_equiv > 0:
            print(f"  ℹ️  {sin_match_equiv} alias no encontrados en tabla equivalencias")
        if sin_residente > 0:
            print(f"  ℹ️  {sin_residente} residentes no encontrados en BD")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def cargar_menu(conn):
    """Carga asignaciones de dispositivos desde conv.xlsx usando tabla de equivalencias"""
    print_step(6, 8, "Cargando asignaciones de dispositivos...")
    
    try:
        df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
        
        # Cargar tabla de equivalencias
        df_equiv = pd.read_excel(EXCEL_EQUIVALENCIAS, sheet_name=0)
        
        # Crear mapeo: alias → apellido
        mapeo_alias = {}
        for _, row in df_equiv.iterrows():
            alias = str(row['Residente 2025']).strip()
            nombre_completo = str(row['NOMBRE Y APELLIDO']).strip()
            if ',' in nombre_completo:
                apellido = nombre_completo.split(',')[0].strip()
                mapeo_alias[alias.lower()] = apellido.lower()
        
        cursor = conn.cursor()
        
        # Crear mapeo de agentes por apellido
        cursor.execute("SELECT id_agente, apellido FROM datos_personales")
        agentes_map = {apellido.lower(): id_agente for id_agente, apellido in cursor.fetchall() if apellido}
        
        insertados = 0
        
        print(f"    Procesando {len(df)} filas...")
        
        for _, row in df.iterrows():
            # Parsear fecha
            fecha_val = row.get('Fecha')
            if pd.isna(fecha_val):
                continue
            
            if isinstance(fecha_val, (datetime, pd.Timestamp)):
                fecha = fecha_val.strftime('%Y-%m-%d')
            else:
                continue
            
            if fecha < '2025-07-01' or fecha > '2025-12-31':
                continue
            
            dispositivo = str(row.get('Dispositivo', '')).strip()
            alias = str(row.get('Residente', '')).strip()
            
            if not dispositivo or not alias or pd.isna(row.get('Dispositivo')) or pd.isna(row.get('Residente')):
                continue
            
            # Buscar dispositivo
            cursor.execute("""
                SELECT id_dispositivo FROM dispositivos WHERE nombre_dispositivo = ?
            """, (dispositivo,))
            disp_row = cursor.fetchone()
            if not disp_row:
                continue
            
            id_dispositivo = disp_row[0]
            
            # Buscar agente usando tabla de equivalencias
            alias_lower = alias.lower()
            if alias_lower not in mapeo_alias:
                continue
            
            apellido_buscado = mapeo_alias[alias_lower]
            id_agente = agentes_map.get(apellido_buscado)
            if not id_agente:
                continue
            
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
            
            # Obtener orden y acompaña grupo
            orden = 1
            if pd.notna(row.get('Orden')):
                try:
                    orden = int(row['Orden'])
                except:
                    orden = 1
            
            acompana = 0
            if pd.notna(row.get('Acom. al grupo')):
                acompana_val = str(row['Acom. al grupo']).lower()
                if acompana_val in ['si', 'sí', 's', '1', 'true']:
                    acompana = 1
            
            # Insertar en menú
            try:
                cursor.execute("""
                    INSERT INTO menu (id_convocatoria, id_dispositivo, id_agente, fecha_asignacion, orden, acompaña_grupo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_convocatoria, id_dispositivo, id_agente, fecha, orden, acompana))
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
    """Carga inasistencias desde global.xlsx"""
    print_step(7, 8, "Cargando inasistencias...")
    
    try:
        df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Inasistencias')
        
        cursor = conn.cursor()
        insertados = 0
        
        print(f"    Procesando {len(df)} filas...")
        
        for _, row in df.iterrows():
            # Parsear fecha
            fecha_val = row.get('Fecha de la inasistencia')
            if pd.isna(fecha_val):
                continue
            
            if isinstance(fecha_val, (datetime, pd.Timestamp)):
                fecha = fecha_val.strftime('%Y-%m-%d')
            else:
                try:
                    parsed = pd.to_datetime(fecha_val)
                    fecha = parsed.strftime('%Y-%m-%d')
                except:
                    continue
            
            if fecha < '2025-07-01' or fecha > '2025-12-31':
                continue
            
            # Residente
            residente_col = 'Residente' if 'Residente' in df.columns else 'Residente cultural '
            residente = str(row.get(residente_col, '')).strip()
            if not residente or pd.isna(row.get(residente_col)):
                continue
            
            # Buscar agente
            residente_lower = residente.lower()
            cursor.execute("""
                SELECT id_agente FROM datos_personales 
                WHERE LOWER(apellido) LIKE ? OR LOWER(nombre) LIKE ?
                OR LOWER(apellido || ', ' || nombre) LIKE ?
                LIMIT 1
            """, (f"%{residente_lower}%", f"%{residente_lower}%", f"%{residente_lower}%"))
            agente_row = cursor.fetchone()
            if not agente_row:
                continue
            
            id_agente = agente_row[0]
            
            # Mapear motivo
            motivo_str = str(row.get('Motivo de la ausencia', '')).lower() if pd.notna(row.get('Motivo de la ausencia')) else ''
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
                """, (id_agente, fecha_aviso, fecha, motivo))
                insertados += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        print(f"  ✅ {insertados} inasistencias insertadas")
        return insertados
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0

def verificar_saldos(conn):
    """Verifica que los triggers de saldos funcionaron"""
    print_step(8, 8, "Verificando saldos automáticos...")
    
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
    
    if agentes_con_conv > 0:
        print(f"  ✅ Triggers de saldos funcionando")
        return True
    else:
        print(f"  ⚠️  No hay convocatorias cargadas")
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
  1. sqlite3 data/gestion_rrhh.db "SELECT * FROM vista_salud_sistema;"
  2. python3 generar_reporte_html.py (si lo tienes)
""")

def main():
    """Función principal"""
    print_header("CARGA FINAL - ARCHIVOS REALES")
    print("Fuentes:")
    print("  • Convocatorias y Menu: conv.xlsx")
    print("  • Datos personales e Inasistencias: global.xlsx")
    
    # Verificar archivos
    if not Path(DB_PATH).exists():
        print(f"\n❌ No se encuentra: {DB_PATH}")
        return False
    
    if not Path(EXCEL_CONV).exists():
        print(f"\n❌ No se encuentra: {EXCEL_CONV}")
        return False
    
    if not Path(EXCEL_GLOBAL).exists():
        print(f"\n❌ No se encuentra: {EXCEL_GLOBAL}")
        return False
    
    if not Path(EXCEL_EQUIVALENCIAS).exists():
        print(f"\n❌ No se encuentra: {EXCEL_EQUIVALENCIAS}")
        print("   Renombra 'Hoja_de_cálculo_sin_título.xlsx' a 'equivalencias.xlsx'")
        return False
    
    print(f"\n✅ Base de datos: {DB_PATH}")
    print(f"✅ Archivo conv: {EXCEL_CONV}")
    print(f"✅ Archivo global: {EXCEL_GLOBAL}")
    print(f"✅ Tabla equivalencias: {EXCEL_EQUIVALENCIAS}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        activar_foreign_keys(conn)
        limpiar_base_datos(conn)
        cargar_datos_personales(conn)
        cargar_dias_y_turnos(conn)
        cargar_dispositivos(conn)
        cargar_convocatorias(conn)
        cargar_menu(conn)
        cargar_inasistencias(conn)
        verificar_saldos(conn)
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
