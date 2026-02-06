#!/usr/bin/env python3
"""
ETL Capacitaciones 2025
-----------------------
Migra datos históricos de capacitaciones desde Excel a SQL.

Autor: Pablo
Fecha: 2025-02-06
Principios: DAMA (Integridad, Consistencia, Trazabilidad)
"""

import pandas as pd
import re
import json
from datetime import datetime

# --- CONFIGURACIÓN DE ARCHIVOS ---
# Usar pathlib para rutas robustas
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
QUERY_DIR = PROJECT_ROOT / "query_supabase"

# Archivo Excel fuente (contiene múltiples hojas)
EXCEL_FILE = QUERY_DIR / "registro cap 2025.xlsx"

# Mapeo de hojas del Excel (orden real: Hoja 1, Hoja 2, Hoja 4, Hoja 3)
SHEET_NAMES = {
    'SESSIONS': 0,     # Hoja 1: Dispositivos por sesión
    'ATTENDANCE': 1,   # Hoja 2: Asistencia
    'ABSENCES': 2      # Hoja 4: Inasistencias (índice 2 en el Excel)
}

OUTPUT_FILE = PROJECT_ROOT / "sql" / "seeds" / "migracion_2025_output.sql"

# --- FUNCIONES DE LIMPIEZA Y VALIDACIÓN ---

def clean_date(d):
    """Normaliza fechas, corrigiendo errores comunes (ej: 2026 → 2025)."""
    if pd.isna(d): 
        return None
    
    # Manejar objetos datetime de pandas/Excel
    if hasattr(d, 'strftime'):
        d_str = d.strftime('%Y-%m-%d')
    else:
        d_str = str(d).strip()
    
    # Corregir año erróneo (datos de prueba usaron 2026)
    if '2026' in d_str: 
        d_str = d_str.replace('2026', '2025')
    
    # Validar formato YYYY-MM-DD
    try:
        datetime.strptime(d_str, '%Y-%m-%d')
        return d_str
    except ValueError:
        return None

def clean_group(s):
    """Extrae el grupo (A, B, C) de un string con variaciones."""
    if pd.isna(s): 
        return 'A'
    s = str(s).upper().strip()
    match = re.search(r'[\\s-]((?:A|B|C)(?:\\s|$|COMPLETA))', s)
    if match: 
        return match.group(1).replace('COMPLETA', '').strip()
    if 'MADERA B' in s: 
        return 'B'
    return 'A'

def escape_sql(value):
    """Escapa comillas simples para prevenir SQL injection."""
    if value is None:
        return 'NULL'
    return str(value).replace("'", "''")

# --- PROCESO ETL ---

def run_etl():
    print("🔄 Iniciando proceso ETL para Capacitaciones 2025...")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    # 1. EXTRACCIÓN: Cargar Inasistencias (para filtrado posterior)
    print("📥 Cargando archivo de inasistencias...")
    try:
        df_abs = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAMES['ABSENCES'])
        df_abs['Fecha_Clean'] = df_abs['Falto a cap'].apply(clean_date)
        df_abs['Residente'] = df_abs['Residente'].astype(str).str.strip()
        # Hash Set para búsqueda O(1)
        absence_set = set(zip(df_abs['Residente'], df_abs['Fecha_Clean']))
        print(f"   ✓ {len(absence_set)} inasistencias cargadas")
    except Exception as e:
        print(f"   ⚠️ Error cargando inasistencias: {e}. Continuando sin filtro.")
        absence_set = set()

    # 2. EXTRACCIÓN: Cargar Sesiones y Dispositivos
    print("📥 Cargando archivo de sesiones...")
    df_dev = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAMES['SESSIONS'])
    df_dev['Fecha_Clean'] = df_dev['Fecha'].apply(clean_date)
    df_dev['Grupo_Clean'] = df_dev['Div. Grupo'].apply(clean_group)
    
    # Extraer dispositivos de columnas dinámicas usando SET para deduplicación automática
    device_cols = [c for c in df_dev.columns if c.lower().startswith('dispositivo')]
    
    # FILTRO 1: Dispositivos únicos por (Fecha, Grupo, Device)
    # Esto elimina duplicados dentro del mismo grupo Y entre grupos
    session_devices = set()
    for _, row in df_dev.iterrows():
        if pd.isna(row['Fecha_Clean']): 
            continue
        for col in device_cols:
            if col in row.index and pd.notna(row[col]) and str(row[col]).strip() != '':
                # Tupla única: (Fecha, Grupo, Device)
                session_devices.add((row['Fecha_Clean'], row['Grupo_Clean'], str(row[col]).strip()))
    
    df_sessions_dev = pd.DataFrame(list(session_devices), columns=['Fecha_Clean', 'Grupo_Clean', 'Device'])
    
    # Sesiones únicas (para crear capacitaciones)
    unique_sessions = df_sessions_dev[['Fecha_Clean', 'Grupo_Clean']].drop_duplicates().sort_values(by=['Fecha_Clean', 'Grupo_Clean'])
    print(f"   ✓ {len(unique_sessions)} sesiones únicas identificadas")
    print(f"   ✓ {len(df_sessions_dev)} dispositivos únicos (post-dedup)")

    # 3. EXTRACCIÓN: Cargar Asistencia
    print("📥 Cargando archivo de asistencia...")
    df_att = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAMES['ATTENDANCE'])
    df_att['Fecha_Clean'] = df_att['Fecha'].apply(clean_date)
    df_att['Grupo_Clean'] = df_att['Grupo'].apply(clean_group)
    # Detectar columnas de residentes dinámicamente
    res_cols = [c for c in df_att.columns[5:] if "Unnamed" not in c and ".1" not in c and c not in ['Total', 'Finalizada']]
    print(f"   ✓ {len(res_cols)} columnas de residentes detectadas")

    # 4. TRANSFORMACIÓN Y GENERACIÓN DE SQL
    print(f"✍️  Generando SQL para {len(unique_sessions)} sesiones...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- ============================================================\\n")
        f.write("-- MIGRACIÓN AUTOMÁTICA: Capacitaciones 2025\\n")
        f.write(f"-- Generado: {datetime.now().isoformat()}\\n")
        f.write("-- ============================================================\\n\\n")
        f.write("BEGIN;\\n\\n")

        # --- A. CREAR SESIONES (CAPACITACIONES) ---
        f.write("-- 1. CREACIÓN DE SESIONES\\n")
        f.write("-- Busca id_dia mediante JOIN con tabla dias\\n\\n")
        
        for _, row in unique_sessions.iterrows():
            fecha = escape_sql(row['Fecha_Clean'])
            grupo = escape_sql(row['Grupo_Clean'])
            sql = f"""
INSERT INTO capacitaciones (id_dia, coordinador_cap, tema, grupo, observaciones)
SELECT d.id_dia, 1, 'Capacitación Práctica 2025', '{grupo}', 'Migración ETL Automática'
FROM dias d
WHERE d.fecha = '{fecha}'
  AND NOT EXISTS (
      SELECT 1 FROM capacitaciones c 
      WHERE c.id_dia = d.id_dia AND c.grupo = '{grupo}'
  );
"""
            f.write(sql.strip() + "\\n\\n")

        # --- B. ASIGNAR DISPOSITIVOS ---
        f.write("\\n-- 2. ASIGNACIÓN DE DISPOSITIVOS\\n")
        f.write("-- Usa id_cap (no id_capacitacion) y ON CONFLICT para idempotencia\\n\\n")
        
        # Usar df_sessions_dev que ya está deduplicado
        for _, row in df_sessions_dev.iterrows():
            fecha = escape_sql(row['Fecha_Clean'])
            grupo = escape_sql(row['Grupo_Clean'])
            device = escape_sql(row['Device'])
            sql = f"""
INSERT INTO capacitaciones_dispositivos (id_cap, id_dispositivo, tiempo_minutos)
SELECT c.id_cap, disp.id_dispositivo, 60
FROM capacitaciones c
JOIN dias d ON c.id_dia = d.id_dia
JOIN dispositivos disp ON disp.nombre_dispositivo ILIKE '{device}'
WHERE d.fecha = '{fecha}' AND c.grupo = '{grupo}'
ON CONFLICT (id_cap, id_dispositivo) DO NOTHING;
"""
            f.write(sql.strip() + "\\n\\n")

        # --- C. ASIGNAR PARTICIPANTES ---
        f.write("\\n-- 3. ASIGNACIÓN DE PARTICIPANTES\\n")
        f.write("-- Bloque PL/pgSQL para lógica condicional\\n\\n")
        f.write("DO $$\\nDECLARE\\n  v_cap_id INT;\\n  v_agente_id INT;\\nBEGIN\\n\\n")
        
        for _, row in unique_sessions.iterrows():
            fecha = escape_sql(row['Fecha_Clean'])
            grupo = escape_sql(row['Grupo_Clean'])
            
            # Buscar asistentes en el DF de asistencia
            session_att = df_att[(df_att['Fecha_Clean'] == row['Fecha_Clean']) & (df_att['Grupo_Clean'] == row['Grupo_Clean'])]
            
            attendees = []
            if not session_att.empty:
                for _, s_row in session_att.iterrows():
                    for rc in res_cols:
                        val = str(s_row[rc]).lower().strip()
                        if val in ['1', 'true', '1.0']:
                            # FILTRO: Verificar que no esté en lista de inasistencias
                            if (rc.strip(), row['Fecha_Clean']) not in absence_set:
                                attendees.append(rc.strip())
            
            attendees = list(set(attendees))  # Desduplicar
            
            if attendees:
                f.write(f"  -- Sesión {fecha} Grupo {grupo} ({len(attendees)} asistentes)\\n")
                f.write(f"  SELECT c.id_cap INTO v_cap_id FROM capacitaciones c\\n")
                f.write(f"  JOIN dias d ON c.id_dia = d.id_dia\\n")
                f.write(f"  WHERE d.fecha = '{fecha}' AND c.grupo = '{grupo}';\\n\\n")
                
                f.write(f"  IF v_cap_id IS NOT NULL THEN\\n")
                
                for att in attendees:
                    att_safe = escape_sql(att)
                    f.write(f"    -- Participante: {att_safe}\\n")
                    f.write(f"    SELECT id_agente INTO v_agente_id FROM datos_personales\\n")
                    f.write(f"    WHERE CONCAT(nombre, ' ', apellido) ILIKE '%{att_safe}%' LIMIT 1;\\n")
                    f.write(f"    IF v_agente_id IS NOT NULL THEN\\n")
                    f.write(f"      INSERT INTO capacitaciones_participantes (id_cap, id_agente)\\n")
                    f.write(f"      VALUES (v_cap_id, v_agente_id)\\n")
                    f.write(f"      ON CONFLICT (id_cap, id_agente) DO NOTHING;\\n")
                    f.write(f"    END IF;\\n\\n")
                
                f.write(f"  END IF;\\n\\n")

        f.write("END $$;\\n\\n")
        f.write("COMMIT;\\n")
        f.write("\\n-- ============================================================\\n")
        f.write("-- FIN DE MIGRACIÓN\\n")
        f.write("-- ============================================================\\n")

    print(f"✅ ¡Éxito! Archivo generado: {OUTPUT_FILE}")
    print(f"   Sesiones procesadas: {len(unique_sessions)}")
    print(f"   Dispositivos únicos: {len(df_sessions_dev)}")

if __name__ == "__main__":
    run_etl()
