"""
Extractor Module
----------------
Responsable de la ingesta de datos desde fuentes no estructuradas.
Aplica normalización básica de tipos y detección dinámica de esquemas.

Principios DAMA: Accesibilidad, Consistencia
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Tuple, Optional
import yaml


def load_config(config_path: Path) -> dict:
    """Carga la configuración YAML del ETL."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def clean_date(value, year_fixes: Dict[str, str] = None) -> Optional[str]:
    """
    Normaliza valores de fecha a formato ISO (YYYY-MM-DD).
    
    Aplica correcciones de año si se especifican (ej: errores de tipeo).
    
    Args:
        value: Valor crudo de fecha (datetime, string, o NaN)
        year_fixes: Diccionario de correcciones {buscar: reemplazar}
    
    Returns:
        String en formato YYYY-MM-DD o None si inválido
    """
    if pd.isna(value):
        return None
    
    # Manejar objetos datetime nativos
    if hasattr(value, 'strftime'):
        date_str = value.strftime('%Y-%m-%d')
    else:
        date_str = str(value).strip()
    
    # Aplicar correcciones de año
    if year_fixes:
        for find, replace in year_fixes.items():
            date_str = date_str.replace(find, replace)
    
    # Validar formato
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return None


def extract_exceptions(
    excel_path: Path,
    sheet_index: int,
    date_column: str,
    entity_column: str,
    year_fixes: Dict[str, str] = None
) -> Set[Tuple[str, str]]:
    """
    Extrae el conjunto de excepciones (ausencias) como hash set.
    
    Permite búsqueda O(1) para filtrado posterior.
    
    Args:
        excel_path: Ruta al archivo Excel
        sheet_index: Índice de la hoja
        date_column: Nombre de columna con fechas
        entity_column: Nombre de columna con identificador de entidad
        year_fixes: Correcciones de año a aplicar
    
    Returns:
        Set de tuplas (entity_id, date) para búsqueda rápida
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_index)
        df['_date_clean'] = df[date_column].apply(lambda x: clean_date(x, year_fixes))
        df['_entity_clean'] = df[entity_column].astype(str).str.strip()
        
        return set(zip(df['_entity_clean'], df['_date_clean']))
    except Exception as e:
        print(f"⚠️ Error extrayendo excepciones: {e}")
        return set()


def extract_sessions(
    excel_path: Path,
    sheet_index: int,
    date_column: str,
    group_column: str,
    resource_prefix: str,
    year_fixes: Dict[str, str] = None,
    default_group: str = 'A'
) -> pd.DataFrame:
    """
    Extrae sesiones con sus recursos asignados.
    
    Detecta dinámicamente las columnas de recursos y las normaliza.
    Retorna DataFrame con columnas: [Fecha_Clean, Grupo_Clean, Resource]
    
    Args:
        excel_path: Ruta al archivo Excel
        sheet_index: Índice de la hoja
        date_column: Nombre de columna con fechas
        group_column: Nombre de columna con grupo/categoría
        resource_prefix: Prefijo para detectar columnas de recursos
        year_fixes: Correcciones de año
        default_group: Valor por defecto si el grupo no se puede parsear
    
    Returns:
        DataFrame con sesiones normalizadas y deduplicadas
    """
    import re
    
    df = pd.read_excel(excel_path, sheet_name=sheet_index)
    df['Fecha_Clean'] = df[date_column].apply(lambda x: clean_date(x, year_fixes))
    
    # Parser dinámico de grupos
    def parse_group(val):
        if pd.isna(val):
            return default_group
        s = str(val).upper().strip()
        match = re.search(r'[\s-]([A-C])(?:\s|$|COMPLETA)', s)
        if match:
            return match.group(1)
        return default_group
    
    df['Grupo_Clean'] = df[group_column].apply(parse_group)
    
    # Detectar columnas de recursos dinámicamente
    resource_cols = [c for c in df.columns if str(c).lower().startswith(resource_prefix.lower())]
    
    # Usar SET para deduplicación automática O(1)
    sessions = set()
    for _, row in df.iterrows():
        if pd.isna(row['Fecha_Clean']):
            continue
        for col in resource_cols:
            if pd.notna(row[col]) and str(row[col]).strip():
                sessions.add((
                    row['Fecha_Clean'],
                    row['Grupo_Clean'],
                    str(row[col]).strip()
                ))
    
    return pd.DataFrame(list(sessions), columns=['Fecha_Clean', 'Grupo_Clean', 'Resource'])


def extract_attendance(
    excel_path: Path,
    sheet_index: int,
    date_column: str,
    group_column: str,
    entity_start_col: int,
    exclude_patterns: list,
    exception_set: Set[Tuple[str, str]],
    year_fixes: Dict[str, str] = None,
    default_group: str = 'A'
) -> Set[Tuple[str, str]]:
    """
    Extrae registros de participación, filtrando excepciones.
    
    Retorna set de (Fecha, Entity) para evitar duplicados por multi-grupo.
    
    Args:
        excel_path: Ruta al archivo Excel
        sheet_index: Índice de la hoja
        date_column: Nombre de columna con fechas
        group_column: Nombre de columna con grupo
        entity_start_col: Índice donde empiezan las columnas de entidades
        exclude_patterns: Patrones de columnas a excluir
        exception_set: Set de excepciones para filtrar
        year_fixes: Correcciones de año
        default_group: Valor por defecto para grupo
    
    Returns:
        Set de tuplas (date, entity) únicas
    """
    import re
    
    df = pd.read_excel(excel_path, sheet_name=sheet_index)
    df['Fecha_Clean'] = df[date_column].apply(lambda x: clean_date(x, year_fixes))
    
    # Detectar columnas de entidades
    entity_cols = []
    for col in df.columns[entity_start_col:]:
        col_str = str(col)
        if not any(pat in col_str for pat in exclude_patterns):
            entity_cols.append(col)
    
    # Parser dinámico de grupos (reusado)
    def parse_group(val):
        if pd.isna(val):
            return default_group
        s = str(val).upper().strip()
        match = re.search(r'[\s-]([A-C])(?:\s|$|COMPLETA)', s)
        if match:
            return match.group(1)
        return default_group

    df['Grupo_Clean'] = df[group_column].apply(parse_group)

    # Usar SET para pasar todos los registros (Fecha, Grupo, Entity)
    # La deduplicación se hace en SQL (loader.py) para elegir el mejor grupo disponible
    attendance = set()
    filtered_count = 0
    
    for _, row in df.iterrows():
        if pd.isna(row['Fecha_Clean']):
            continue
        for col in entity_cols:
            val = str(row[col]).lower().strip()
            if val in ['1', 'true', '1.0']:
                entity = str(col).strip()
                fecha = row['Fecha_Clean']
                grupo = row['Grupo_Clean']
                
                # Filtrar por excepciones
                if (entity, fecha) in exception_set:
                    filtered_count += 1
                    continue
                
                attendance.add((fecha, grupo, entity))
    
    print(f"   Filtradas por excepción: {filtered_count}")
    print(f"   Registros de asistencia (incluyendo multi-grupo): {len(attendance)}")
        
    return attendance
