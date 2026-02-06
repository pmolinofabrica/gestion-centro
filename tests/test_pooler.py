import psycopg2
from dotenv import load_dotenv
import os

load_dotenv('.env')

# Construir connection string URI (formato que funciona con pooler)
user = os.getenv('SUPABASE_DB_USER')
password = os.getenv('SUPABASE_DB_PASSWORD')
host = os.getenv('SUPABASE_DB_HOST')
port = os.getenv('SUPABASE_DB_PORT')
database = os.getenv('SUPABASE_DB_NAME')

conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"

print('📋 Configuración:')
print(f'   Host: {host}')
print(f'   Puerto: {port}')
print(f'   Usuario: {user}')
print(f'   Password: {"*" * len(password)} ({len(password)} chars)')

print('\n🔌 Conectando al pooler...')
try:
    conn = psycopg2.connect(conn_string, connect_timeout=15)
    print('✅ Conexión PostgreSQL OK')
    
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM turnos')
    count = cursor.fetchone()[0]
    print(f'🔍 Turnos en Supabase: {count}')
    
    conn.close()
    print('✅ Todo funciona correctamente')
    
except Exception as e:
    print(f'❌ Error: {e}')
