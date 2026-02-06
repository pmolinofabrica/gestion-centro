"""
Transformer Module
------------------
Aplica reglas de negocio para transformar datos crudos en estructuras
listas para persistencia.

Principios DAMA: Integridad, Consistencia, Unicidad
"""

import pandas as pd
from typing import Set, Tuple, Dict, List


def resolve_entity_conflicts(
    attendance_set: Set[Tuple[str, str]],
    exception_set: Set[Tuple[str, str]]
) -> Set[Tuple[str, str]]:
    """
    Cruza los logs de actividad con la tabla de excepciones.
    
    Principio: La integridad del dato exige que no exista actividad 
    registrada si hay una excepción validada en la misma fecha.
    
    Args:
        attendance_set: Set de (fecha, entity) con registros de actividad
        exception_set: Set de (entity, fecha) con excepciones
    
    Returns:
        Set filtrado sin conflictos
    """
    valid_records = set()
    
    for fecha, entity in attendance_set:
        # Verificar si existe excepción (formato invertido en exception_set)
        if (entity, fecha) not in exception_set:
            valid_records.add((fecha, entity))
    
    return valid_records


def deduplicate_resources(
    sessions_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Elimina recursos duplicados dentro de la misma sesión.
    
    Un recurso solo puede ser asignado una vez por (fecha, grupo).
    Previene el "efecto multiplicador" de datos mal ingresados.
    
    Args:
        sessions_df: DataFrame con columnas [Fecha_Clean, Grupo_Clean, Resource]
    
    Returns:
        DataFrame deduplicado
    """
    return sessions_df.drop_duplicates(subset=['Fecha_Clean', 'Grupo_Clean', 'Resource'])


def merge_attendance_with_resources(
    attendance_set: Set[Tuple[str, str]],
    sessions_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Cruza asistencia con recursos para generar la matriz final.
    
    Cada entidad que asistió a una fecha se vincula con TODOS los
    recursos de esa fecha (independiente del grupo, para evitar
    fragmentación por multi-grupo).
    
    Args:
        attendance_set: Set de (fecha, entity)
        sessions_df: DataFrame con recursos por sesión
    
    Returns:
        DataFrame con columnas [Entity, Resource, Date]
    """
    # Convertir attendance a DataFrame
    df_att = pd.DataFrame(list(attendance_set), columns=['Fecha', 'Entity'])
    
    # Recursos únicos por fecha (ignorar grupo para el merge)
    df_res = sessions_df.drop_duplicates(subset=['Fecha_Clean', 'Resource'])[['Fecha_Clean', 'Resource']]
    df_res.columns = ['Fecha', 'Resource']
    
    # Merge
    merged = pd.merge(df_att, df_res, on='Fecha')
    
    return merged


def calculate_repetitions(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas de repetición por entidad/recurso.
    
    Útil para auditoría de calidad de datos.
    
    Args:
        merged_df: DataFrame con [Entity, Resource, Fecha]
    
    Returns:
        DataFrame con conteo y fechas agrupadas
    """
    grouped = merged_df.groupby(['Entity', 'Resource'])['Fecha'].agg([
        'count',
        lambda x: ', '.join(sorted(list(set(x))))
    ]).reset_index()
    
    grouped.columns = ['Entity', 'Resource', 'Count', 'Dates']
    
    return grouped.sort_values('Count', ascending=False)
