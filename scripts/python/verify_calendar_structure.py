import sys
import os
import pandas as pd

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from db_connect import get_supabase_client

def check_calendar_structure():
    supabase = get_supabase_client()
    
    print("🔍 INSPECCIÓN DE 'calendario_dispositivos'")
    print("==========================================")
    
    try:
        # Fetch 1 row to see keys
        res = supabase.table('calendario_dispositivos').select('*').limit(1).execute()
        
        if res.data:
            cols = list(res.data[0].keys())
            print("✅ Columnas encontradas:", cols)
            
            if 'cupo_objetivo' in cols:
                print("   -> 'cupo_objetivo': EXISTE")
            else:
                print("   -> 'cupo_objetivo': ❌ FALTA (Posible causa del error)")
                
        else:
             print("⚠️ La tabla parece vacía (o sin permisos), no puedo leer columnas.")
             
        # Check permissions/RLS via SQL injection trick or just logical deduction
        # We can't easily check pg_class via PostgREST unless exposed.
        
    except Exception as e:
        print(f"❌ Error leyendo tabla: {e}")

if __name__ == "__main__":
    check_calendar_structure()
