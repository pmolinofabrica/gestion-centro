#!/usr/bin/env python3
"""
Helper para crear conexiones a la BD con Foreign Keys activadas
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'

@contextmanager
def get_connection(db_path=None):
    """
    Context manager para obtener conexión con Foreign Keys activadas
    
    Uso:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tabla")
            conn.commit()
    """
    if db_path is None:
        db_path = DB_PATH
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Acceso por nombre de columna
    
    # ACTIVAR FOREIGN KEYS
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_simple_connection(db_path=None):
    """
    Obtiene conexión simple con Foreign Keys activadas
    IMPORTANTE: Debes cerrar manualmente con conn.close()
    
    Uso:
        conn = get_simple_connection()
        cursor = conn.cursor()
        # ... tu código ...
        conn.close()
    """
    if db_path is None:
        db_path = DB_PATH
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    return conn

# Ejemplo de uso
if __name__ == '__main__':
    # Opción 1: Context manager (recomendado)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as n FROM datos_personales")
        print(f"Agentes: {cursor.fetchone()['n']}")
    
    # Opción 2: Conexión simple
    conn = get_simple_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    print(f"Foreign Keys: {cursor.fetchone()[0]}")
    conn.close()
