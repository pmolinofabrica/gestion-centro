#!/usr/bin/env python3
"""
Script para activar Foreign Keys en la base de datos SQLite
y verificar que estén activadas correctamente
"""

import sqlite3
import sys
from pathlib import Path

def activar_foreign_keys(db_path):
    """Activa las Foreign Keys en la base de datos"""
    
    print("="*70)
    print("  ACTIVACIÓN DE FOREIGN KEYS")
    print("="*70)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar estado actual
        cursor.execute("PRAGMA foreign_keys")
        estado_antes = cursor.fetchone()[0]
        print(f"\n1. Estado actual: {'ACTIVADAS ✓' if estado_antes else 'DESACTIVADAS ✗'}")
        
        # Activar Foreign Keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verificar que se activaron
        cursor.execute("PRAGMA foreign_keys")
        estado_despues = cursor.fetchone()[0]
        print(f"2. Después de activar: {'ACTIVADAS ✓' if estado_despues else 'DESACTIVADAS ✗'}")
        
        if estado_despues:
            print("\n✅ Foreign Keys activadas correctamente")
            
            # Verificar integridad
            print("\n3. Verificando integridad referencial...")
            cursor.execute("PRAGMA foreign_key_check")
            errores = cursor.fetchall()
            
            if errores:
                print(f"⚠️  Se encontraron {len(errores)} problemas de integridad:")
                for error in errores[:5]:  # Mostrar primeros 5
                    print(f"   - {error}")
            else:
                print("✅ Sin problemas de integridad referencial")
            
            # Guardar configuración (nota: en SQLite es por sesión)
            print("\n⚠️  IMPORTANTE:")
            print("   Foreign Keys en SQLite son POR SESIÓN.")
            print("   Cada conexión debe activarlas con: PRAGMA foreign_keys = ON")
            print("\n   En Python, hazlo así:")
            print("   ```python")
            print("   conn = sqlite3.connect('data/gestion_rrhh.db')")
            print("   conn.execute('PRAGMA foreign_keys = ON')")
            print("   ```")
            
        else:
            print("\n❌ No se pudieron activar las Foreign Keys")
            print("   Verifica que tu versión de SQLite soporte FKs (3.6.19+)")
        
        conn.close()
        return estado_despues
        
    except sqlite3.Error as e:
        print(f"\n❌ Error: {e}")
        return False

def crear_helper_connection():
    """Crea un helper para conexiones con FKs activadas"""
    
    helper_path = Path(__file__).parent / 'db_connection_helper.py'
    
    helper_code = '''#!/usr/bin/env python3
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
'''
    
    with open(helper_path, 'w') as f:
        f.write(helper_code)
    
    print(f"\n4. Helper creado: {helper_path}")
    print("   Ahora puedes importar: from db_connection_helper import get_connection")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'data/gestion_rrhh.db'
    
    if not Path(db_path).exists():
        print(f"❌ Error: No se encuentra {db_path}")
        sys.exit(1)
    
    success = activar_foreign_keys(db_path)
    
    if success:
        print("\n" + "="*70)
        crear_helper_connection()
        print("="*70)
    
    sys.exit(0 if success else 1)
