
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/pablo/gestion-rrhh-centro/admin_tools/.env')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

def inspect_table(table_name):
    print(f"--- Inspecting {table_name} ---")
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?limit=1"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                print("Columns found (from data):")
                print(list(data[0].keys()))
                print("\nSample Data:")
                print(json.dumps(data[0], indent=2))
            else:
                print("Table is empty, cannot infer columns from data.")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

inspect_table('inasistencias')
inspect_table('certificados')
