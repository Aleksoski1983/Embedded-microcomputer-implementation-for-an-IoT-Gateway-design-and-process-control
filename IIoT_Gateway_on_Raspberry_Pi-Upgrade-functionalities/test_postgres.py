"""Test PostgreSQL Connection"""
import psycopg2
from app.config import Config

print("Testing PostgreSQL Connection...")
print(f"Host: {Config.POSTGRES_HOST}")
print(f"Port: {Config.POSTGRES_PORT}")
print(f"Database: {Config.POSTGRES_DB}")
print(f"User: {Config.POSTGRES_USER}")
print()

try:
    conn = psycopg2.connect(
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        database=Config.POSTGRES_DB,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        connect_timeout=5
    )
    
    print("✓ Connection successful!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"✓ PostgreSQL version: {version}")
    
    # Check if tables exist
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    
    if tables:
        print(f"\n✓ Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("\n⚠ No tables found in database")
    
    cursor.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print(f"✗ Connection failed: {e}")
    print("\nPossible issues:")
    print("  1. PostgreSQL service is not running")
    print("  2. Database 'iiot_gateway' doesn't exist")
    print("  3. Username/password incorrect")
    print("  4. PostgreSQL not accepting connections on localhost:5432")
    
except Exception as e:
    print(f"✗ Error: {e}")
