#!/usr/bin/env python3
"""
EXTRACTOR DE REGISTROS NO CARGADOS v1.0
======================================

Genera archivos Excel con los registros que tienen datos reales
pero no se cargaron en la base de datos.

Output:
- data/no_cargados_convocatorias.xlsx
- data/no_cargados_menu.xlsx
- data/no_cargados_inasistencias.xlsx
"""

import pandas as pd
import sqlite3
from pathlib import Path
import unicodedata

# ==========================
# CONFIGURACIÓN
# ==========================
DB_PATH = 'data/gestion_rrhh.db'
EXCEL_CONV = 'data/conv.xlsx'
EXCEL_GLOBAL = 'data/global.xlsx'
EXCEL_EQUIVALENCIAS = 'data/equivalencias.xlsx'

# Archivos de salida
OUTPUT_CONV = 'data/no_cargados_convocatorias.xlsx'
OUTPUT_MENU = 'data/no_cargados_menu.xlsx'
OUTPUT_INAS = 'data/no_cargados_inasistencias.xlsx'

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


# ==========================
# EXTRACTORES
# ==========================

def extraer_convocatorias_no_cargadas():
    """Extrae convocatorias con datos que no se cargaron"""
    print("\n[1/3] Analizando CONVOCATORIAS no cargadas...")
    
    # Leer Excel
    df = pd.read_excel(EXCEL_CONV, sheet_name='Convocatoria')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(r['NOMBRE Y APELLIDO']).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025'])
    }
    
    # Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    # Procesar cada fila
    no_cargadas = []
    
    for idx, row in df.iterrows():
        # Saltar filas vacías
        if fila_vacia(row, ['Dia', 'Residente', 'Turno']):
            continue
        
        # Parsear fecha
        fecha = pd.to_datetime(row.get('Dia'), errors='coerce')
        if pd.isna(fecha):
            no_cargadas.append({
                'fila_excel': idx + 2,  # +2 porque Excel empieza en 1 y tiene header
                'fecha': row.get('Dia'),
                'residente': row.get('Residente'),
                'turno': row.get('Turno'),
                'mes': row.get('Mes'),
                'motivo_no_carga': 'Fecha inválida'
            })
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        
        # Verificar rango
        if not ('2025-07-01' <= fecha_str <= '2025-12-31'):
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'turno': row.get('Turno'),
                'mes': row.get('Mes'),
                'motivo_no_carga': f'Fuera de rango (jul-dic 2025)'
            })
            continue
        
        # Verificar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        
        if not apellido:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'turno': row.get('Turno'),
                'mes': row.get('Mes'),
                'motivo_no_carga': 'Alias no encontrado en tabla equivalencias'
            })
            continue
        
        if apellido not in agentes:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'turno': row.get('Turno'),
                'mes': row.get('Mes'),
                'motivo_no_carga': 'Residente no encontrado en BD'
            })
            continue
        
        id_agente = agentes[apellido]
        
        # Verificar si existe en BD
        cursor.execute("""
            SELECT COUNT(*) FROM convocatoria 
            WHERE id_agente = ? AND fecha_convocatoria = ?
        """, (id_agente, fecha_str))
        
        if cursor.fetchone()[0] == 0:
            # No está en BD, determinar por qué
            cursor.execute("SELECT numero_dia_semana FROM dias WHERE fecha = ?", (fecha_str,))
            dia_row = cursor.fetchone()
            
            if not dia_row:
                motivo = 'Día no existe en tabla dias'
            else:
                dia_semana = dia_row[0]
                turno_raw = normalizar(row.get('Turno'))
                tipo = 'capacitacion'
                if 'apertura' in turno_raw:
                    tipo = 'apertura_publico'
                elif 'tarde' in turno_raw:
                    tipo = 'tarde'
                elif 'manana' in turno_raw:
                    tipo = 'mañana'
                
                cursor.execute("""
                    SELECT COUNT(*) FROM turnos 
                    WHERE numero_dia_semana = ? AND tipo_turno = ?
                """, (dia_semana, tipo))
                
                if cursor.fetchone()[0] == 0:
                    motivo = f'Turno no existe ({tipo} para día {dia_semana})'
                else:
                    motivo = 'Error de inserción (posible duplicado)'
            
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'turno': row.get('Turno'),
                'mes': row.get('Mes'),
                'motivo_no_carga': motivo
            })
    
    conn.close()
    
    # Crear DataFrame y guardar
    if no_cargadas:
        df_no_cargadas = pd.DataFrame(no_cargadas)
        df_no_cargadas.to_excel(OUTPUT_CONV, index=False)
        print(f"  ✅ {len(no_cargadas)} registros con datos extraídos → {OUTPUT_CONV}")
    else:
        print(f"  ℹ️  No hay registros con datos sin cargar")
    
    return len(no_cargadas)


def extraer_menu_no_cargado():
    """Extrae asignaciones de menu con datos que no se cargaron"""
    print("\n[2/3] Analizando ASIGNACIONES (MENU) no cargadas...")
    
    # Leer Excel
    df = pd.read_excel(EXCEL_CONV, sheet_name='Menu')
    df_eq = pd.read_excel(EXCEL_EQUIVALENCIAS)
    
    # Mapeo alias → apellido
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(r['NOMBRE Y APELLIDO']).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025'])
    }
    
    # Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    cursor.execute("SELECT id_dispositivo, nombre_dispositivo FROM dispositivos")
    dispositivos = {normalizar(d): i for i, d in cursor.fetchall()}
    
    # Procesar cada fila
    no_cargadas = []
    
    for idx, row in df.iterrows():
        # Saltar filas vacías
        if fila_vacia(row, ['Fecha', 'Residente', 'Dispositivo']):
            continue
        
        # Parsear fecha
        fecha = pd.to_datetime(row.get('Fecha'), errors='coerce')
        if pd.isna(fecha):
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': row.get('Fecha'),
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': 'Fecha inválida'
            })
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        
        # Verificar rango
        if not ('2025-07-01' <= fecha_str <= '2025-12-31'):
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': 'Fuera de rango (jul-dic 2025)'
            })
            continue
        
        # Verificar dispositivo
        disp_raw = normalizar(row.get('Dispositivo'))
        if disp_raw not in dispositivos:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': 'Dispositivo no encontrado en BD'
            })
            continue
        
        # Verificar residente
        alias = normalizar(row.get('Residente'))
        apellido = alias_map.get(alias)
        
        if not apellido:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': 'Alias no encontrado en tabla equivalencias'
            })
            continue
        
        if apellido not in agentes:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': 'Residente no encontrado en BD'
            })
            continue
        
        id_agente = agentes[apellido]
        id_dispositivo = dispositivos[disp_raw]
        
        # Verificar si existe en BD
        cursor.execute("""
            SELECT COUNT(*) FROM menu 
            WHERE id_agente = ? AND fecha_asignacion = ? AND id_dispositivo = ?
        """, (id_agente, fecha_str, id_dispositivo))
        
        if cursor.fetchone()[0] == 0:
            # No está en BD, verificar si existe convocatoria
            cursor.execute("""
                SELECT COUNT(*) FROM convocatoria 
                WHERE id_agente = ? AND fecha_convocatoria = ?
            """, (id_agente, fecha_str))
            
            if cursor.fetchone()[0] == 0:
                motivo = 'Sin convocatoria correspondiente'
            else:
                motivo = 'Error de inserción (posible duplicado)'
            
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente'),
                'dispositivo': row.get('Dispositivo'),
                'turno': row.get('Turno'),
                'orden': row.get('Orden'),
                'motivo_no_carga': motivo
            })
    
    conn.close()
    
    # Crear DataFrame y guardar
    if no_cargadas:
        df_no_cargadas = pd.DataFrame(no_cargadas)
        df_no_cargadas.to_excel(OUTPUT_MENU, index=False)
        print(f"  ✅ {len(no_cargadas)} registros con datos extraídos → {OUTPUT_MENU}")
    else:
        print(f"  ℹ️  No hay registros con datos sin cargar")
    
    return len(no_cargadas)


def extraer_inasistencias_no_cargadas():
    """Extrae inasistencias con datos que no se cargaron"""
    print("\n[3/3] Analizando INASISTENCIAS no cargadas...")
    
    # Leer Excel
    df = pd.read_excel(EXCEL_GLOBAL, sheet_name='Inasistencias')
    
    # Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes = {normalizar(a): i for i, a in cursor.fetchall()}
    
    # Procesar cada fila
    no_cargadas = []
    
    for idx, row in df.iterrows():
        # Saltar filas vacías
        if fila_vacia(row, ['Fecha de la inasistencia', 'Fecha', 'Residente', 'Residente cultural ']):
            continue
        
        # Parsear fecha
        fecha_raw = row.get('Fecha de la inasistencia') or row.get('Fecha')
        fecha = pd.to_datetime(fecha_raw, errors='coerce')
        
        if pd.isna(fecha):
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_raw,
                'residente': row.get('Residente') or row.get('Residente cultural '),
                'motivo': row.get('Motivo de la ausencia'),
                'marca_temporal': row.get('Marca temporal'),
                'motivo_no_carga': 'Fecha inválida'
            })
            continue
        
        fecha_str = fecha.strftime('%Y-%m-%d')
        
        # Verificar rango
        if not ('2025-07-01' <= fecha_str <= '2025-12-31'):
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': row.get('Residente') or row.get('Residente cultural '),
                'motivo': row.get('Motivo de la ausencia'),
                'marca_temporal': row.get('Marca temporal'),
                'motivo_no_carga': f'Fuera de rango (jul-dic 2025) - es {fecha_str[:7]}'
            })
            continue
        
        # Verificar residente
        residente_raw = row.get('Residente') or row.get('Residente cultural ')
        residente_norm = normalizar(residente_raw)
        
        # Buscar por apellido
        id_agente = None
        if ',' in residente_norm:
            apellido = residente_norm.split(',')[0].strip()
            id_agente = agentes.get(apellido)
        else:
            tokens = residente_norm.split()
            if tokens:
                apellido_compuesto = ' '.join(tokens[:-1])
                id_agente = agentes.get(apellido_compuesto) or agentes.get(tokens[0])
        
        if not id_agente:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': residente_raw,
                'motivo': row.get('Motivo de la ausencia'),
                'marca_temporal': row.get('Marca temporal'),
                'motivo_no_carga': 'Residente no encontrado en BD'
            })
            continue
        
        # Verificar si existe en BD
        cursor.execute("""
            SELECT COUNT(*) FROM inasistencias 
            WHERE id_agente = ? AND fecha_inasistencia = ?
        """, (id_agente, fecha_str))
        
        if cursor.fetchone()[0] == 0:
            no_cargadas.append({
                'fila_excel': idx + 2,
                'fecha': fecha_str,
                'residente': residente_raw,
                'motivo': row.get('Motivo de la ausencia'),
                'marca_temporal': row.get('Marca temporal'),
                'motivo_no_carga': 'Error de inserción (posible duplicado)'
            })
    
    conn.close()
    
    # Crear DataFrame y guardar
    if no_cargadas:
        df_no_cargadas = pd.DataFrame(no_cargadas)
        df_no_cargadas.to_excel(OUTPUT_INAS, index=False)
        print(f"  ✅ {len(no_cargadas)} registros con datos extraídos → {OUTPUT_INAS}")
    else:
        print(f"  ℹ️  No hay registros con datos sin cargar")
    
    return len(no_cargadas)


# ==========================
# MAIN
# ==========================

def main():
    print_header("EXTRACTOR DE REGISTROS NO CARGADOS")
    print("""
Este script analiza los archivos Excel y extrae los registros
que tienen datos reales pero NO se cargaron en la base de datos.
    
Se excluyen:
  • Filas completamente vacías
  • Filas con solo valores nulos
    
Se generarán 3 archivos Excel con los registros NO cargados:
  1. data/no_cargados_convocatorias.xlsx
  2. data/no_cargados_menu.xlsx
  3. data/no_cargados_inasistencias.xlsx
""")
    
    # Verificar archivos
    for f in [DB_PATH, EXCEL_CONV, EXCEL_GLOBAL, EXCEL_EQUIVALENCIAS]:
        if not Path(f).exists():
            print(f"❌ Falta archivo: {f}")
            return False
    
    # Extraer registros no cargados
    total_conv = extraer_convocatorias_no_cargadas()
    total_menu = extraer_menu_no_cargado()
    total_inas = extraer_inasistencias_no_cargadas()
    
    # Resumen
    print_header("RESUMEN DE EXTRACCIÓN")
    print(f"""
  📋 Archivos generados:
    
    1. {OUTPUT_CONV}
       • {total_conv} convocatorias con datos NO cargadas
       
    2. {OUTPUT_MENU}
       • {total_menu} asignaciones con datos NO cargadas
       
    3. {OUTPUT_INAS}
       • {total_inas} inasistencias con datos NO cargadas
       
  📊 Total registros con datos extraídos: {total_conv + total_menu + total_inas}
  
  ℹ️  Cada archivo incluye:
     • Fila original del Excel (fila_excel)
     • Datos del registro
     • Motivo específico de por qué no se cargó
""")
    
    if total_conv + total_menu + total_inas == 0:
        print("  ✅ ¡Todos los registros con datos se cargaron correctamente!")
    else:
        print("  📝 Revisa los archivos para analizar los registros no cargados")
    
    print("\n" + "=" * 70 + "\n")
    return True


if __name__ == '__main__':
    import sys
    ok = main()
    sys.exit(0 if ok else 1)