import psycopg2
from datetime import datetime

# PostgreSQL connection
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='iiot_gateway',
    user='iiot_user',
    password='iiot_password'
)

cursor = conn.cursor()

print("="*100)
print("POSTGRESQL DATA CHECK")
print("="*100)

# Check total records
cursor.execute("SELECT COUNT(*) FROM sensor_data")
total = cursor.fetchone()[0]
print(f"\n📊 Total records in PostgreSQL: {total}")

if total > 0:
    # Check records by variable
    cursor.execute("""
        SELECT 
            location,
            field_name,
            COUNT(*) as record_count,
            MIN(timestamp) as first_record,
            MAX(timestamp) as last_record,
            MAX(field_value) as last_value
        FROM sensor_data 
        WHERE source = 'opcua'
        GROUP BY location, field_name 
        ORDER BY last_record DESC
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n{'Variable':<30} {'Records':<10} {'First Record':<20} {'Last Record':<20} {'Last Value':<12}")
    print("-"*100)
    
    for r in rows:
        first = r[3].strftime('%Y-%m-%d %H:%M:%S') if r[3] else 'N/A'
        last = r[4].strftime('%Y-%m-%d %H:%M:%S') if r[4] else 'N/A'
        print(f"{r[0]:<30} {r[2]:<10} {first:<20} {last:<20} {r[5]:<12.2f}")
    
    # Show last 10 records
    print("\n" + "="*100)
    print("LAST 10 RECORDS:")
    print("="*100)
    
    cursor.execute("""
        SELECT timestamp, location, field_value, unit
        FROM sensor_data
        WHERE source = 'opcua'
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    records = cursor.fetchall()
    print(f"\n{'Timestamp':<20} {'Variable':<30} {'Value':<15} {'Unit':<10}")
    print("-"*100)
    
    for r in records:
        ts = r[0].strftime('%Y-%m-%d %H:%M:%S')
        unit = r[3] if r[3] else ''
        print(f"{ts:<20} {r[1]:<30} {r[2]:<15.2f} {unit:<10}")
    
    # Check how recent the data is
    cursor.execute("""
        SELECT MAX(timestamp) as latest, 
               EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) as seconds_ago
        FROM sensor_data
        WHERE source = 'opcua'
    """)
    
    result = cursor.fetchone()
    if result[0]:
        latest = result[0].strftime('%Y-%m-%d %H:%M:%S')
        seconds = int(result[1])
        print(f"\n⏱️  Latest record: {latest} ({seconds} seconds ago)")
        
        if seconds > 60:
            print(f"\n⚠️  WARNING: Last data is {seconds} seconds old - monitoring may not be running!")
        else:
            print(f"\n✅ Data is fresh! Monitoring is working correctly.")
else:
    print("\n❌ NO DATA IN POSTGRESQL!")
    print("\nPossible reasons:")
    print("  1. Variables are not ENABLED")
    print("  2. Variables don't have 'Store to DB' checked")
    print("  3. OPC UA client is not connected")
    print("  4. Monitoring is not started")
    print("  5. PostgreSQL connection failed during write")

cursor.close()
conn.close()

print("\n" + "="*100)
