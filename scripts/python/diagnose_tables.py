import sys
import os
import pandas as pd

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from db_connect import get_supabase_client

def diagnose():
    supabase = get_supabase_client()
    
    print("🔍 DIAGNÓSTICO DE TABLAS")
    print("========================")
    
    # 1. Inspect Convocatoria Columns (by fetching one row)
    print("\n1. Estructura de 'convocatoria':")
    try:
        res = supabase.table('convocatoria').select('*').limit(1).execute()
        if res.data:
            print("   Columnas detectadas:", list(res.data[0].keys()))
        else:
            print("   ⚠️ Tabla vacía o sin permisos de lectura.")
    except Exception as e:
        print(f"   ❌ Error leyendo convocatoria: {e}")

    # 2. Check Data for March 2025
    print("\n2. Datos de Marzo 2025:")
    try:
        # Check Calendario
        res_cal = supabase.table('calendario_dispositivos').select('count', count='exact').filter('fecha', 'gte', '2025-03-01').filter('fecha', 'lte', '2025-03-31').execute()
        print(f"   - Calendario (filas en Mar-25): {res_cal.count}")
        
        # Check Convocatoria - Try 'fecha_convocatoria' first, then 'fecha'
        try:
             res_conv = supabase.table('convocatoria').select('count', count='exact').filter('fecha_convocatoria', 'gte', '2025-03-01').filter('fecha_convocatoria', 'lte', '2025-03-31').execute()
             print(f"   - Convocatoria (filas en Mar-25 usando 'fecha_convocatoria'): {res_conv.count}")
        except:
             print("   - Falló 'fecha_convocatoria', probando 'fecha'...")
             res_conv = supabase.table('convocatoria').select('count', count='exact').filter('fecha', 'gte', '2025-03-01').filter('fecha', 'lte', '2025-03-31').execute()
             print(f"   - Convocatoria (filas en Mar-25 usando 'fecha'): {res_conv.count}")

    except Exception as e:
        print(f"   ❌ Error filtrando datos: {e}")

if __name__ == "__main__":
    diagnose()
