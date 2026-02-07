"""
Loader Module
-------------
Genera artefactos de persistencia (SQL, JSON) idempotentes.

Principios DAMA: Trazabilidad, Reproducibilidad
"""

from datetime import datetime
from pathlib import Path
from typing import Set, Tuple
import pandas as pd


def escape_sql(value) -> str:
    """Escapa comillas simples para prevenir SQL injection."""
    if value is None:
        return 'NULL'
    return str(value).replace("'", "''")


def generate_session_inserts(
    sessions_df: pd.DataFrame,
    date_column: str = 'Fecha_Clean',
    group_column: str = 'Grupo_Clean'
) -> str:
    """
    Genera INSERT statements para sesiones.
    
    Usa WHERE NOT EXISTS para idempotencia.
    
    Args:
        sessions_df: DataFrame con sesiones únicas
        date_column: Nombre de columna de fecha
        group_column: Nombre de columna de grupo
    
    Returns:
        String SQL con todos los INSERTs
    """
    unique_sessions = sessions_df[[date_column, group_column]].drop_duplicates()
    
    sql_parts = ["-- CREACIÓN DE SESIONES"]
    sql_parts.append("-- Usa lookup por fecha y verificación de existencia previa\n")
    
    for _, row in unique_sessions.iterrows():
        fecha = escape_sql(row[date_column])
        grupo = escape_sql(row[group_column])
        
        sql = f"""
INSERT INTO capacitaciones (id_dia, coordinador_cap, tema, grupo, observaciones)
SELECT d.id_dia, 1, 'Capacitación Migrada', '{grupo}', 'ETL Automático'
FROM dias d
WHERE d.fecha = '{fecha}'
  AND NOT EXISTS (
      SELECT 1 FROM capacitaciones c 
      WHERE c.id_dia = d.id_dia AND c.grupo = '{grupo}'
  );
"""
        sql_parts.append(sql.strip())
    
    return '\n\n'.join(sql_parts)


    return '\n\n'.join(sql_parts)

    
def generate_resource_inserts(
    sessions_df: pd.DataFrame,
    default_time: int = 60
) -> str:
    """
    Genera INSERT statements para asignación de recursos.
    
    Usa ON CONFLICT DO NOTHING para idempotencia.
    
    Args:
        sessions_df: DataFrame con [Fecha_Clean, Grupo_Clean, Resource]
        default_time: Tiempo por defecto en minutos
    
    Returns:
        String SQL con todos los INSERTs
    """
    # Agrupar dispositivos únicos para no hacer inserts repetidos
    unique_resources = sessions_df[['Resource']].drop_duplicates()
        
    sql_parts = ["-- ASIGNACIÓN DE RECURSOS"]
    sql_parts.append("-- ON CONFLICT previene duplicados en re-ejecución\n")
    
    sql_parts.append("DO $$")
    sql_parts.append("DECLARE")
    sql_parts.append("  v_cap_id INT;")
    sql_parts.append("  v_disp_id INT;")
    sql_parts.append("BEGIN\n")
    
    for _, row in sessions_df.iterrows():
        fecha = escape_sql(row['Fecha_Clean'])
        grupo = escape_sql(row['Grupo_Clean'])
        device = row['Resource']
        
        device_safe = escape_sql(device)
        device_simple = remove_accents(device)
        device_simple_safe = escape_sql(device_simple)
        
        sql_parts.append(f"  -- Sesión {fecha} Grupo {grupo}: Asignar {device}")
        sql_parts.append(f"  SELECT c.id_cap INTO v_cap_id FROM capacitaciones c")
        sql_parts.append(f"  JOIN dias d ON c.id_dia = d.id_dia")
        sql_parts.append(f"  WHERE d.fecha = '{fecha}' AND c.grupo = '{grupo}';")
        
        # Búsqueda robusta: Intenta coincidencia directa OR coincidencia sin acentos
        sql_parts.append(f"  SELECT id_dispositivo INTO v_disp_id FROM dispositivos")
        sql_parts.append(f"  WHERE nombre_dispositivo ILIKE '{device_safe}' OR nombre_dispositivo ILIKE '{device_simple_safe}' LIMIT 1;")
        
        sql_parts.append(f"  IF v_cap_id IS NOT NULL AND v_disp_id IS NOT NULL THEN")
        sql_parts.append(f"    INSERT INTO capacitaciones_dispositivos (id_cap, id_dispositivo, tiempo_minutos)")
        sql_parts.append(f"    VALUES (v_cap_id, v_disp_id, {default_time})")
        sql_parts.append(f"    ON CONFLICT (id_cap, id_dispositivo) DO NOTHING;")
        sql_parts.append(f"  END IF;\n")

    sql_parts.append("END $$;")
    
    return '\n'.join(sql_parts)


import unicodedata

def remove_accents(input_str):
    """Normaliza y elimina acentos de un string."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def generate_participant_inserts(
    sessions_df: pd.DataFrame,
    attendance_set: Set[Tuple[str, str, str]]
) -> str:
    """
    Genera bloque PL/pgSQL para asignación de participantes.
    
    Busca entidades por nombre y las vincula a sesiones.
    Ahora respeta el GRUPO para evitar asignaciones duplicadas.
    """
    unique_sessions = sessions_df[['Fecha_Clean', 'Grupo_Clean']].drop_duplicates()
    
    # Agrupar attendance por keys: (fecha, grupo) -> set(entities)
    attendance_map = {}
    for fecha, grupo, entity in attendance_set:
        key = (fecha, grupo)
        if key not in attendance_map:
            attendance_map[key] = set()
        attendance_map[key].add(entity)
    
    sql_parts = ["-- ASIGNACIÓN DE PARTICIPANTES"]
    sql_parts.append("DO $$")
    sql_parts.append("DECLARE")
    sql_parts.append("  v_cap_id INT;")
    sql_parts.append("  v_entity_id INT;")
    sql_parts.append("BEGIN\n")
    
    for _, row in unique_sessions.iterrows():
        fecha = row['Fecha_Clean']
        grupo_raw = escape_sql(row['Grupo_Clean'])
        
        # Buscar entidades que match fecha Y grupo
        entities = attendance_map.get((fecha, grupo_raw), set())
        
        if not entities:
            continue
        
        sql_parts.append(f"  -- Sesión {fecha} Grupo {grupo_raw} ({len(entities)} participantes)")
        sql_parts.append(f"  SELECT c.id_cap INTO v_cap_id FROM capacitaciones c")
        sql_parts.append(f"  JOIN dias d ON c.id_dia = d.id_dia")
        sql_parts.append(f"  WHERE d.fecha = '{fecha}' AND c.grupo = '{grupo_raw}';\n")
        sql_parts.append(f"  IF v_cap_id IS NOT NULL THEN")
        
        for entity in entities:
            entity_simple = remove_accents(entity)
            entity_safe = escape_sql(entity_simple)
            
            # Lógica de búsqueda mejorada: Manejar formato "Apellido, Nombre"
            if ',' in entity_simple:
                parts = entity_simple.split(',')
                if len(parts) >= 2:
                    surname = parts[0].strip()
                    name = parts[1].strip()
                    surname_safe = escape_sql(surname)
                    name_safe = escape_sql(name)
                    
                    # Búsqueda FLEXIBLE:
                    # 1. Apellido aprox (por inicio)
                    # 2. Nombre aprox: DB startswith Excel OR Excel contains DB (para "Sol" vs "Maria Sol")
                    match_sql = f"""
                        apellido ILIKE '{surname_safe}%' 
                        AND (
                            nombre ILIKE '{name_safe}%' 
                            OR 
                            '{name_safe}' ILIKE CONCAT('%', nombre, '%')
                        )
                    """
                else:
                    match_sql = f"CONCAT(nombre, ' ', apellido) ILIKE '%{entity_safe}%'"
            else:
                # Búsqueda simple
                match_sql = f"CONCAT(nombre, ' ', apellido) ILIKE '%{entity_safe}%' OR CONCAT(apellido, ' ', nombre) ILIKE '%{entity_safe}%'"

            sql_parts.append(f"    -- Participante: {entity} (Buscado como: {entity_simple})")
            sql_parts.append(f"    SELECT id_agente INTO v_entity_id FROM datos_personales")
            sql_parts.append(f"    WHERE {match_sql} LIMIT 1;")
            
            sql_parts.append(f"    IF v_entity_id IS NOT NULL THEN")
            # VERIFICACIÓN ESTRICTA: Una persona = Un grupo por día
            # Si ya existe una asignación para este agente en ESTA fecha (en cualquier grupo), saltar.
            sql_parts.append(f"      PERFORM 1 FROM capacitaciones_participantes cp")
            sql_parts.append(f"      JOIN capacitaciones c2 ON cp.id_cap = c2.id_cap")
            sql_parts.append(f"      JOIN dias d2 ON c2.id_dia = d2.id_dia")
            sql_parts.append(f"      WHERE d2.fecha = '{fecha}' AND cp.id_agente = v_entity_id;")
            
            sql_parts.append(f"      IF NOT FOUND THEN")
            sql_parts.append(f"        INSERT INTO capacitaciones_participantes (id_cap, id_agente, asistio)")
            sql_parts.append(f"        VALUES (v_cap_id, v_entity_id, true)")
            sql_parts.append(f"        ON CONFLICT (id_cap, id_agente) DO NOTHING;")
            sql_parts.append(f"      END IF;")
            sql_parts.append(f"    END IF;\n")
        
        sql_parts.append(f"  END IF;\n")
    
    sql_parts.append("END $$;")
    
    return '\n'.join(sql_parts)


def write_migration_file(
    output_path: Path,
    session_sql: str,
    resource_sql: str,
    participant_sql: str,
    use_transactions: bool = True
) -> None:
    """
    Escribe el archivo SQL de migración completo.
    
    Args:
        output_path: Ruta de salida
        session_sql: SQL para crear sesiones
        resource_sql: SQL para asignar recursos
        participant_sql: SQL para asignar participantes
        use_transactions: Si wrappear en BEGIN/COMMIT
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- ============================================================\n")
        f.write("-- MIGRACIÓN ETL AUTOMÁTICA\n")
        f.write(f"-- Generado: {datetime.now().isoformat()}\n")
        f.write("-- ============================================================\n\n")
        
        if use_transactions:
            f.write("BEGIN;\n\n")
        
        f.write(session_sql)
        f.write("\n\n")
        f.write(resource_sql)
        f.write("\n\n")
        f.write(participant_sql)
        f.write("\n\n")
        
        if use_transactions:
            f.write("COMMIT;\n")
        
        f.write("\n-- ============================================================\n")
        f.write("-- FIN DE MIGRACIÓN\n")
        f.write("-- ============================================================\n")
    
    print(f"✅ Archivo generado: {output_path}")
