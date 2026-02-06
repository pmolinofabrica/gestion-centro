#!/usr/bin/env python3
"""Limpia datos de tests anteriores"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_connection_helper import get_connection

with get_connection() as conn:
    cursor = conn.cursor()
    
    # Eliminar agentes de prueba (conservar estructura)
    cursor.execute("DELETE FROM datos_personales")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='datos_personales'")
    
    # Eliminar planificaciones de prueba
    cursor.execute("DELETE FROM planificacion")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='planificacion'")
    
    # Eliminar descansos de prueba
    cursor.execute("DELETE FROM descansos")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='descansos'")
    
    print("✅ Datos de prueba limpiados")

