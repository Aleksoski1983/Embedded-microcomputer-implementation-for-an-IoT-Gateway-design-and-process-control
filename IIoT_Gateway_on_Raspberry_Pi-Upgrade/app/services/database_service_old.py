"""
Database Service
Handles SQLite for configuration and PostgreSQL for time-series data
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import os
from app.config import Config

# Conditional import for PostgreSQL support
try:
    import psycopg2
    from psycopg2 import pool, sql
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psycopg2 not installed - PostgreSQL support disabled")

logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service for SQLite and PostgreSQL operations"""
    
    def __init__(self):
        self.sqlite_db_path = Config.SQLITE_DB_PATH
        self.pg_pool = None
        
    def init_sqlite(self):
        """Initialize SQLite database with schema"""
        os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        # Create opcua_monitored_variables table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opcua_monitored_variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL UNIQUE,
                browse_name TEXT NOT NULL,
                display_name TEXT,
                namespace_index INTEGER,
                data_type TEXT,
                polling_interval_ms INTEGER DEFAULT 1000,
                deadband_absolute REAL DEFAULT 0.0,
                store_to_postgres BOOLEAN DEFAULT 1,
                measurement_name TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create mqtt_opcua_mappings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mqtt_opcua_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mqtt_topic TEXT NOT NULL UNIQUE,
                opcua_node_id TEXT NOT NULL,
                opcua_browse_name TEXT NOT NULL,
                data_type TEXT DEFAULT 'Double',
                unit TEXT,
                scaling_factor REAL DEFAULT 1.0,
                offset REAL DEFAULT 0.0,
                store_to_postgres BOOLEAN DEFAULT 1,
                measurement_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT CHECK(device_type IN ('opcua', 'mqtt')),
                name TEXT NOT NULL UNIQUE,
                connection_string TEXT,
                status TEXT DEFAULT 'disconnected',
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create variable_tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS variable_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variable_id INTEGER,
                tag TEXT,
                FOREIGN KEY (variable_id) REFERENCES opcua_monitored_variables(id)
            )
        ''')
        
        # Migration: Ensure devices table has UNIQUE constraint on name
        # Check if we need to recreate the table
        cursor.execute("PRAGMA table_info(devices)")
        columns = cursor.fetchall()
        
        # Check if the table exists and might need migration
        if columns:
            # Try to add UNIQUE constraint by recreating the table
            try:
                cursor.execute("SELECT COUNT(*) FROM devices")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Table is empty, safe to drop and recreate
                    cursor.execute("DROP TABLE IF EXISTS devices")
                    cursor.execute('''
                        CREATE TABLE devices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_type TEXT CHECK(device_type IN ('opcua', 'mqtt')),
                            name TEXT NOT NULL UNIQUE,
                            connection_string TEXT,
                            status TEXT DEFAULT 'disconnected',
                            last_seen TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    logger.info("Recreated devices table with UNIQUE constraint")
            except Exception as e:
                logger.debug(f"Devices table migration check: {e}")
        
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized successfully")
    
    def init_postgresql(self):
        """Initialize PostgreSQL connection pool"""
        if not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL support not available - skipping PostgreSQL initialization")
            return
            
        try:
            self.pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=Config.POSTGRES_HOST,
                port=Config.POSTGRES_PORT,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD
            )
            
            # Create time-series table if it doesn't exist
            conn = self.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensor_data (
                        id BIGSERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        measurement VARCHAR(255) NOT NULL,
                        source VARCHAR(255),
                        location VARCHAR(255),
                        field_name VARCHAR(255) NOT NULL,
                        field_value DOUBLE PRECISION,
                        unit VARCHAR(50)
                    )
                ''')
                
                # Create index for faster time-based queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp 
                    ON sensor_data (timestamp DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement 
                    ON sensor_data (measurement, timestamp DESC)
                ''')
                
                conn.commit()
                cursor.close()
            finally:
                self.pg_pool.putconn(conn)
            
            logger.info("PostgreSQL connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            self.pg_pool = None
    
    # SQLite Operations - OPC UA Variables
    
    def add_monitored_variable(self, node_id: str, browse_name: str, display_name: str = None,
                              namespace_index: int = 0, data_type: str = None,
                              measurement_name: str = None) -> int:
        """Add a variable to monitoring list"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO opcua_monitored_variables 
                (node_id, browse_name, display_name, namespace_index, data_type, measurement_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (node_id, browse_name, display_name, namespace_index, data_type, measurement_name))
            
            conn.commit()
            variable_id = cursor.lastrowid
            logger.info(f"Added monitored variable: {browse_name} ({node_id})")
            return variable_id
        except sqlite3.IntegrityError:
            logger.warning(f"Variable {node_id} already exists")
            return -1
        finally:
            conn.close()
    
    def get_monitored_variables(self, enabled_only: bool = True) -> List[Dict]:
        """Get all monitored variables"""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM opcua_monitored_variables'
        if enabled_only:
            query += ' WHERE enabled = 1'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_opcua_variable(self, variable_data: Dict) -> Dict:
        """Add an OPC-UA variable with enhanced data structure"""
        try:
            # Extract data with defaults
            node_id = variable_data.get('node_id')
            browse_name = variable_data.get('browse_name', variable_data.get('variable_name', ''))
            display_name = variable_data.get('display_name', browse_name)
            namespace_index = variable_data.get('namespace_index', 0)
            data_type = variable_data.get('data_type', 'float')
            measurement_name = variable_data.get('measurement_name', browse_name.lower().replace(' ', '_'))
            
            if not node_id or not browse_name:
                return {'success': False, 'error': 'node_id and browse_name are required'}
            
            # Add additional fields if supported
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Check if the variable already exists
            cursor.execute('SELECT id FROM opcua_monitored_variables WHERE node_id = ?', (node_id,))
            existing = cursor.fetchone()
            
            if existing:
                return {'success': False, 'error': f'Variable with node_id {node_id} already exists'}
            
            # Add the variable
            cursor.execute('''
                INSERT INTO opcua_monitored_variables 
                (node_id, browse_name, display_name, namespace_index, data_type, 
                 measurement_name, store_to_postgres, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node_id,
                browse_name, 
                display_name,
                namespace_index,
                data_type,
                measurement_name,
                variable_data.get('store_to_postgres', variable_data.get('store_to_influxdb', True)),
                variable_data.get('enabled', True)
            ))
            
            conn.commit()
            variable_id = cursor.lastrowid
            conn.close()
            
            logger.info(f"Added OPC-UA variable: {display_name} ({node_id})")
            return {'success': True, 'id': variable_id, 'message': 'Variable added successfully'}
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Database integrity error: {e}")
            return {'success': False, 'error': 'Database integrity error - variable may already exist'}
        except Exception as e:
            logger.error(f"Error adding OPC-UA variable: {e}")
            return {'success': False, 'error': str(e)}
    
    def remove_monitored_variable(self, variable_id: int) -> bool:
        """Remove a variable from monitoring"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM opcua_monitored_variables WHERE id = ?', (variable_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            logger.info(f"Removed monitored variable ID: {variable_id}")
            return True
        return False
    
    def update_variable_status(self, variable_id: int, enabled: bool) -> bool:
        """Enable or disable a monitored variable"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE opcua_monitored_variables SET enabled = ? WHERE id = ?', 
                      (1 if enabled else 0, variable_id))
        conn.commit()
        conn.close()
        return True
    
    # SQLite Operations - MQTT to OPC UA Mappings
    
    def add_mqtt_mapping(self, mqtt_topic: str, opcua_node_id: str, opcua_browse_name: str,
                        data_type: str = 'Double', unit: str = None,
                        measurement_name: str = None) -> int:
        """Add MQTT to OPC UA mapping"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO mqtt_opcua_mappings 
                (mqtt_topic, opcua_node_id, opcua_browse_name, data_type, unit, measurement_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (mqtt_topic, opcua_node_id, opcua_browse_name, data_type, unit, measurement_name))
            
            conn.commit()
            mapping_id = cursor.lastrowid
            logger.info(f"Added MQTT mapping: {mqtt_topic} -> {opcua_browse_name}")
            return mapping_id
        except sqlite3.IntegrityError:
            logger.warning(f"MQTT mapping for {mqtt_topic} already exists")
            return -1
        finally:
            conn.close()
    
    def remove_mqtt_mapping(self, mapping_id: int) -> bool:
        """Remove MQTT to OPC UA mapping"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM mqtt_opcua_mappings WHERE id = ?', (mapping_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            logger.info(f"Removed MQTT mapping ID: {mapping_id}")
            return True
        return False
    
    def get_mqtt_mappings(self) -> List[Dict]:
        """Get all MQTT to OPC UA mappings"""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mqtt_opcua_mappings')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_mqtt_mapping_by_topic(self, mqtt_topic: str) -> Optional[Dict]:
        """Get MQTT mapping by topic"""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mqtt_opcua_mappings WHERE mqtt_topic = ?', (mqtt_topic,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # Device Management
    
    def update_device_status(self, device_type: str, name: str, connection_string: str, 
                           status: str) -> None:
        """Update or create device status"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()
        
        try:
            # First try to update existing device
            cursor.execute('''
                UPDATE devices SET status = ?, last_seen = ?, connection_string = ?
                WHERE name = ?
            ''', (status, datetime.now(), connection_string, name))
            
            if cursor.rowcount == 0:
                # Device doesn't exist, insert it
                cursor.execute('''
                    INSERT INTO devices (device_type, name, connection_string, status, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                ''', (device_type, name, connection_string, status, datetime.now()))
            
            conn.commit()
        except Exception as e:
            logger.warning(f"Error updating device status: {e}")
        finally:
            conn.close()
    
    def get_devices(self) -> List[Dict]:
        """Get all devices"""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # PostgreSQL Operations
    
    def write_sensor_data(self, measurement: str, tags: Dict, fields: Dict, timestamp: datetime = None):
        """Write sensor data to PostgreSQL"""
        if not self.pg_pool:
            logger.warning("PostgreSQL not initialized, skipping write")
            return
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Extract tags (source, location, etc.)
            source = tags.get('source', tags.get('device', 'unknown'))
            location = tags.get('location', tags.get('site', None))
            
            # Insert each field as a separate row
            for field_key, field_value in fields.items():
                cursor.execute('''
                    INSERT INTO sensor_data 
                    (timestamp, measurement, source, location, field_name, field_value)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    timestamp or datetime.now(),
                    measurement,
                    source,
                    location,
                    field_key,
                    float(field_value) if field_value is not None else None
                ))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to write to PostgreSQL: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    def query_sensor_data(self, measurement: str, start: str = '-1h', stop: str = 'now()') -> List[Dict]:
        """Query sensor data from PostgreSQL"""
        if not self.pg_pool:
            logger.warning("PostgreSQL not initialized, skipping query")
            return []
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Parse time strings (basic support for common formats)
            if start == '-1h':
                time_clause = "timestamp >= NOW() - INTERVAL '1 hour'"
            elif start == '-24h':
                time_clause = "timestamp >= NOW() - INTERVAL '24 hours'"
            elif start == '-7d':
                time_clause = "timestamp >= NOW() - INTERVAL '7 days'"
            else:
                # Assume it's a timestamp
                time_clause = f"timestamp >= '{start}'"
            
            if stop != 'now()':
                time_clause += f" AND timestamp <= '{stop}'"
            
            query = f'''
                SELECT timestamp, measurement, source, location, field_name, field_value, unit
                FROM sensor_data
                WHERE measurement = %s AND {time_clause}
                ORDER BY timestamp DESC
                LIMIT 10000
            '''
            
            cursor.execute(query, (measurement,))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'time': row[0],
                    'measurement': row[1],
                    'source': row[2],
                    'location': row[3],
                    'field': row[4],
                    'value': row[5],
                    'unit': row[6]
                })
            
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to query PostgreSQL: {e}")
            return []
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    def close(self):
        """Close database connections"""
        if self.pg_pool:
            self.pg_pool.closeall()
            logger.info("PostgreSQL connection pool closed")


# Global database service instance
db_service = DatabaseService()

def init_database():
    """Initialize database service"""
    db_service.init_sqlite()
    db_service.init_postgresql()
    logger.info("Database service initialized")
