from sync_core import sync_sheet_to_table
import sys

# Nombre exacto de tu Google Sheet
SPREADSHEET_NAME = "carga 2026"

def main():
    print("--- Comenzando Proceso ETL Antigravity ---")
    
    # Opción A: Si ejecutas "python main.py nombre_tabla", carga solo esa tabla
    if len(sys.argv) > 1:
        table_to_load = sys.argv[1]
        sync_sheet_to_table(SPREADSHEET_NAME, table_to_load)
        
    # Opción B: Si ejecutas solo "python main.py", carga TODO en orden lógico
    else:
        # 1. Catálogos (Independientes)
        sync_sheet_to_table(SPREADSHEET_NAME, "dias")
        sync_sheet_to_table(SPREADSHEET_NAME, "turnos")
        
        # 2. Maestros (Personas)
        sync_sheet_to_table(SPREADSHEET_NAME, "datos_personales")
        
        # 3. Transaccionales (Dependen de los anteriores)
        # Nota: Planificación busca IDs de Días y Turnos automáticamente
        sync_sheet_to_table(SPREADSHEET_NAME, "planificacion")
        
        # 4. Asignaciones (Dependen de Planificación y Agentes)
        sync_sheet_to_table(SPREADSHEET_NAME, "convocatoria")

    print("--- Proceso Finalizado ---")

if __name__ == "__main__":
    main()