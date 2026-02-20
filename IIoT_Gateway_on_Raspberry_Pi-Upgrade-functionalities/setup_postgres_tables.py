"""
Setup PostgreSQL Configuration Tables
Reads and executes the init_postgresql.sql file
"""

import psycopg2
from app.config import Config

def setup_postgres_tables():
    """Create configuration tables in PostgreSQL"""
    
    # First, connect to default 'postgres' database to create our database
    try:
        conn = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database='postgres',
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{Config.POSTGRES_DB}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database: {Config.POSTGRES_DB}")
            cursor.execute(f"CREATE DATABASE {Config.POSTGRES_DB}")
            print("Database created successfully")
        else:
            print(f"Database {Config.POSTGRES_DB} already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
    
    # Now connect to the target database and create tables
    try:
        conn = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        
        print(f"\nConnected to database: {Config.POSTGRES_DB}")
        
        # Create sensor_data table
        print("Creating sensor_data table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id BIGSERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                measurement VARCHAR(255) NOT NULL,
                source VARCHAR(255),
                location VARCHAR(255),
                field_name VARCHAR(255) NOT NULL,
                field_value DOUBLE PRECISION,
                unit VARCHAR(50)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement ON sensor_data(measurement)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement_timestamp ON sensor_data(measurement, timestamp DESC)')
        
        # Create opcua_monitored_variables table
        print("Creating opcua_monitored_variables table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opcua_monitored_variables (
                id SERIAL PRIMARY KEY,
                node_id VARCHAR(255) NOT NULL UNIQUE,
                browse_name VARCHAR(255) NOT NULL,
                display_name VARCHAR(255),
                namespace_index INTEGER,
                data_type VARCHAR(50),
                polling_interval_ms INTEGER DEFAULT 1000,
                deadband_absolute DOUBLE PRECISION DEFAULT 0.0,
                store_to_postgres BOOLEAN DEFAULT TRUE,
                measurement_name VARCHAR(255),
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create mqtt_opcua_mappings table
        print("Creating mqtt_opcua_mappings table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mqtt_opcua_mappings (
                id SERIAL PRIMARY KEY,
                mqtt_topic VARCHAR(255) NOT NULL,
                opcua_node_id VARCHAR(255) NOT NULL,
                opcua_browse_name VARCHAR(255) NOT NULL,
                json_key VARCHAR(255) DEFAULT 'value',
                data_type VARCHAR(50) DEFAULT 'Double',
                unit VARCHAR(50),
                scaling_factor DOUBLE PRECISION DEFAULT 1.0,
                value_offset DOUBLE PRECISION DEFAULT 0.0,
                store_to_postgres BOOLEAN DEFAULT TRUE,
                measurement_name VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create devices table
        print("Creating devices table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                device_type VARCHAR(10) CHECK(device_type IN ('opcua', 'mqtt')),
                name VARCHAR(255) NOT NULL UNIQUE,
                connection_string TEXT,
                status VARCHAR(20) CHECK(status IN ('connected', 'disconnected', 'error')),
                last_connected_at TIMESTAMP WITH TIME ZONE,
                last_error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opcua_variables_enabled ON opcua_monitored_variables(enabled)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mqtt_mappings_topic ON mqtt_opcua_mappings(mqtt_topic)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_mqtt_mappings_topic_json_key ON mqtt_opcua_mappings(mqtt_topic, json_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_type_status ON devices(device_type, status)')
        
        conn.commit()
        print("\n✓ All tables created successfully!")
        print("✓ Indexes created successfully!")
        
        # Show table counts
        cursor.execute("SELECT COUNT(*) FROM opcua_monitored_variables")
        opcua_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mqtt_opcua_mappings")
        mqtt_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM devices")
        devices_count = cursor.fetchone()[0]
        
        print(f"\nTable Status:")
        print(f"  - opcua_monitored_variables: {opcua_count} rows")
        print(f"  - mqtt_opcua_mappings: {mqtt_count} rows")
        print(f"  - devices: {devices_count} rows")
        
        cursor.close()
        conn.close()
        
        print("\n✓ PostgreSQL setup complete!")
        print("  You can now restart the application to use PostgreSQL for all data.")
        
    except Exception as e:
        print(f"Error setting up tables: {e}")
        raise

if __name__ == "__main__":
    print("Setting up PostgreSQL tables for IIoT Gateway...")
    print(f"Host: {Config.POSTGRES_HOST}")
    print(f"Port: {Config.POSTGRES_PORT}")
    print(f"Database: {Config.POSTGRES_DB}")
    print(f"User: {Config.POSTGRES_USER}")
    print()
    setup_postgres_tables()
