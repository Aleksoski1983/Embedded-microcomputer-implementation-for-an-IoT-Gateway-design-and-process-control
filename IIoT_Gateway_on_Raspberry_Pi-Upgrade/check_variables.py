import sqlite3
import sys

# Check monitored variables
conn = sqlite3.connect('database/iiot_gateway.db')
cursor = conn.cursor()

print("="*100)
print("MONITORED VARIABLES CONFIGURATION")
print("="*100)

cursor.execute('''
    SELECT id, browse_name, node_id, data_type, enabled, store_to_influxdb 
    FROM opcua_monitored_variables
''')
rows = cursor.fetchall()

print(f"\n{'ID':<4} {'Browse Name':<30} {'Node ID':<45} {'Type':<10} {'En':<4} {'DB':<4}")
print("-"*100)

for r in rows:
    node_short = r[2][:43] + "..." if len(r[2]) > 43 else r[2]
    enabled = "YES" if r[4] else "NO"
    store_db = "YES" if r[5] else "NO"
    print(f"{r[0]:<4} {r[1]:<30} {node_short:<45} {r[3]:<10} {enabled:<4} {store_db:<4}")

enabled_count = sum(1 for r in rows if r[4])
storing_count = sum(1 for r in rows if r[5])
active_count = sum(1 for r in rows if r[4] and r[5])

print("\n" + "="*100)
print(f"📊 Summary: {len(rows)} total | {enabled_count} enabled | {storing_count} store-to-db | {active_count} ACTIVE (enabled+storing)")
print("="*100)

if active_count == 0:
    print("\n⚠️  WARNING: No variables are both ENABLED and set to STORE TO DB!")
    print("   → Variables must be ENABLED=YES and DB=YES to log data to PostgreSQL")

conn.close()
