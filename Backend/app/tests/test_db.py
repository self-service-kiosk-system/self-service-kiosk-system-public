import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_NUBE_URL")
#DATABASE_URL = os.getenv("DATABASE_LOCAL_URL")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa a Supabase")
        print(f"Resultado: {result.fetchone()}")
        
        # Verificar tablas existentes
        tables = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        print("\n📊 Tablas en la base de datos:")
        for table in tables:
            print(f"  - {table[0]}")
            
except Exception as e:
    print(f"❌ Error de conexión: {e}")