import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_supabase_client() -> Client:
    """
    Retorna el cliente de Supabase autenticado usando las variables de entorno.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Faltan las variables SUPABASE_URL o SUPABASE_KEY en el archivo .env")
        
    return create_client(url, key)

def get_gspread_client():
    """
    Retorna el cliente de Google Sheets autenticado con service_account.json.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_file = "service_account.json"
    
    if not os.path.exists(creds_file):
        raise FileNotFoundError(f"No se encontró el archivo de credenciales: {creds_file}")
        
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    
    return client
