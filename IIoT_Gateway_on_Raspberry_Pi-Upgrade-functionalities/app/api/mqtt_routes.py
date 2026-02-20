"""
MQTT API Routes
Endpoints for managing MQTT topics and mappings
"""

from flask import jsonify, request
from app.api import api_bp
from app.services.mqtt_service import mqtt_service
from app.services.database_service import db_service
from app.services.opcua_server_service import opcua_server
from app.config import Config
from datetime import datetime
import logging
import asyncio
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@api_bp.route('/mqtt/topics', methods=['GET'])
def get_mqtt_topics():
    """Get list of configured MQTT topics"""
    try:
        mappings = db_service.get_mqtt_mappings()
        
        return jsonify({
            'success': True,
            'topics': mappings,
            'count': len(mappings)
        })
        
    except Exception as e:
        logger.error(f"Error getting MQTT topics: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/expose', methods=['POST'])
def expose_mqtt_topic():
    """Expose MQTT topic as OPC UA variable"""
    try:
        data = request.get_json()
        
        required_fields = ['mqtt_topic', 'opcua_browse_name']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'mqtt_topic and opcua_browse_name are required'}), 400
        
        mqtt_topic = data['mqtt_topic']
        opcua_browse_name = data['opcua_browse_name']
        json_key = data.get('json_key', 'value')
        data_type = data.get('data_type', 'Double')
        unit = data.get('unit')
        measurement_name = data.get('measurement_name', opcua_browse_name.lower())
        
        # Get OPC UA node ID from request, or generate a default one
        # For writing to S7-1500, user MUST provide the actual node ID
        opcua_node_id = data.get('opcua_node_id')
        if not opcua_node_id or opcua_node_id.strip() == '':
            # Generate default node ID (for gateway's OPC UA server)
            opcua_node_id = f"ns=2;s=MQTT.{opcua_browse_name}"
            logger.warning(f"No opcua_node_id provided, using generated ID: {opcua_node_id}")
        else:
            # Use the provided node ID (strip whitespace)
            opcua_node_id = opcua_node_id.strip()
            logger.info(f"Using provided OPC UA node ID: {opcua_node_id}")
        
        # Add mapping to database
        mapping_id = db_service.add_mqtt_mapping(
            mqtt_topic=mqtt_topic,
            opcua_node_id=opcua_node_id,
            opcua_browse_name=opcua_browse_name,
            data_type=data_type,
            unit=unit,
            measurement_name=measurement_name,
            json_key=json_key
        )
        
        if mapping_id > 0:
            # Create OPC UA variable in server
            loop = asyncio.new_event_loop()
            initial_value = 0.0 if data_type == 'Double' else ""
            var = loop.run_until_complete(
                opcua_server.create_mqtt_variable(
                    topic=mqtt_topic,
                    browse_name=opcua_browse_name,
                    data_type=data_type,
                    initial_value=initial_value,
                    unit=unit
                )
            )
            loop.close()
            
            # Subscribe to MQTT topic
            mqtt_service.subscribe_topic(mqtt_topic)
            
            return jsonify({
                'success': True,
                'mapping_id': mapping_id,
                'opcua_node_id': opcua_node_id,
                'json_key': json_key,
                'message': f'MQTT topic {mqtt_topic} exposed as OPC UA variable'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Mapping already exists or could not be created'
            }), 409
        
    except Exception as e:
        logger.error(f"Error exposing MQTT topic: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/mappings/<int:mapping_id>', methods=['DELETE'])
def remove_mqtt_mapping(mapping_id):
    """Remove MQTT to OPC UA mapping"""
    try:
        # Get mapping info
        mappings = db_service.get_mqtt_mappings()
        mapping = next((m for m in mappings if m['id'] == mapping_id), None)
        
        if not mapping:
            return jsonify({'error': 'Mapping not found'}), 404
        
        # Unsubscribe from MQTT topic
        mqtt_service.unsubscribe_topic(mapping['mqtt_topic'])
        
        # Remove from database
        success = db_service.remove_mqtt_mapping(mapping_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'MQTT mapping removed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove mapping from database'
            }), 500
        
    except Exception as e:
        logger.error(f"Error removing MQTT mapping: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/status', methods=['GET'])
def mqtt_status():
    """Get MQTT client connection status"""
    return jsonify({
        'connected': mqtt_service.connected,
        'broker': f"{mqtt_service.client._host}:{mqtt_service.client._port}" if mqtt_service.client else None,
        'subscriptions': len(mqtt_service.subscriptions)
    })

@api_bp.route('/mqtt/publish', methods=['POST'])
def mqtt_publish():
    """Publish message to MQTT topic"""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data or 'payload' not in data:
            return jsonify({'error': 'topic and payload are required'}), 400
        
        topic = data['topic']
        payload = data['payload']
        qos = data.get('qos', 1)
        
        success = mqtt_service.publish(topic, str(payload), qos)
        
        return jsonify({
            'success': success,
            'topic': topic,
            'payload': payload
        })
        
    except Exception as e:
        logger.error(f"Error publishing MQTT message: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/test', methods=['POST'])
def test_mqtt_connection():
    """Test MQTT broker connection"""
    try:
        import paho.mqtt.client as mqtt_test
        import socket
        
        data = request.get_json() or {}
        broker = data.get('broker', Config.MQTT_BROKER)
        port = int(data.get('port', Config.MQTT_PORT))
        username = data.get('username', Config.MQTT_USERNAME)
        password = data.get('password', Config.MQTT_PASSWORD)
        timeout = int(data.get('timeout', 5))
        
        result = {'success': False, 'broker': broker, 'port': port}
        
        # First test TCP connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((broker, port))
            sock.close()
            result['tcp_reachable'] = True
        except socket.error as e:
            result['tcp_reachable'] = False
            result['error'] = f"Cannot reach broker: {str(e)}"
            return jsonify(result)
        
        # Test MQTT connection
        test_client = mqtt_test.Client(client_id="test_connection_" + str(int(datetime.now().timestamp())))
        
        connection_result = {'connected': False, 'error': None}
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                connection_result['connected'] = True
            else:
                connection_result['error'] = f"Connection failed with code: {rc}"
        
        test_client.on_connect = on_connect
        
        if username and password:
            test_client.username_pw_set(username, password)
        
        try:
            test_client.connect(broker, port, keepalive=timeout)
            test_client.loop_start()
            
            # Wait for connection
            import time
            start_time = time.time()
            while not connection_result['connected'] and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            test_client.loop_stop()
            test_client.disconnect()
            
            if connection_result['connected']:
                result['success'] = True
                result['message'] = 'MQTT broker connection successful'
            else:
                result['error'] = connection_result['error'] or 'Connection timeout'
                
        except Exception as e:
            result['error'] = f"MQTT connection error: {str(e)}"
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing MQTT connection: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/mqtt/connect', methods=['POST'])
def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        # If already connected but config changed, force reconnect
        if mqtt_service.connected and (
            getattr(mqtt_service, 'current_broker', None) == Config.MQTT_BROKER and
            getattr(mqtt_service, 'current_port', None) == Config.MQTT_PORT
        ):
            return jsonify({
                'success': True,
                'message': 'Already connected to MQTT broker',
                'connected': True
            })

        if mqtt_service.connected:
            try:
                mqtt_service.stop()
            except Exception:
                logger.exception('Error stopping MQTT client before reconnect')
        
        # Start MQTT client in a new thread
        import threading
        
        mqtt_thread = threading.Thread(target=mqtt_service.start, daemon=True)
        mqtt_thread.start()
        
        # Wait briefly for connection
        import time
        time.sleep(2)
        
        return jsonify({
            'success': mqtt_service.connected,
            'message': 'Connected to MQTT broker' if mqtt_service.connected else 'Connection attempt started',
            'connected': mqtt_service.connected
        })
        
    except Exception as e:
        logger.error(f"Error connecting to MQTT broker: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/mqtt/disconnect', methods=['POST'])
def disconnect_mqtt():
    """Disconnect from MQTT broker"""
    try:
        if not mqtt_service.connected:
            return jsonify({
                'success': True,
                'message': 'Already disconnected from MQTT broker',
                'connected': False
            })
        
        mqtt_service.stop()
        
        return jsonify({
            'success': True,
            'message': 'Disconnected from MQTT broker',
            'connected': False
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting from MQTT broker: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/mqtt/configure', methods=['POST'])
def configure_mqtt():
    """Configure MQTT broker settings"""
    try:
        data = request.get_json()
        broker = data.get('broker')
        port = data.get('port')
        username = data.get('username', '')
        password = data.get('password', '')
        reconnect = bool(data.get('reconnect', False))
        
        logger.info(f"MQTT configure request: broker={broker}, port={port}, username={username}")
        
        if not broker:
            return jsonify({'error': 'Broker address is required'}), 400
        
        # Update project .env file (do not rely on current working directory)
        env_path = Path(__file__).resolve().parents[2] / '.env'
        updates = {
            'MQTT_BROKER': broker,
            'MQTT_PORT': str(port) if port else '1883',
            'MQTT_USERNAME': username,
            'MQTT_PASSWORD': password
        }
        
        env_lines = []
        updated_keys = set()
        
        if env_path.exists():
            with env_path.open('r', encoding='utf-8') as f:
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
        
        with env_path.open('w', encoding='utf-8') as f:
            f.writelines(env_lines)
        
        # Update runtime config
        Config.MQTT_BROKER = broker
        Config.MQTT_PORT = int(port) if port else 1883
        Config.MQTT_USERNAME = username
        Config.MQTT_PASSWORD = password
        
        logger.info(f'MQTT configuration updated: {broker}:{port}')
        logger.info(f'Config.MQTT_BROKER is now: {Config.MQTT_BROKER}')
        
        # Optionally reconnect MQTT immediately
        connected = mqtt_service.connected
        message = 'MQTT configuration updated. Restart connection to apply changes.'

        if reconnect:
            try:
                mqtt_service.stop()

                import threading
                import time
                mqtt_thread = threading.Thread(target=mqtt_service.start, daemon=True)
                mqtt_thread.start()
                time.sleep(2)

                connected = mqtt_service.connected
                message = 'MQTT configuration updated and reconnect attempted.'
            except Exception:
                logger.exception('Error reconnecting MQTT after configuration update')
                message = 'MQTT configuration updated, but reconnect failed. Please reconnect manually.'

        return jsonify({
            'success': True,
            'message': message,
            'broker': broker,
            'port': port,
            'connected': connected
        })
        
    except Exception as e:
        logger.error(f"Error configuring MQTT: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
@api_bp.route('/mqtt/subscribe', methods=['POST'])
def subscribe_topic():
    """Dynamically subscribe to an MQTT topic"""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data:
            return jsonify({'error': 'topic is required'}), 400
        
        topic = data['topic']
        qos = data.get('qos', 1)
        
        if not mqtt_service.connected:
            return jsonify({
                'success': False,
                'error': 'MQTT client is not connected'
            }), 503
        
        success = mqtt_service.subscribe_dynamic(topic, qos=qos)
        
        return jsonify({
            'success': success,
            'topic': topic,
            'qos': qos,
            'message': f'Subscribed to topic: {topic}' if success else 'Subscription failed'
        })
        
    except Exception as e:
        logger.error(f"Error subscribing to topic: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/unsubscribe', methods=['POST'])
def unsubscribe_topic():
    """Unsubscribe from an MQTT topic"""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data:
            return jsonify({'error': 'topic is required'}), 400
        
        topic = data['topic']
        
        if not mqtt_service.connected:
            return jsonify({
                'success': False,
                'error': 'MQTT client is not connected'
            }), 503
        
        success = mqtt_service.unsubscribe_dynamic(topic)
        
        return jsonify({
            'success': success,
            'topic': topic,
            'message': f'Unsubscribed from topic: {topic}' if success else 'Unsubscribe failed'
        })
        
    except Exception as e:
        logger.error(f"Error unsubscribing from topic: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/subscriptions', methods=['GET'])
def get_subscriptions():
    """Get list of all active subscriptions"""
    try:
        topics = mqtt_service.get_subscribed_topics()
        
        return jsonify({
            'success': True,
            'subscriptions': topics,
            'count': len(topics)
        })
        
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/bridge', methods=['POST'])
def add_bridge_rule():
    """Add a rule to bridge/forward messages between topics"""
    try:
        data = request.get_json()
        
        if not data or 'source_topic' not in data or 'target_topic' not in data:
            return jsonify({'error': 'source_topic and target_topic are required'}), 400
        
        source_topic = data['source_topic']
        target_topic = data['target_topic']

        # Support OPC-UA targets via prefixes or explicit fields
        target_type = data.get('target_type')  # 'mqtt' (default) or 'opcua'
        target_opcua_node_id = data.get('opcua_node_id') or data.get('target_opcua_node_id')
        target_opcua_browse_name = data.get('opcua_browse_name') or data.get('target_opcua_browse_name')

        if isinstance(target_topic, str):
            tt = target_topic.strip()
            if tt.startswith('opcua:'):
                target_type = 'opcua'
                target_opcua_node_id = tt[len('opcua:'):].strip()
            elif tt.startswith('opcua_browse:'):
                target_type = 'opcua'
                target_opcua_browse_name = tt[len('opcua_browse:'):].strip()
            elif 'ns=' in tt and (';s=' in tt or ';i=' in tt or ';g=' in tt):
                # Looks like a node id
                target_type = 'opcua'
                target_opcua_node_id = tt

        if not target_type:
            target_type = 'mqtt'
        
        # Optional: add transform function
        transform = None
        if 'transform' in data:
            transform_type = data['transform']
            if transform_type == 'json_extract':
                field = data.get('field', 'value')
                def _json_extract(payload: str, _field: str = field):
                    try:
                        obj = json.loads(payload)
                        if isinstance(obj, dict):
                            return obj.get(_field, payload)
                        return obj
                    except Exception:
                        return payload
                transform = _json_extract
            elif transform_type == 'multiply':
                factor = float(data.get('factor', 1.0))
                transform = lambda payload: str(float(payload) * factor)
            elif transform_type == 'prefix':
                prefix = data.get('prefix', '')
                transform = lambda payload: f"{prefix}{payload}"
        
        # Optional: add condition function
        condition = None
        if 'condition' in data:
            condition_type = data['condition']
            if condition_type == 'greater_than':
                threshold = float(data.get('threshold', 0))
                condition = lambda topic, payload: float(payload) > threshold
            elif condition_type == 'equals':
                value = data.get('value', '')
                condition = lambda topic, payload: payload == value
        
        rule_id = mqtt_service.add_bridge_rule(
            source_topic=source_topic,
            target_topic=target_topic,
            transform=transform,
            condition=condition,
            target_type=target_type,
            target_opcua_node_id=target_opcua_node_id,
            target_opcua_browse_name=target_opcua_browse_name
        )
        
        return jsonify({
            'success': True,
            'rule_id': rule_id,
            'source_topic': source_topic,
            'target_topic': target_topic,
            'target_type': target_type,
            'message': f'Bridge rule added: {source_topic} → {target_topic}'
        })
        
    except Exception as e:
        logger.error(f"Error adding bridge rule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/bridge/<int:rule_id>', methods=['DELETE'])
def remove_bridge_rule(rule_id):
    """Remove a bridge rule"""
    try:
        mqtt_service.remove_bridge_rule(rule_id)
        
        return jsonify({
            'success': True,
            'message': f'Bridge rule {rule_id} removed'
        })
        
    except Exception as e:
        logger.error(f"Error removing bridge rule: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mqtt/bridge', methods=['GET'])
def get_bridge_rules():
    """Get all active bridge rules"""
    try:
        rules = mqtt_service.get_bridge_rules()
        
        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        })
        
    except Exception as e:
        logger.error(f"Error getting bridge rules: {e}")
        return jsonify({'error': str(e)}), 500