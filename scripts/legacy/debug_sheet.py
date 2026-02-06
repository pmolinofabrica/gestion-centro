import json
from db_connect import get_gspread_client

# Configuración
SPREADSHEET_NAME = "carga 2026"
TAB_NAME = "planificacion"

def debug_headers():
    print(f"\n🕵️‍♂️ --- INICIANDO DIAGNÓSTICO FORENSE: {TAB_NAME} ---")
    
    try:
        g_client = get_gspread_client()
        spreadsheet = g_client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.worksheet(TAB_NAME)
    except Exception as e:
        print(f"❌ Error Fatal conectando a Google Sheet: {e}")
        return

    # 1. ANÁLISIS DE LA FILA 1 (ENCABEZADOS)
    print("\n--- 1. ANÁLISIS DE ENCABEZADOS (Fila 1) ---")
    headers = worksheet.row_values(1)
    
    print(f"Lista completa cruda: {headers}")
    print(f"Cantidad de columnas detectadas: {len(headers)}")
    
    print("\n🔍 Inspección Rayos-X (Buscando espacios o caracteres invisibles):")
    for index, h in enumerate(headers):
        # Imprimimos la longitud y representacion oficial (repr) para ver caracteres ocultos
        print(f"   Col {index+1}: '{h}' | Longitud: {len(h)} | Repr: {repr(h)}")
        
        if h.lower().strip() == "fecha":
            print("      ✅ Esta columna PARECE ser 'fecha'.")
        else:
            if "fecha" in h.lower():
                print("      ⚠️ ALERTA: Contiene 'fecha' pero tiene basura extra.")

    # 2. ANÁLISIS DE LA FILA 2 (DATOS)
    print("\n--- 2. ANÁLISIS DE DATOS (Fila 2) ---")
    row_2 = worksheet.row_values(2)
    print(f"Valores crudos Fila 2: {row_2}")
    
    # 3. PRUEBA DE LIBRERÍA (get_all_records)
    print("\n--- 3. PRUEBA DE INTERPRETACIÓN (get_all_records) ---")
    # Esto es lo que usa el script normalmente. Si esto falla, aquí veremos por qué.
    try:
        records = worksheet.get_all_records()
        if records:
            first_row = records[0]
            print("Python convirtió la primera fila en este diccionario:")
            print(json.dumps(first_row, indent=4, default=str))
            
            # Verificación específica del campo problemático
            val_fecha = first_row.get('fecha')
            print(f"\nValor recuperado con clave exacta 'fecha': {repr(val_fecha)}")
            
            if val_fecha is None:
                print("❌ ERROR CONFIRMADO: La clave 'fecha' no existe en el diccionario.")
                print("   Claves disponibles:", list(first_row.keys()))
        else:
            print("⚠️ La hoja no tiene datos (get_all_records vacío).")
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO al leer registros: {e}")

if __name__ == "__main__":
    debug_headers()