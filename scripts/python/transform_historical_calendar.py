import pandas as pd
import sys
import os

# Agregar path raiz para importar db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from db_connect import get_supabase_client

def main():
    print("🚀 Iniciando transformación de datos históricos...")
    
    # 1. Conectar a Supabase y obtener Lookups
    supabase = get_supabase_client()
    
    print("📥 Descargas tablas de referencia...")
    res_turnos = supabase.table('turnos').select('id_turno, tipo_turno').execute()
    res_disp = supabase.table('dispositivos').select('id_dispositivo, nombre_dispositivo').execute()
    
    # Crear diccionarios de mapeo (Nombre -> ID)
    # Normalizamos a lowercase y trim para evitar errores tontos
    map_turnos = {t['tipo_turno'].strip().lower(): t['id_turno'] for t in res_turnos.data}
    map_disp = {d['nombre_dispositivo'].strip().lower(): d['id_dispositivo'] for d in res_disp.data}
    
    # Mapeos manuales para corregir discrepancias Excel vs DB
    MANUAL_MAPPING_TURNOS = {
        'apertura al público': 1, # Asumimos ID 1 (verificar si es 4hs o 5hs)
        # Agregar otros si fallan
    }
    
    print(f"   - Turnos encontrados: {len(map_turnos)}")
    print(f"   - Dispositivos encontrados: {len(map_disp)}")

    # 2. Leer Excel
    input_file = 'query_supabase/asignaciones 25.xlsx'
    print(f"📖 Leyendo {input_file}...")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    # Normalizar columnas
    df.columns = [c.strip() for c in df.columns]
    # Esperamos: 'Fecha', 'Turno', 'Dispositivo'
    
    # 3. Procesar Data
    results = []
    errors = []
    
    # Agrupar para contar cupos (Fecha + Turno + Dispositivo)
    # Esto nos dice: "El 23/03 en Apertura, en el dispositivo X hubo 3 personas" -> Cupo = 3
    print("🔄 Agregando datos y calculando cupos...")
    
    # Asegurar fecha formato
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    grouped = df.groupby(['Fecha', 'Turno', 'Dispositivo']).size().reset_index(name='count')
    
    # Ahora agrupamos por Fecha + Turno para construir el string de la matriz
    # Queremos: Fecha, Turno, ConfigString ("id:cupo, id:cupo")
    
    matrix_rows = []
    
    for (fecha, turno_nombre), group in grouped.groupby(['Fecha', 'Turno']):
        
        # Validar Turno
        turno_key = str(turno_nombre).strip().lower()
        id_turno = map_turnos.get(turno_key)
        
        if not id_turno:
            # Intentar fallback manual
            id_turno = MANUAL_MAPPING_TURNOS.get(turno_key)
        
        if not id_turno:
            if turno_key not in errors:
                errors.append(f"Turno no encontrado: {turno_nombre}")
            continue
            
        config_entries = []
        
        for _, row in group.iterrows():
            disp_nombre = str(row['Dispositivo']).strip()
            disp_key = disp_nombre.lower()
            count = row['count']
            
            id_disp = map_disp.get(disp_key)
            
            if id_disp:
                config_entries.append(f"{id_disp}:{count}")
            else:
                 # Intentar matcheo parcial o loguear error
                 # Por ahora logueamos solo una vez por dispositivo
                 if disp_key not in errors:
                     errors.append(f"Dispositivo no encontrado: {disp_nombre}")

        if config_entries:
            config_str = ", ".join(config_entries)
            matrix_rows.append({
                'Fecha (YYYY-MM-DD)': fecha.strftime('%Y-%m-%d'),
                'Turno (ID)': id_turno,
                'Configuración': config_str,
                'Status': '' # Vacio para que GAS lo procese
            })
            
    # 4. Exportar
    output_file = 'query_supabase/carga_masiva_calendario_2025.csv'
    df_out = pd.DataFrame(matrix_rows)
    df_out.to_csv(output_file, index=False)
    
    print(f"✅ Transformación completada.")
    print(f"📄 Archivo generado: {output_file}")
    print(f"   - Filas generadas: {len(df_out)}")
    
    if errors:
        print("\n⚠️ ERRORES DE MAPEO (Revisar nombres en DB vs Excel):")
        for e in errors[:20]: # Mostrar primeros 20
            print(f"   - {e}")
        if len(errors) > 20: 
            print(f"   ... y {len(errors)-20} más.")

if __name__ == "__main__":
    main()
