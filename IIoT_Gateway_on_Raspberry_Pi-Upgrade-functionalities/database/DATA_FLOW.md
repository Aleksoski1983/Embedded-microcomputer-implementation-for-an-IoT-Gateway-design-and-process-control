# Data Flow: Monitored Variables → PostgreSQL

## Overview

This document explains how OPC UA monitored variables create data records in the PostgreSQL database.

## Architecture

```
S7-1500 PLC (OPC UA Server)
    ↓
OPC UA Client Service (Polling)
    ↓
Database Service (PostgreSQL Writer)
    ↓
PostgreSQL sensor_data Table
```

## Step-by-Step Data Flow

### 1. **Adding Variables to Monitor**

**Location:** `app/api/opcua_routes.py` - `/opcua/client/monitor` endpoint

When you add a variable through the Variables page:

```python
# User selects variable from OPC UA browser
node_id = "ns=3;s=\"OPC_UA_Variables\".\"Temperature\""
browse_name = "Temperature"
data_type = "float"
store_to_postgres = True  # Enable database storage

# API saves to SQLite configuration database
variable_id = db_service.add_monitored_variable(
    node_id=node_id,
    browse_name=browse_name,
    data_type=data_type,
    unit=unit,
    store_to_postgres=True  # KEY FLAG
)
```

**SQLite Table:** `opcua_monitored_variables`
```sql
CREATE TABLE opcua_monitored_variables (
    id INTEGER PRIMARY KEY,
    node_id TEXT UNIQUE,
    browse_name TEXT,
    data_type TEXT,
    unit TEXT,
    enabled INTEGER DEFAULT 1,
    store_to_postgres INTEGER DEFAULT 0,  -- Controls PostgreSQL storage
    measurement_name TEXT,
    created_at TIMESTAMP
)
```

### 2. **Polling Loop (Current Implementation)**

**Location:** `app/services/opcua_client_service.py`

The system uses **polling** (not subscriptions) to read values periodically:

```python
class OPCUAClientService:
    def start_monitoring(self):
        """Start monitoring thread that polls variables"""
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
    
    def _monitoring_loop(self):
        """Main loop that reads values every 1 second"""
        while self.running:
            variables = db_service.get_monitored_variables(enabled_only=True)
            
            for var in variables:
                try:
                    # Read current value from PLC
                    node = self.client.get_node(var['node_id'])
                    value = node.get_value()
                    
                    # Check if this variable should be stored
                    if var.get('store_to_postgres'):
                        # Write to PostgreSQL
                        self._store_value(var, value)
                    
                except Exception as e:
                    logger.error(f"Error reading {var['browse_name']}: {e}")
            
            time.sleep(1)  # Poll every second
```

### 3. **Writing to PostgreSQL**

**Location:** `app/services/database_service.py`

When a monitored variable's value is read and `store_to_postgres=1`:

```python
def _store_value(self, variable_info, value):
    """Store variable value to PostgreSQL"""
    
    # Prepare data for PostgreSQL
    measurement = variable_info.get('measurement_name') or variable_info['browse_name']
    
    tags = {
        'source': 'opcua',
        'location': variable_info.get('browse_name', 'unknown')
    }
    
    fields = {
        variable_info['browse_name']: float(value)
    }
    
    # Write to PostgreSQL
    db_service.write_sensor_data(
        measurement=measurement,
        tags=tags,
        fields=fields,
        timestamp=datetime.now()
    )
```

**PostgreSQL Write Function:**

```python
def write_sensor_data(self, measurement: str, tags: Dict, fields: Dict, timestamp: datetime = None):
    """Write sensor data to PostgreSQL"""
    if not self.pg_pool:
        return False
    
    if timestamp is None:
        timestamp = datetime.now()
    
    conn = None
    try:
        conn = self.pg_pool.getconn()
        cursor = conn.cursor()
        
        # Insert each field as a separate row
        for field_name, field_value in fields.items():
            cursor.execute('''
                INSERT INTO sensor_data 
                (timestamp, measurement, source, location, field_name, field_value, unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                timestamp,
                measurement,
                tags.get('source', 'unknown'),
                tags.get('location', 'unknown'),
                field_name,
                float(field_value),
                tags.get('unit', None)
            ))
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"Error writing to PostgreSQL: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            self.pg_pool.putconn(conn)
```

### 4. **PostgreSQL Table Structure**

**Table:** `sensor_data`

```sql
CREATE TABLE sensor_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    measurement VARCHAR(255) NOT NULL,
    source VARCHAR(255),              -- 'opcua', 'mqtt'
    location VARCHAR(255),             -- Variable browse name
    field_name VARCHAR(255) NOT NULL,  -- Field being measured
    field_value DOUBLE PRECISION,      -- Numeric value
    unit VARCHAR(50)                   -- Unit of measurement
);

-- Indexes for fast queries
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp DESC);
CREATE INDEX idx_sensor_data_measurement ON sensor_data(measurement);
CREATE INDEX idx_sensor_data_measurement_timestamp ON sensor_data(measurement, timestamp DESC);
```

### 5. **Example Data Record**

When Temperature variable = 25.5°C is read from PLC:

```sql
INSERT INTO sensor_data VALUES (
    1,                          -- id (auto-increment)
    '2025-12-16 13:30:45+00',   -- timestamp
    'temperature',               -- measurement
    'opcua',                     -- source
    'Temperature',               -- location (variable name)
    'Temperature',               -- field_name
    25.5,                        -- field_value
    '°C'                         -- unit
);
```

## Query Examples

### Get latest values for all measurements:
```sql
SELECT DISTINCT ON (measurement)
    measurement,
    field_value,
    unit,
    timestamp
FROM sensor_data
ORDER BY measurement, timestamp DESC;
```

### Get temperature history for last hour:
```sql
SELECT 
    timestamp,
    field_value as temperature,
    unit
FROM sensor_data
WHERE measurement = 'temperature'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Get all data from a specific variable:
```sql
SELECT 
    timestamp,
    field_name,
    field_value,
    unit
FROM sensor_data
WHERE source = 'opcua'
  AND location = 'Temperature'
ORDER BY timestamp DESC
LIMIT 100;
```

## Data Retention

Currently, data is kept indefinitely. To implement retention:

```sql
-- Delete data older than 30 days
DELETE FROM sensor_data 
WHERE timestamp < NOW() - INTERVAL '30 days';
```

## Performance Optimization

### Connection Pooling
The system uses a connection pool (1-20 connections) to handle concurrent writes efficiently.

### Batch Writes (Recommendation)
For high-frequency data (< 1 second intervals), consider batching:

```python
# Buffer writes and insert every 5 seconds
write_buffer = []

def buffer_write(measurement, tags, fields, timestamp):
    write_buffer.append((measurement, tags, fields, timestamp))
    
    if len(write_buffer) >= 50:  # Flush every 50 records
        flush_buffer()

def flush_buffer():
    # Execute multi-row INSERT
    values = []
    for measurement, tags, fields, timestamp in write_buffer:
        for field_name, field_value in fields.items():
            values.append((timestamp, measurement, tags['source'], 
                          tags['location'], field_name, field_value, tags.get('unit')))
    
    cursor.executemany('''INSERT INTO sensor_data ...''', values)
    write_buffer.clear()
```

## Troubleshooting

### No data in PostgreSQL?

1. **Check variable configuration:**
   ```sql
   SELECT node_id, browse_name, enabled, store_to_postgres 
   FROM opcua_monitored_variables;
   ```
   Ensure `store_to_postgres = 1`

2. **Check PostgreSQL connection:**
   - Dashboard should show "PostgreSQL Connected"
   - Test connection in Configuration page

3. **Check application logs:**
   ```
   tail -f logs/iiot-gateway.log | grep "PostgreSQL"
   ```

4. **Verify table exists:**
   ```sql
   SELECT COUNT(*) FROM sensor_data;
   ```

5. **Check OPC UA connection:**
   - Variables page should show "Connected" status
   - Values should be updating in real-time

## Future Enhancements

1. **Subscription-based monitoring** (instead of polling)
2. **Configurable polling intervals** per variable
3. **Data aggregation** (min/max/avg per minute/hour)
4. **Automatic data retention** policies
5. **TimescaleDB** integration for better time-series performance
