"""
Test script to verify monitoring loop is working
Checks PostgreSQL connectivity and shows live data being written
"""

import psycopg2
import time
from datetime import datetime

# PostgreSQL connection
conn_params = {
    'host': 'localhost',
    'port': 5432,
    'database': 'iiot_gateway',
    'user': 'iiot_user',
    'password': 'iiot_password'
}

def check_connection():
    """Test PostgreSQL connection"""
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print(f"✓ Connected to PostgreSQL")
        print(f"  Version: {version[0][:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTo fix authentication:")
        print("1. Open pgAdmin")
        print("2. Run the SQL in fix_postgres_user.sql")
        print("3. Or run: psql -U postgres -d iiot_gateway -f fix_postgres_user.sql")
        return False

def monitor_data_changes(duration_seconds=30):
    """Monitor sensor_data table for new records (change detection)"""
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Get initial count
        cursor.execute('SELECT COUNT(*) FROM sensor_data')
        initial_count = cursor.fetchone()[0]
        
        print(f"\n📊 Monitoring PostgreSQL for {duration_seconds} seconds...")
        print(f"Initial records: {initial_count}")
        print("-" * 80)
        
        start_time = time.time()
        last_count = initial_count
        changes_detected = 0
        
        while time.time() - start_time < duration_seconds:
            time.sleep(2)  # Check every 2 seconds
            
            cursor.execute('SELECT COUNT(*) FROM sensor_data')
            current_count = cursor.fetchone()[0]
            
            if current_count > last_count:
                new_records = current_count - last_count
                changes_detected += new_records
                
                # Get the latest records
                cursor.execute('''
                    SELECT timestamp, location, field_name, field_value
                    FROM sensor_data
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (new_records,))
                
                print(f"✓ {new_records} new record(s) detected:")
                for row in cursor.fetchall():
                    timestamp, location, field_name, value = row
                    print(f"  {timestamp.strftime('%H:%M:%S')} | {location:20s} | {field_name:20s} | {value}")
                
                last_count = current_count
            else:
                print(f"  Checking... ({int(time.time() - start_time)}s elapsed)")
        
        print("-" * 80)
        print(f"\n📈 Summary:")
        print(f"  Initial records: {initial_count}")
        print(f"  Final records:   {current_count}")
        print(f"  Changes detected: {changes_detected}")
        print(f"  Total unique variables: ", end="")
        
        cursor.execute('SELECT COUNT(DISTINCT location) FROM sensor_data')
        unique_vars = cursor.fetchone()[0]
        print(f"{unique_vars}")
        
        if changes_detected == 0:
            print("\n⚠️  No changes detected. Possible issues:")
            print("  1. OPC UA client not connected (check Variables page)")
            print("  2. No variables enabled for database storage")
            print("  3. Variable values haven't changed during monitoring period")
            print("  4. Monitoring loop not started (check application logs)")
            
            # Show configuration
            cursor.execute('''
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'sensor_data'
            ''')
            if cursor.fetchone()[0] == 0:
                print("  5. sensor_data table doesn't exist! Run init_postgresql.sql")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error monitoring data: {e}")

def show_current_data():
    """Show latest data points"""
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("\n📋 Latest data points (last 10 records):")
        print("-" * 80)
        
        cursor.execute('''
            SELECT timestamp, location, field_name, field_value
            FROM sensor_data
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                timestamp, location, field_name, value = row
                print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {location:20s} | {field_name:20s} | {value}")
        else:
            print("  (No data in database yet)")
        
        print("-" * 80)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error showing data: {e}")

if __name__ == "__main__":
    print("=" * 80)
    print("  OPC UA Monitoring Test - Change Detection Mode")
    print("=" * 80)
    
    if check_connection():
        show_current_data()
        monitor_data_changes(duration_seconds=30)
        
        print("\n✓ Test complete!")
        print("\nTo check data in pgAdmin, use:")
        print("  SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 20;")
    else:
        print("\n✗ Cannot proceed without database connection")
