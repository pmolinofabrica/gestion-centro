import os
import requests
from dotenv import load_dotenv

# Cargar entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Faltan credenciales en .env")
    exit(1)

def test_view_filter(anio, mes):
    print(f"\n🔍 Probando vista_convocatoria_completa para {mes}/{anio}...")
    
    # URL exacta que GAS intentaría construir
    url = f"{SUPABASE_URL}/rest/v1/vista_convocatoria_completa"
    params = {
        "select": "*",
        "anio": f"eq.{anio}",
        "mes": f"eq.{mes}"
    }
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        print(f"📡 URL llamada: {response.url}")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Registros encontrados: {len(data)}")
            if len(data) > 0:
                print("📝 Ejemplo primer registro:")
                print(f"   - Agente: {data[0].get('agente')}")
                print(f"   - Fecha: {data[0].get('fecha_turno')}")
                print(f"   - Estado: {data[0].get('estado')}")
            else:
                print("⚠️  La respuesta fue exitosa (200 OK) pero vacía [].")
                print("   Posibles causas: No hay datos para esa fecha o el filtro no coincide.")
        else:
            print(f"❌ Error API: {response.text}")
            
    except Exception as e:
        print(f"💥 Error de conexión: {str(e)}")

# Probar Octubre 2025
test_view_filter(2025, 10)
