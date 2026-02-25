"""
Data API Routes
Endpoints for querying sensor data and system information
"""

from flask import jsonify, request
from app.api import api_bp
from app.services.database_service import db_service
import logging

logger = logging.getLogger(__name__)

@api_bp.route('/data/query', methods=['GET'])
def query_data():
    """Query sensor data from PostgreSQL"""
    try:
        measurement = request.args.get('measurement', 'temperature')
        start = request.args.get('start', '-1h')
        stop = request.args.get('stop', 'now()')
        
        data = db_service.query_sensor_data(measurement, start, stop)
        
        return jsonify({
            'success': True,
            'measurement': measurement,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        logger.error(f"Error querying data: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/data/latest/<measurement>', methods=['GET'])
def get_latest_data(measurement):
    """Get latest value for a measurement"""
    try:
        data = db_service.query_sensor_data(measurement, start='-5m', stop='now()')
        
        latest = data[-1] if data else None
        
        return jsonify({
            'success': True,
            'measurement': measurement,
            'latest': latest
        })
        
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get list of all devices"""
    try:
        devices = db_service.get_devices()
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices)
        })
        
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system/info', methods=['GET'])
def system_info():
    """Get system information"""
    try:
        from app.services.mqtt_service import mqtt_service
        from app.services.opcua_client_service import opcua_client
        from app.config import Config
        
        # Log current connection states for debugging
        logger.debug(f"MQTT connected: {mqtt_service.connected}")
        logger.debug(f"OPC UA Client connected: {opcua_client.connected}")
        
        # Use Config values directly (they're updated when configuration is saved)
        mqtt_broker = Config.MQTT_BROKER
        mqtt_port = Config.MQTT_PORT
        opcua_endpoint = Config.OPCUA_CLIENT_ENDPOINT
        postgres_host = Config.POSTGRES_HOST
        postgres_port = Config.POSTGRES_PORT
        postgres_db = Config.POSTGRES_DB
        
        # Get connection states
        mqtt_connected = mqtt_service.connected if mqtt_service else False
        opcua_connected = opcua_client.connected if opcua_client else False
        
        info = {
            'mqtt': {
                'connected': mqtt_connected,
                'broker': f"{mqtt_broker}:{mqtt_port}"
            },
            'opcua_client': {
                'connected': opcua_connected,
                'endpoint': opcua_endpoint,
                'monitored_variables': len(opcua_client.monitored_nodes) if opcua_client else 0,
                'security_policy': Config.OPCUA_CLIENT_SECURITY_POLICY,
                'security_mode': Config.OPCUA_CLIENT_SECURITY_MODE,
                'timeout': Config.OPCUA_CLIENT_TIMEOUT
            },
            'database': {
                'postgresql': f"{postgres_host}:{postgres_port}/{postgres_db}",
                'sqlite': Config.SQLITE_DB_PATH
            }
        }
        
        logger.debug(f"Returning system info: mqtt={mqtt_connected}, opcua={opcua_connected}")
        
        return jsonify({
            'success': True,
            'system': info
        })
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    try:
        monitored_vars = db_service.get_monitored_variables()
        mqtt_mappings = db_service.get_mqtt_mappings()
        devices = db_service.get_devices()
        
        stats = {
            'monitored_variables': len(monitored_vars),
            'mqtt_mappings': len(mqtt_mappings),
            'devices': len(devices),
            'devices_online': len([d for d in devices if d['status'] == 'connected'])
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/database/status', methods=['GET'])
def database_status():
    """Get database connection status"""
    try:
        import sqlite3
        import os
        from app.config import Config
        
        result = {
            'sqlite': {
                'connected': False,
                'path': Config.SQLITE_DB_PATH,
                'tables': []
            },
            'postgresql': {
                'connected': False,
                'host': Config.POSTGRES_HOST,
                'port': Config.POSTGRES_PORT,
                'database': Config.POSTGRES_DB,
                'user': Config.POSTGRES_USER
            }
        }
        
        # Check SQLite connection
        try:
            if os.path.exists(Config.SQLITE_DB_PATH):
                conn = sqlite3.connect(Config.SQLITE_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                result['sqlite']['connected'] = True
                result['sqlite']['tables'] = tables
        except Exception as e:
            result['sqlite']['error'] = str(e)
        
        # Check PostgreSQL connection
        try:
            if db_service.pg_pool:
                conn = db_service.pg_pool.getconn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT version()')
                    version = cursor.fetchone()[0]
                    cursor.close()
                    result['postgresql']['connected'] = True
                    result['postgresql']['version'] = version
                finally:
                    db_service.pg_pool.putconn(conn)
        except Exception as e:
            result['postgresql']['error'] = str(e)
        
        return jsonify({
            'success': True,
            'database': result
        })
        
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/database/test', methods=['POST'])
def test_database_connection():
    """Test database connection"""
    try:
        data = request.get_json() or {}
        db_type = data.get('type', 'all')  # 'sqlite', 'postgresql', or 'all'
        
        result = {'success': True, 'tests': {}}
        
        # Test SQLite
        if db_type in ['sqlite', 'all']:
            import sqlite3
            import os
            from app.config import Config
            
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(Config.SQLITE_DB_PATH), exist_ok=True)
                
                conn = sqlite3.connect(Config.SQLITE_DB_PATH)
                cursor = conn.cursor()
                
                # Test query
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()[0]
                
                # Get table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                conn.close()
                
                result['tests']['sqlite'] = {
                    'success': True,
                    'version': version,
                    'tables': tables,
                    'path': Config.SQLITE_DB_PATH
                }
            except Exception as e:
                result['tests']['sqlite'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Test PostgreSQL
        if db_type in ['postgresql', 'all']:
            from app.config import Config
            
            try:
                if db_service.pg_pool:
                    conn = db_service.pg_pool.getconn()
                    try:
                        cursor = conn.cursor()
                        
                        # Test query
                        cursor.execute('SELECT version()')
                        version = cursor.fetchone()[0]
                        
                        # Check if sensor_data table exists
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = 'sensor_data'
                            );
                        """)
                        table_exists = cursor.fetchone()[0]
                        
                        # Get row count if table exists
                        row_count = 0
                        if table_exists:
                            cursor.execute('SELECT COUNT(*) FROM sensor_data')
                            row_count = cursor.fetchone()[0]
                        
                        cursor.close()
                        
                        result['tests']['postgresql'] = {
                            'success': True,
                            'version': version,
                            'host': Config.POSTGRES_HOST,
                            'port': Config.POSTGRES_PORT,
                            'database': Config.POSTGRES_DB,
                            'table_exists': table_exists,
                            'row_count': row_count
                        }
                    finally:
                        db_service.pg_pool.putconn(conn)
                else:
                    result['tests']['postgresql'] = {
                        'success': False,
                        'error': 'PostgreSQL connection pool not initialized'
                    }
            except Exception as e:
                result['tests']['postgresql'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing database connection: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/database/init', methods=['POST'])
def init_database():
    """Initialize/reinitialize database tables"""
    try:
        from app.services.database_service import db_service
        
        # Initialize PostgreSQL
        db_service.init_postgresql()
        
        return jsonify({
            'success': True,
            'message': 'PostgreSQL database initialized successfully'
        })
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/database/disconnect', methods=['POST'])
def disconnect_database():
    """Disconnect from database"""
    try:
        from app.services.database_service import db_service
        
        # Close PostgreSQL connection pool
        if hasattr(db_service, 'pg_pool') and db_service.pg_pool:
            db_service.pg_pool.closeall()
            db_service.pg_pool = None
            logger.info("PostgreSQL connection pool closed")
        
        return jsonify({
            'success': True,
            'message': 'PostgreSQL disconnected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting database: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/database/configure', methods=['POST'])
def configure_database():
    """Configure database settings"""
    try:
        import os
        data = request.get_json()
        
        updates = {}
        
        if 'postgres_host' in data:
            updates['POSTGRES_HOST'] = data['postgres_host']
        if 'postgres_port' in data:
            updates['POSTGRES_PORT'] = str(data['postgres_port'])
        if 'postgres_db' in data:
            updates['POSTGRES_DB'] = data['postgres_db']
        if 'postgres_user' in data:
            updates['POSTGRES_USER'] = data['postgres_user']
        if 'postgres_password' in data:
            updates['POSTGRES_PASSWORD'] = data['postgres_password']
        
        if not updates:
            return jsonify({'error': 'No configuration provided'}), 400
        
        # Update .env file
        env_path = os.path.join(os.getcwd(), '.env')
        env_lines = []
        updated_keys = set()
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    updated = False
                    for key, value in updates.items():
                        if line.startswith(f'{key}='):
                            env_lines.append(f'{key}={value}\n')
                            updated_keys.add(key)
                            updated = True
                            break
                    if not updated:
                        env_lines.append(line)
        
        # Add any missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                env_lines.append(f'{key}={value}\n')
        
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        
        # Update runtime config
        from app.config import Config
        for key, value in updates.items():
            setattr(Config, key, value)
        
        # Reinitialize PostgreSQL connection pool
        db_service.init_postgresql()
        
        logger.info('Database configuration updated')
        
        return jsonify({
            'success': True,
            'message': 'Database configuration updated',
            'updated': list(updates.keys())
        })
        
    except Exception as e:
        logger.error(f"Error configuring database: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/database/tables', methods=['GET'])
def get_database_tables():
    """Get list of database tables and their info"""
    try:
        import sqlite3
        from app.config import Config
        
        result = {'tables': {}}
        
        conn = sqlite3.connect(Config.SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [{'name': row[1], 'type': row[2], 'nullable': not row[3], 'pk': bool(row[5])} 
                      for row in cursor.fetchall()]
            
            result['tables'][table] = {
                'row_count': count,
                'columns': columns
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Error getting database tables: {e}")
        return jsonify({'error': str(e)}), 500
