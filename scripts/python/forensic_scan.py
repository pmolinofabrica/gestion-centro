import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from db_connect import get_supabase_client

def scan_table_by_month(supabase, table_name, date_col):
    print(f"\n📊 Escaneando tabla '{table_name}' (Columna fecha: {date_col})")
    print(f"{'Mes':<10} | {'Filas':<10}")
    print("-" * 25)
    
    total = 0
    # Escanear todo 2025
    for month in range(1, 13):
        start_date = f"2025-{month:02d}-01"
        # Calcular fin de mes
        if month == 12:
            end_date = "2025-12-31"
        else:
            end_date = f"2025-{month+1:02d}-01" # Menor estricto que el 1 del mes siguiente
            
        try:
            res = supabase.table(table_name)\
                .select('count', count='exact')\
                .filter(date_col, 'gte', start_date)\
                .filter(date_col, 'lt', end_date)\
                .execute()
            
            count = res.count or 0
            if count > 0:
                print(f"2025-{month:02d}    | {count}")
            total += count
        except Exception as e:
            print(f"Error scanning {month}: {e}")
            
    if total == 0:
        print("⚠️  TABLA VACÍA en todo 2025")
    else:
        print(f"TOTAL 2025: {total}")

def main():
    supabase = get_supabase_client()
    print("🔍 DIAGNÓSTICO FORENSE DE DATOS")
    
    # 1. Calendario (Oferta)
    scan_table_by_month(supabase, 'calendario_dispositivos', 'fecha')
    
    # 2. Convocatoria (Demanda) - Verificamos nombre col fecha
    # Intentamos primero fetch one para ver estructura
    try:
        sample = supabase.table('convocatoria').select('*').limit(1).execute()
        cols = list(sample.data[0].keys()) if sample.data else []
        print("\nColumnas Convocatoria:", cols)
        
        date_col = 'fecha_convocatoria' if 'fecha_convocatoria' in cols else 'fecha'
        scan_table_by_month(supabase, 'convocatoria', date_col)
        
    except Exception as e:
        print(f"\n❌ Error inspeccionando convocatoria: {e}")

    # 3. Planificación (Es compleja: planificacion -> dias -> fecha)
    print("\n📊 Escaneando 'planificacion' (Join con 'dias')")
    print(f"{'Mes':<10} | {'Filas':<10}")
    print("-" * 25)
    
    total_plan = 0
    try:
        # Obtenemos dias primero
        for month in range(1, 13):
            start_date = f"2025-{month:02d}-01"
            if month == 12:
                end_date = "2025-12-31"
            else:
                end_date = f"2025-{month+1:02d}-01"
            
            # 1. Get IDs from 'dias'
            res_dias = supabase.table('dias').select('id_dia').filter('fecha', 'gte', start_date).filter('fecha', 'lt', end_date).execute()
            ids_dias = [d['id_dia'] for d in res_dias.data]
            
            if ids_dias:
                # 2. Count planificacion where id_dia IN ids_dias
                # Supabase-py 'in' filter requires tuple or list
                res_plan = supabase.table('planificacion').select('count', count='exact').in_('id_dia', ids_dias).execute()
                count = res_plan.count or 0
                if count > 0:
                    print(f"2025-{month:02d}    | {count}")
                total_plan += count
            
    except Exception as e:
        print(f"Error scanning planificacion: {e}")
        
    print(f"TOTAL 2025: {total_plan}")

if __name__ == "__main__":
    main()
