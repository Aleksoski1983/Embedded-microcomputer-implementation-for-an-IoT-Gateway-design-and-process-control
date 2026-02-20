"""
Database Service - PostgreSQL Only
All configuration and time-series data stored in PostgreSQL
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from app.config import Config
import psycopg2
from psycopg2 import pool, sql, extras

logger = logging.getLogger(__name__)

class DatabaseService:
    """PostgreSQL-only database service"""
    
    def __init__(self):
        self.pg_pool = None
        
    def init_postgresql(self):
        """Initialize PostgreSQL connection pool and create tables"""
        try:
            self.pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=Config.POSTGRES_HOST,
                port=Config.POSTGRES_PORT,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD
            )
            
            # Create all tables
            conn = self.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                
                # Sensor data table (time-series)
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
                
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp DESC)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement ON sensor_data(measurement)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement_timestamp ON sensor_data(measurement, timestamp DESC)')
                
                # OPC UA monitored variables
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
                
                # MQTT to OPC UA mappings
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
                
                # Devices table
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
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_type_status ON devices(device_type, status)')

                # --- Migration for older installs ---
                # Older schema had mqtt_topic UNIQUE and no json_key column.
                # Some older scripts used column name "offset" instead of "value_offset".
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'mqtt_opcua_mappings' AND column_name = 'offset'
                        ) AND NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'mqtt_opcua_mappings' AND column_name = 'value_offset'
                        ) THEN
                            ALTER TABLE mqtt_opcua_mappings RENAME COLUMN "offset" TO value_offset;
                        END IF;
                    END $$;
                """)
                cursor.execute("ALTER TABLE mqtt_opcua_mappings ADD COLUMN IF NOT EXISTS json_key VARCHAR(255) DEFAULT 'value'")
                cursor.execute("UPDATE mqtt_opcua_mappings SET json_key = 'value' WHERE json_key IS NULL")
                cursor.execute("ALTER TABLE mqtt_opcua_mappings ALTER COLUMN json_key SET DEFAULT 'value'")

                # Drop legacy UNIQUE constraint on mqtt_topic if it exists.
                # Postgres default name for column-level UNIQUE is: <table>_<column>_key
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'mqtt_opcua_mappings_mqtt_topic_key'
                        ) THEN
                            ALTER TABLE mqtt_opcua_mappings
                            DROP CONSTRAINT mqtt_opcua_mappings_mqtt_topic_key;
                        END IF;
                    END $$;
                """)

                # Allow multiple mappings per topic/json_key (fan-out to multiple OPC UA nodes).
                # Uniqueness should prevent exact duplicates only.
                cursor.execute('DROP INDEX IF EXISTS idx_mqtt_mappings_topic_json_key')
                cursor.execute(
                    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mqtt_mappings_topic_json_key_node '
                    'ON mqtt_opcua_mappings(mqtt_topic, json_key, opcua_node_id)'
                )
                
                conn.commit()
                logger.info("PostgreSQL connection pool initialized successfully")
                logger.info("All database tables created/verified")
                
            finally:
                self.pg_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            self.pg_pool = None
            raise
    
    # OPC UA Variables Operations
    
    def add_monitored_variable(self, node_id: str, browse_name: str, display_name: str = None,
                              namespace_index: int = 0, data_type: str = None,
                              measurement_name: str = None) -> int:
        """Add a variable to monitoring list"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO opcua_monitored_variables 
                (node_id, browse_name, display_name, namespace_index, data_type, measurement_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (node_id, browse_name, display_name, namespace_index, data_type, measurement_name))
            
            variable_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Added monitored variable: {browse_name} ({node_id})")
            return variable_id
        except psycopg2.IntegrityError:
            conn.rollback()
            logger.warning(f"Variable {node_id} already exists")
            return -1
        finally:
            self.pg_pool.putconn(conn)
    
    def get_monitored_variables(self, enabled_only: bool = True) -> List[Dict]:
        """Get all monitored variables"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            
            query = 'SELECT * FROM opcua_monitored_variables'
            if enabled_only:
                query += ' WHERE enabled = TRUE'
            
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pg_pool.putconn(conn)
    
    def remove_monitored_variable(self, variable_id: int) -> bool:
        """Remove a variable from monitoring"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM opcua_monitored_variables WHERE id = %s', (variable_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Removed monitored variable ID: {variable_id}")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Error removing monitored variable {variable_id}: {e}")
            return False
        finally:
            self.pg_pool.putconn(conn)
    
    def add_opcua_variable(self, variable_data: Dict) -> Dict:
        """Add an OPC-UA variable with enhanced data structure"""
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            
            cursor.execute('''
                INSERT INTO opcua_monitored_variables 
                (node_id, browse_name, display_name, namespace_index, data_type, 
                 polling_interval_ms, deadband_absolute, store_to_postgres, 
                 measurement_name, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (
                variable_data.get('node_id'),
                variable_data.get('browse_name'),
                variable_data.get('display_name'),
                variable_data.get('namespace_index', 0),
                variable_data.get('data_type'),
                variable_data.get('polling_interval_ms', 1000),
                variable_data.get('deadband_absolute', 0.0),
                variable_data.get('store_to_postgres', True),
                variable_data.get('measurement_name'),
                variable_data.get('enabled', True)
            ))
            
            result = cursor.fetchone()
            conn.commit()
            self.pg_pool.putconn(conn)
            
            return dict(result) if result else None
            
        except psycopg2.IntegrityError:
            conn.rollback()
            self.pg_pool.putconn(conn)
            return None
        except Exception as e:
            conn.rollback()
            self.pg_pool.putconn(conn)
            logger.error(f"Error adding OPC-UA variable: {e}")
            return None
    
    def get_opcua_variables(self) -> List[Dict]:
        """Get all OPC-UA monitored variables"""
        return self.get_monitored_variables(enabled_only=False)
    
    def update_opcua_variable(self, variable_id: int, updates: Dict) -> bool:
        """Update an OPC-UA variable"""
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            set_clause = ', '.join([f"{key} = %s" for key in updates.keys()])
            values = list(updates.values()) + [variable_id]
            
            cursor.execute(f'''
                UPDATE opcua_monitored_variables 
                SET {set_clause}
                WHERE id = %s
            ''', values)
            
            conn.commit()
            self.pg_pool.putconn(conn)
            return True
        except Exception as e:
            conn.rollback()
            self.pg_pool.putconn(conn)
            logger.error(f"Error updating OPC-UA variable: {e}")
            return False
    
    def delete_opcua_variable(self, variable_id: int) -> bool:
        """Delete an OPC-UA variable"""
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM opcua_monitored_variables WHERE id = %s', (variable_id,))
            conn.commit()
            self.pg_pool.putconn(conn)
            return True
        except Exception as e:
            conn.rollback()
            self.pg_pool.putconn(conn)
            logger.error(f"Error deleting OPC-UA variable: {e}")
            return False
    
    # MQTT Mappings Operations
    
    def add_mqtt_mapping(self, mqtt_topic: str, opcua_node_id: str, opcua_browse_name: str,
                        data_type: str = 'Double', unit: str = None, measurement_name: str = None,
                        json_key: str = 'value') -> int:
        """Add MQTT to OPC UA mapping"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mqtt_opcua_mappings 
                (mqtt_topic, opcua_node_id, opcua_browse_name, json_key, data_type, unit, measurement_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (mqtt_topic, opcua_node_id, opcua_browse_name, json_key or 'value', data_type, unit, measurement_name))
            
            mapping_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Added MQTT mapping: {mqtt_topic}[{json_key or 'value'}] -> {opcua_node_id}")
            return mapping_id
        except psycopg2.IntegrityError:
            conn.rollback()
            logger.warning(
                f"MQTT mapping already exists for {mqtt_topic}[{json_key or 'value'}] -> {opcua_node_id}"
            )
            return -1
        finally:
            self.pg_pool.putconn(conn)
    
    def get_mqtt_mappings(self) -> List[Dict]:
        """Get all MQTT topic mappings"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT * FROM mqtt_opcua_mappings ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pg_pool.putconn(conn)

    def get_mqtt_mappings_by_topic(self, topic: str) -> List[Dict]:
        """Get all MQTT mappings for a specific topic (supports JSON fan-out)."""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT * FROM mqtt_opcua_mappings WHERE mqtt_topic = %s ORDER BY id', (topic,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pg_pool.putconn(conn)
    
    def get_mqtt_mapping_by_topic(self, topic: str) -> Optional[Dict]:
        """Get MQTT mapping for a specific topic"""
        # Backward-compatible: return first mapping for this topic.
        mappings = self.get_mqtt_mappings_by_topic(topic)
        return mappings[0] if mappings else None
    
    def delete_mqtt_mapping(self, mapping_id: int) -> bool:
        """Delete MQTT mapping"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM mqtt_opcua_mappings WHERE id = %s', (mapping_id,))
            conn.commit()
            return True
        finally:
            self.pg_pool.putconn(conn)
    
    def remove_mqtt_mapping(self, mapping_id: int) -> bool:
        """Remove MQTT mapping (alias for delete_mqtt_mapping)"""
        return self.delete_mqtt_mapping(mapping_id)
    
    # Device Status Operations
    
    def update_device_status(self, device_type: str, name: str, connection_string: str = None, 
                           status: str = 'disconnected', last_error: str = None):
        """Update device connection status"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Upsert device status
            cursor.execute('''
                INSERT INTO devices (device_type, name, connection_string, status, last_connected_at, last_error, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) 
                DO UPDATE SET 
                    connection_string = EXCLUDED.connection_string,
                    status = EXCLUDED.status,
                    last_connected_at = EXCLUDED.last_connected_at,
                    last_error = EXCLUDED.last_error,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                device_type,
                name,
                connection_string,
                status,
                datetime.now() if status == 'connected' else None,
                last_error
            ))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating device status: {e}")
        finally:
            self.pg_pool.putconn(conn)
    
    def get_devices(self) -> List[Dict]:
        """Get all devices"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT * FROM devices ORDER BY name')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pg_pool.putconn(conn)
    
    # Time-Series Data Operations
    
    def write_sensor_data(self, measurement: str, fields: Dict, tags: Dict = None, timestamp: datetime = None):
        """Write sensor data to PostgreSQL"""
        if not timestamp:
            timestamp = datetime.now()
        
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            for field_name, field_value in fields.items():
                cursor.execute('''
                    INSERT INTO sensor_data 
                    (timestamp, measurement, source, location, field_name, field_value, unit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    timestamp,
                    measurement,
                    tags.get('source') if tags else None,
                    tags.get('location') if tags else None,
                    field_name,
                    float(field_value) if field_value is not None else None,
                    tags.get('unit') if tags else None
                ))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error writing sensor data: {e}")
        finally:
            self.pg_pool.putconn(conn)
    
    def get_sensor_data(self, measurement: str = None, start_time: datetime = None, 
                       end_time: datetime = None, limit: int = 1000) -> List[Dict]:
        """Query sensor data from PostgreSQL"""
        conn = self.pg_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            
            query = 'SELECT * FROM sensor_data WHERE 1=1'
            params = []
            
            if measurement:
                query += ' AND measurement = %s'
                params.append(measurement)
            
            if start_time:
                query += ' AND timestamp >= %s'
                params.append(start_time)
            
            if end_time:
                query += ' AND timestamp <= %s'
                params.append(end_time)
            
            query += f' ORDER BY timestamp DESC LIMIT {limit}'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pg_pool.putconn(conn)
    
    def get_database_status(self) -> Dict:
        """Get PostgreSQL database status"""
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Get PostgreSQL version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Get table row counts
            cursor.execute("SELECT COUNT(*) FROM sensor_data")
            sensor_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM opcua_monitored_variables")
            opcua_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mqtt_opcua_mappings")
            mqtt_count = cursor.fetchone()[0]
            
            self.pg_pool.putconn(conn)
            
            return {
                'connected': True,
                'type': 'postgresql',
                'version': version,
                'host': Config.POSTGRES_HOST,
                'port': Config.POSTGRES_PORT,
                'database': Config.POSTGRES_DB,
                'tables': {
                    'sensor_data': sensor_count,
                    'opcua_monitored_variables': opcua_count,
                    'mqtt_opcua_mappings': mqtt_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting database status: {e}")
            return {
                'connected': False,
                'error': str(e)
            }

# Global database service instance
db_service = DatabaseService()

def init_database():
    """Initialize PostgreSQL database"""
    db_service.init_postgresql()
    logger.info("PostgreSQL database service initialized")
