"""
MQTT Service
Subscribes to MQTT topics (Raspberry Pi Pico temperature) and updates OPC UA server
"""

import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from typing import Dict, Callable
from app.config import Config
from app.services.database_service import db_service
import asyncio

logger = logging.getLogger(__name__)

class MQTTService:
    """MQTT Client Service"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.current_broker = None
        self.current_port = None
        self.subscriptions: Dict[str, Callable] = {}
        self.opcua_update_callback = None
        self.topic_callbacks: Dict[str, list] = {}  # Custom callbacks for topics
        self.bridge_rules: list = []  # Rules for bridging data between topics/brokers
        self.dynamic_subscriptions: set = set()  # Track all dynamic subscriptions
        
    def set_opcua_callback(self, callback: Callable):
        """Set callback function to update OPC UA server variables"""
        self.opcua_update_callback = callback
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            
            # Use Config values directly
            mqtt_broker = Config.MQTT_BROKER
            mqtt_port = Config.MQTT_PORT
            
            logger.info(f"Connected to MQTT broker: {mqtt_broker}:{mqtt_port}")
            
            # Update device status
            db_service.update_device_status(
                device_type='mqtt',
                name='Mosquitto Broker',
                connection_string=f"{mqtt_broker}:{mqtt_port}",
                status='connected'
            )
            
            # Subscribe to topics from database
            self._subscribe_to_configured_topics()
            
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            
            # Use Config values directly
            mqtt_broker = Config.MQTT_BROKER
            mqtt_port = Config.MQTT_PORT
            
            db_service.update_device_status(
                device_type='mqtt',
                name='Mosquitto Broker',
                connection_string=f"{mqtt_broker}:{mqtt_port}",
                status='disconnected'
            )
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker. Code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
        
        # Use Config values directly
        mqtt_broker = Config.MQTT_BROKER
        mqtt_port = Config.MQTT_PORT
        
        db_service.update_device_status(
            device_type='mqtt',
            name='Mosquitto Broker',
            connection_string=f"{mqtt_broker}:{mqtt_port}",
            status='disconnected'
        )
    
    def on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"MQTT message received - Topic: {topic}, Payload: {payload}")
            
            # Broadcast message to web clients via Socket.IO
            try:
                from app import socketio
                socketio.emit('mqtt_message', {
                    'topic': topic,
                    'payload': payload,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.debug(f"Could not broadcast via Socket.IO: {e}")
            
            # Execute custom topic callbacks first
            if topic in self.topic_callbacks:
                for callback in self.topic_callbacks[topic]:
                    try:
                        callback(topic, payload)
                    except Exception as e:
                        logger.error(f"Error in topic callback: {e}")
            
            # Check bridge rules for forwarding
            self._process_bridge_rules(topic, payload)
            
            # Process message for OPC UA mapping
            self._process_message(topic, payload)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    @staticmethod
    def _extract_json_value(data: dict, json_key: str):
        """Extract a value from a JSON object using a simple key or dotted path."""
        if not isinstance(data, dict):
            return None

        if not json_key:
            json_key = 'value'

        current = data
        for part in str(json_key).split('.'):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _process_message(self, topic: str, payload: str):
        """Process received MQTT message and bridge JSON fields to OPC UA variables."""
        try:
            logger.info(f"Processing message for topic: {topic}")

            mappings = db_service.get_mqtt_mappings_by_topic(topic)
            if not mappings:
                logger.info(f"No mappings found for topic: {topic}")
                return

            # Parse payload once
            parsed_json = None
            try:
                parsed_json = json.loads(payload)
            except json.JSONDecodeError:
                parsed_json = None

            timestamp = datetime.now()

            # Import lazily to avoid circular imports on module load
            from app.services.opcua_client_service import opcua_client

            for mapping in mappings:
                json_key = mapping.get('json_key') or 'value'

                # Determine the source value
                value = None
                if isinstance(parsed_json, dict):
                    value = self._extract_json_value(parsed_json, json_key)

                    # Backwards compatibility for older configs that didn't specify json_key
                    if value is None and json_key == 'value':
                        value = parsed_json.get('value', parsed_json.get('temperature', parsed_json.get('data')))
                elif parsed_json is not None and not isinstance(parsed_json, dict):
                    # JSON but not dict (e.g. number/string)
                    if json_key == 'value':
                        value = parsed_json
                else:
                    # Not JSON
                    if json_key == 'value':
                        value = payload

                if value is None:
                    logger.debug(f"No JSON field '{json_key}' in payload for topic {topic}")
                    continue

                # Convert primitives
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        pass

                # Apply scaling and offset
                if isinstance(value, (int, float)):
                    value = value * mapping.get('scaling_factor', 1.0) + mapping.get('value_offset', 0.0)

                opcua_node_id = (mapping.get('opcua_node_id') or '').strip()
                if not opcua_node_id:
                    logger.warning(
                        f"Skipping mapping for {topic}[{json_key}] → missing opcua_node_id (browse_name={mapping.get('opcua_browse_name')})"
                    )
                    continue

                # Write to OPC UA Client (S7-1500 PLC)
                if opcua_client.connected:
                    success, msg = opcua_client.write_variable(opcua_node_id, value)
                    mapping['last_activity'] = f"{topic}[{json_key}]={value} → OPC UA {mapping.get('opcua_browse_name')} ({opcua_node_id}): {msg}"
                    if success:
                        logger.info(
                            f"Bridged MQTT {topic}[{json_key}]={value} → OPC UA {mapping.get('opcua_browse_name')} ({opcua_node_id})"
                        )
                        mapping['last_error'] = None
                    else:
                        logger.error(
                            f"Failed bridge MQTT {topic}[{json_key}]={value} → OPC UA {mapping.get('opcua_browse_name')} ({opcua_node_id}): {msg}"
                        )
                        mapping['last_error'] = msg
                else:
                    logger.warning("Cannot write to PLC - OPC UA client not connected")

                # Store to database if configured
                if mapping.get('store_to_postgres', True):
                    measurement = mapping.get('measurement_name') or mapping.get('opcua_browse_name') or topic
                    db_service.write_sensor_data(
                        measurement=measurement,
                        tags={
                            'source': 'mqtt',
                            'topic': topic,
                            'device': 'mqtt',
                            'json_key': json_key,
                        },
                        fields={
                            'value': float(value) if isinstance(value, (int, float)) else None,
                        },
                        timestamp=timestamp
                    )

        except Exception as e:
            logger.error(f"Error processing message for topic {topic}: {e}", exc_info=True)
    
    def _subscribe_to_configured_topics(self):
        """Subscribe to all configured MQTT topics from database"""
        try:
            mappings = db_service.get_mqtt_mappings()
            
            if not mappings:
                logger.info("No MQTT topic mappings configured in database")
                return
            
            topics = sorted({m['mqtt_topic'] for m in mappings if m.get('mqtt_topic')})
            for topic in topics:
                try:
                    result = self.client.subscribe(topic, qos=1)
                    if result[0] == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"Subscribed to MQTT topic: {topic}")
                    else:
                        logger.error(f"Failed to subscribe to topic {topic}: {result}")
                except Exception as e:
                    logger.error(f"Error subscribing to topic {topic}: {e}")
        except Exception as e:
            logger.error(f"Error loading MQTT topic mappings: {e}", exc_info=True)
    
    def subscribe_topic(self, topic: str, qos: int = 1):
        """Subscribe to a new MQTT topic"""
        if self.connected:
            self.client.subscribe(topic, qos=qos)
            logger.info(f"Subscribed to topic: {topic}")
            return True
        else:
            logger.warning("Cannot subscribe: not connected to MQTT broker")
            return False
    
    def unsubscribe_topic(self, topic: str):
        """Unsubscribe from MQTT topic"""
        if self.connected:
            self.client.unsubscribe(topic)
            logger.info(f"Unsubscribed from topic: {topic}")
            return True
        return False
    
    def publish(self, topic: str, payload: str, qos: int = 1):
        """Publish message to MQTT topic"""
        if self.connected:
            result = self.client.publish(topic, payload, qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published to {topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}")
                return False
        else:
            logger.warning("Cannot publish: not connected to MQTT broker")
            return False
    
    def start(self):
        """Start MQTT client"""
        try:
            import time
            
            # Use Config values directly (they're updated when configuration is saved)
            mqtt_broker = Config.MQTT_BROKER
            mqtt_port = Config.MQTT_PORT
            mqtt_username = Config.MQTT_USERNAME
            mqtt_password = Config.MQTT_PASSWORD

            self.current_broker = mqtt_broker
            self.current_port = mqtt_port
            
            logger.info(f"Starting MQTT client with broker: {mqtt_broker}:{mqtt_port}")
            
            # Create MQTT client with protocol version MQTTv311 and unique client ID
            client_id = f"{Config.MQTT_CLIENT_ID}-{int(time.time())}"
            self.client = mqtt.Client(
                client_id=client_id,
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            # Set credentials if provided
            if mqtt_username and mqtt_password:
                self.client.username_pw_set(mqtt_username, mqtt_password)
            
            # Enable automatic reconnection
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker {mqtt_broker}:{mqtt_port} with client ID: {client_id}...")
            self.client.connect(mqtt_broker, mqtt_port, keepalive=60)
            
            # Start network loop in background (non-blocking)
            self.client.loop_start()
            logger.info("MQTT client loop started in background")
            
        except Exception as e:
            logger.error(f"MQTT service error: {e}", exc_info=True)
            self.connected = False
    
    def subscribe_dynamic(self, topic: str, callback: Callable = None, qos: int = 1):
        """
        Dynamically subscribe to a topic with optional callback
        
        Args:
            topic: MQTT topic to subscribe to (supports wildcards like +, #)
            callback: Optional callback function(topic, payload) to execute on message
            qos: Quality of Service level (0, 1, or 2)
        """
        if not self.connected:
            logger.warning("Cannot subscribe: not connected to MQTT broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos=qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Dynamically subscribed to topic: {topic} (QoS: {qos})")
                
                # Track subscription
                self.dynamic_subscriptions.add(topic)
                
                # Add callback if provided
                if callback:
                    if topic not in self.topic_callbacks:
                        self.topic_callbacks[topic] = []
                    self.topic_callbacks[topic].append(callback)
                    logger.info(f"Added callback for topic: {topic}")
                
                return True
            else:
                logger.error(f"Failed to subscribe to topic {topic}: {result}")
                return False
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")
            return False
    
    def unsubscribe_dynamic(self, topic: str, remove_callbacks: bool = True):
        """
        Unsubscribe from a dynamically subscribed topic
        
        Args:
            topic: MQTT topic to unsubscribe from
            remove_callbacks: Whether to remove all callbacks for this topic
        """
        if not self.connected:
            logger.warning("Cannot unsubscribe: not connected to MQTT broker")
            return False
        
        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Unsubscribed from topic: {topic}")
                
                # Remove from tracking
                self.dynamic_subscriptions.discard(topic)
                
                # Remove callbacks if requested
                if remove_callbacks and topic in self.topic_callbacks:
                    del self.topic_callbacks[topic]
                    logger.info(f"Removed callbacks for topic: {topic}")
                
                return True
            else:
                logger.error(f"Failed to unsubscribe from topic {topic}: {result}")
                return False
        except Exception as e:
            logger.error(f"Error unsubscribing from topic {topic}: {e}")
            return False
    
    def add_bridge_rule(self, source_topic: str, target_topic: str,
                       transform: Callable = None, condition: Callable = None,
                       target_type: str = 'mqtt', target_opcua_node_id: str = None,
                       target_opcua_browse_name: str = None):
        """
        Add a rule to bridge/forward messages between topics
        
        Args:
            source_topic: Topic to listen to
            target_topic: Topic to publish to (can be same broker or different)
            transform: Optional function(payload) to transform the message
            condition: Optional function(topic, payload) that returns True if message should be forwarded
        """
        rule = {
            'id': len(self.bridge_rules) + 1,
            'source_topic': source_topic,
            'target_topic': target_topic,
            'target_type': target_type or 'mqtt',
            'target_opcua_node_id': target_opcua_node_id,
            'target_opcua_browse_name': target_opcua_browse_name,
            'transform': transform,
            'condition': condition,
            'message_count': 0,
            'last_message': None,
            'last_error': None,
            'subscription_ok': False
        }
        self.bridge_rules.append(rule)
        
        # Ensure we're subscribed to the source topic
        subscribed = self.subscribe_dynamic(source_topic)
        rule['subscription_ok'] = bool(subscribed)
        if not subscribed:
            rule['last_error'] = 'Failed to subscribe to source topic (check MQTT connection / topic pattern)'
        
        logger.info(f"Added bridge rule: {source_topic} → {target_topic}")
        return rule['id']
    
    def remove_bridge_rule(self, rule_id: int):
        """Remove a bridge rule by ID"""
        self.bridge_rules = [r for r in self.bridge_rules if r['id'] != rule_id]
        logger.info(f"Removed bridge rule ID: {rule_id}")
    
    def get_bridge_rules(self):
        """Get all active bridge rules"""
        return [{
            'id': r['id'],
            'source_topic': r['source_topic'],
            'target_topic': r['target_topic'],
            'target_type': r.get('target_type', 'mqtt'),
            'target_opcua_node_id': r.get('target_opcua_node_id'),
            'target_opcua_browse_name': r.get('target_opcua_browse_name'),
            'message_count': r['message_count'],
            'last_message': r['last_message'],
            'last_error': r.get('last_error'),
            'subscription_ok': r.get('subscription_ok', False)
        } for r in self.bridge_rules]

    @staticmethod
    def _coerce_payload_value(payload: str):
        """Try to coerce a payload string into a primitive (number/bool) when possible."""
        if payload is None:
            return None

        # Common human-readable format: "SomeVar = { ...json... }"
        # Strip prefix to get valid JSON.
        if isinstance(payload, str) and '=' in payload:
            left, right = payload.split('=', 1)
            if right.strip().startswith('{') or right.strip().startswith('['):
                payload = right.strip()

        # Try JSON first (handles numeric JSON, true/false, quoted strings)
        try:
            parsed = json.loads(payload)
            # Common IoT convention: JSON object with a numeric field
            if isinstance(parsed, dict):
                return parsed.get('value', parsed.get('temperature', parsed.get('data', parsed)))
            return parsed
        except Exception:
            pass

        # Try float
        try:
            return float(payload)
        except Exception:
            return payload

    def _resolve_opcua_node_id_for_rule(self, rule: dict) -> str | None:
        """Resolve (and cache) OPC UA node id for a bridge rule."""
        node_id = (rule.get('target_opcua_node_id') or '').strip()
        if node_id:
            return node_id

        browse_name = (rule.get('target_opcua_browse_name') or '').strip()
        if not browse_name:
            return None

        try:
            from app.services.opcua_client_service import opcua_client
            if not opcua_client.connected:
                return None

            matches = opcua_client.search_variables(query=browse_name, start_node_id='i=85', max_results=25, max_depth=8)
            if not matches:
                return None

            # Prefer exact browse_name match (case-insensitive)
            exact = [m for m in matches if (m.get('browse_name') or '').lower() == browse_name.lower()]
            chosen = None
            if len(exact) == 1:
                chosen = exact[0]
            elif len(matches) == 1:
                chosen = matches[0]

            if not chosen:
                return None

            resolved = (chosen.get('node_id') or '').strip()
            if resolved:
                rule['target_opcua_node_id'] = resolved  # cache
            return resolved
        except Exception:
            logger.debug('Failed resolving OPC UA node id for bridge rule', exc_info=True)
            return None
    
    def _process_bridge_rules(self, topic: str, payload: str):
        """Process message through bridge rules"""
        for rule in self.bridge_rules:
            try:
                # Check if topic matches (support wildcards)
                if self._topic_matches(topic, rule['source_topic']):
                    # Check condition if provided
                    if rule['condition'] and not rule['condition'](topic, payload):
                        continue
                    
                    # Transform payload if transform function provided
                    forwarded_payload = payload
                    if rule['transform']:
                        forwarded_payload = rule['transform'](payload)

                    success = False
                    rule['last_error'] = None
                    now_iso = datetime.now().isoformat()

                    target_type = rule.get('target_type', 'mqtt')
                    if target_type == 'opcua':
                        node_id = self._resolve_opcua_node_id_for_rule(rule)
                        if not node_id:
                            rule['last_error'] = 'OPC UA target node could not be resolved'
                            rule['last_activity'] = f"{topic} → OPC UA: node_id could not be resolved"
                        else:
                            try:
                                from app.services.opcua_client_service import opcua_client
                                if not opcua_client.connected:
                                    rule['last_error'] = 'OPC UA client not connected'
                                    rule['last_activity'] = f"{topic} → OPC UA: client not connected"
                                else:
                                    value = self._coerce_payload_value(forwarded_payload)
                                    success, msg = opcua_client.write_variable(node_id, value)
                                    rule['last_activity'] = f"{topic}={value} → OPC UA {node_id}: {msg}"
                                    if not success:
                                        rule['last_error'] = msg
                                    else:
                                        rule['last_error'] = None
                            except Exception as e:
                                rule['last_error'] = str(e)
                                rule['last_activity'] = f"{topic} → OPC UA {node_id}: Exception {e}"
                                logger.error(f"Error bridging to OPC UA for rule {rule['id']}: {e}", exc_info=True)
                    else:
                        # Publish to target topic
                        success = self.publish(rule['target_topic'], str(forwarded_payload))
                        if not success:
                            rule['last_error'] = 'MQTT publish failed'

                    # Update rule stats
                    rule['last_message'] = now_iso
                    if success:
                        rule['message_count'] += 1
                        logger.debug(f"Bridged message: {topic} → {rule['target_topic']} ({target_type})")
                    
            except Exception as e:
                rule['last_error'] = str(e)
                logger.error(f"Error processing bridge rule {rule['id']}: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports MQTT wildcards + and #)"""
        import re
        
        # Convert MQTT wildcard pattern to regex
        pattern_regex = pattern.replace('+', '[^/]+').replace('#', '.*')
        pattern_regex = f"^{pattern_regex}$"
        
        return bool(re.match(pattern_regex, topic))
    
    def get_subscribed_topics(self):
        """Get list of all subscribed topics"""
        topics = set()
        
        # Get topics from database mappings
        mappings = db_service.get_mqtt_mappings()
        for mapping in mappings:
            topics.add(mapping['mqtt_topic'])
        
        # Get topics from dynamic subscriptions
        topics.update(self.dynamic_subscriptions)
        
        # Get topics from bridge rules
        for rule in self.bridge_rules:
            topics.add(rule['source_topic'])
        
        return list(topics)
    
    def stop(self):
        """Stop MQTT client"""
        try:
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    logger.debug('Error disconnecting MQTT client', exc_info=True)

                try:
                    self.client.loop_stop()
                except Exception:
                    logger.debug('Error stopping MQTT client loop', exc_info=True)

            self.connected = False
            self.client = None
            # keep current_broker/current_port (reflect last attempted config)
            logger.info("MQTT client stopped")
        except Exception:
            logger.exception('Error stopping MQTT client')


# Global MQTT service instance
mqtt_service = MQTTService()
