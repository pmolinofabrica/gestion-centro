
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add src to path to allow importing if needed, but we will try to be standalone first
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def main():
    print("🚀 Starting migration execution...")
    
    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
    if os.path.exists(dotenv_path):
        print(f"📄 Loading .env from {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print("⚠️ Warning: .env file not found in parent directory")
    
    # Get database credentials from environment variables
    db_host = os.getenv('SUPABASE_DB_HOST')
    db_port = os.getenv('SUPABASE_DB_PORT')
    db_name = os.getenv('SUPABASE_DB_NAME')
    db_user = os.getenv('SUPABASE_DB_USER')
    db_password = os.getenv('SUPABASE_DB_PASSWORD')
    
    if not all([db_host, db_user, db_password]):
        print("❌ Error: Missing database credentials in .env")
        return

    # Path to SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), '../sql/rpc_matriz_certificaciones.sql')
    
    if not os.path.exists(sql_file_path):
        print(f"❌ Error: SQL file not found at {sql_file_path}")
        return
        
    print(f"📄 Reading SQL file: {sql_file_path}")
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    print(f"🔌 Connecting to Supabase at {db_host}...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            sslmode='require',
            connect_timeout=15
        )
        conn.autocommit = False # We want transaction
        
        cursor = conn.cursor()
        
        print("🔄 Executing SQL script...")
        # Execute the entire script
        cursor.execute(sql_content)
        
        print("✅ SQL Executed successfully. Committing transaction...")
        conn.commit()
        print("🎉 Migration completed successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database Error: {e}")
        if conn:
            print("ROLLBACK transaction...")
            conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("🔌 Connection closed.")

if __name__ == "__main__":
    main()
