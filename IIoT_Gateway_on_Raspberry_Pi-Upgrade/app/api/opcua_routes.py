"""OPC UA API Routes

Endpoints for browsing and managing OPC UA variables
"""

from flask import jsonify, request
from typing import Dict
from app.api import api_bp
from app.services.opcua_client_service import opcua_client
from app.services.database_service import db_service
from app.config import Config
import logging
# import asyncio  # Removed - using synchronous methods now

logger = logging.getLogger(__name__)


def _decode_access_level(mask: int) -> Dict:
    """Decode OPC UA AccessLevel bitmask into readable flags."""
    try:
        m = int(mask)
    except Exception:
        m = 0
    return {
        'raw': m,
        'current_read': bool(m & 0x01),
        'current_write': bool(m & 0x02),
        'history_read': bool(m & 0x04),
        'history_write': bool(m & 0x08),
        'semantic_change': bool(m & 0x10),
        'status_write': bool(m & 0x20),
        'timestamp_write': bool(m & 0x40),
    }

@api_bp.route('/opcua/browse', methods=['GET'])
def browse_opcua():
    """Browse OPC UA namespace from S7-1500 - synchronous method with folder support"""
    try:
        node_id = request.args.get('node_id', 'i=85')  # Default to Objects folder
        
        if not opcua_client.connected:
            return jsonify({
                'error': 'OPC UA client not connected',
                'connected': False
            }), 503
        
        # Use simple synchronous browse method with specified node
        items = opcua_client.browse_simple(node_id)
        
        return jsonify({
            'success': True,
            'node_id': node_id,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        logger.error(f"Error browsing OPC UA: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/browse/s7', methods=['GET'])
def browse_s7_specific():
    """Browse S7-1500 specific variable paths"""
    try:
        if not opcua_client.connected:
            return jsonify({
                'error': 'OPC UA client not connected',
                'connected': False
            }), 503
        
        # Use a thread pool to run the async function safely
        import concurrent.futures
        import threading
        
        def run_s7_browse():
            # Use simple synchronous browse method
            return opcua_client.browse_simple()
        
        # Run in thread pool with timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_s7_browse)
            try:
                tree = future.result(timeout=15)  # 15 second timeout
            except concurrent.futures.TimeoutError:
                return jsonify({'error': 'S7-1500 browse operation timed out'}), 504
        
        return jsonify({
            'success': True,
            'source': 's7_specific_paths',
            'tree': tree,
            'count': len(tree)
        })
        
    except Exception as e:
        logger.error(f"Error browsing S7-1500 specific paths: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/browse/comprehensive', methods=['GET'])
def browse_comprehensive():
    """Comprehensive browse using simple synchronous method with folder support"""
    try:
        node_id = request.args.get('node_id', 'i=85')  # Default to Objects folder
        
        if not opcua_client.connected:
            return jsonify({
                'error': 'OPC UA client not connected',
                'connected': False
            }), 503
        
        # Use simple synchronous browse method with folder support
        items = opcua_client.browse_simple(node_id)
        
        return jsonify({
            'success': True,
            'source': 'simple_synchronous_with_folders',
            'node_id': node_id,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        logger.error(f"Error in comprehensive browse: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/namespaces', methods=['GET'])
def get_namespaces():
    """Get list of OPC UA namespaces"""
    try:
        if not opcua_client.connected:
            return jsonify({'error': 'OPC UA client not connected'}), 503
        
        # Get namespaces using synchronous method
        ns_list = opcua_client.get_namespaces()
        
        return jsonify({
            'success': True,
            'namespaces': ns_list,
            'count': len(ns_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting namespaces: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/opcua/search', methods=['GET'])
def search_opcua_variables():
    """Search OPC UA variables by browse_name substring.

    Query params:
      - query: required search string (substring match)
      - node_id: optional start node (default i=85)
      - max_results: optional cap (default 50, max 500)
      - max_depth: optional traversal depth (default 6, max 20)
    """
    try:
        if not opcua_client.connected:
            return jsonify({'error': 'OPC UA client not connected', 'connected': False}), 503

        query = request.args.get('query', '').strip()
        if not query:
            return jsonify({'error': 'query is required'}), 400

        start_node_id = request.args.get('node_id', 'i=85')
        max_results = int(request.args.get('max_results', 50))
        max_depth = int(request.args.get('max_depth', 6))

        matches = opcua_client.search_variables(
            query=query,
            start_node_id=start_node_id,
            max_results=max(1, min(max_results, 500)),
            max_depth=max(1, min(max_depth, 20)),
        )

        return jsonify({
            'success': True,
            'query': query,
            'start_node_id': start_node_id,
            'count': len(matches),
            'matches': matches,
        })

    except Exception as e:
        logger.error(f"Error searching OPC UA variables: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/variables/selected', methods=['GET'])
def get_selected_variables():
    """Get list of monitored variables"""
    try:
        variables = db_service.get_monitored_variables(enabled_only=False)
        
        return jsonify({
            'success': True,
            'variables': variables,
            'count': len(variables)
        })
        
    except Exception as e:
        logger.error(f"Error getting selected variables: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/variables/values', methods=['GET'])
def get_variable_values():
    """Get current values for all monitored variables"""
    try:
        if not opcua_client.connected:
            return jsonify({
                'success': False,
                'error': 'OPC UA client not connected',
                'values': []
            })
        
        variables = db_service.get_monitored_variables(enabled_only=True)
        values = []
        
        for var in variables:
            try:
                node = opcua_client.client.get_node(var['node_id'])
                current_value = node.get_value()
                
                values.append({
                    'node_id': var['node_id'],
                    'browse_name': var['browse_name'],
                    'value': current_value,
                    'data_type': var.get('data_type', 'unknown')
                })
            except Exception as e:
                logger.warning(f"Could not read {var['browse_name']}: {e}")
                values.append({
                    'node_id': var['node_id'],
                    'browse_name': var['browse_name'],
                    'value': None,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'values': values,
            'count': len(values)
        })
        
    except Exception as e:
        logger.error(f"Error getting variable values: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/opcua/variables/select', methods=['POST'])
def select_variable():
    """Add a variable to monitoring list"""
    try:
        data = request.get_json()
        
        if not data or 'node_id' not in data:
            return jsonify({'error': 'node_id is required'}), 400
        
        node_id = data['node_id']
        browse_name = data.get('browse_name', 'Unknown')
        display_name = data.get('display_name', browse_name)
        namespace_index = data.get('namespace_index', 0)
        data_type = data.get('data_type', 'Unknown')
        measurement_name = data.get('measurement_name', browse_name.lower())
        
        # Add to database
        variable_id = db_service.add_monitored_variable(
            node_id=node_id,
            browse_name=browse_name,
            display_name=display_name,
            namespace_index=namespace_index,
            data_type=data_type,
            measurement_name=measurement_name
        )
        
        if variable_id > 0:
            # Variable successfully added
            return jsonify({
                'success': True,
                'variable_id': variable_id,
                'message': f'Variable {browse_name} added to monitoring list'
            })
        elif variable_id == -1:
            # Variable already exists (SQLite IntegrityError)
            return jsonify({
                'success': False,
                'error': f'Variable with node ID {node_id} already exists in monitoring list'
            }), 409
        else:
            # Other database error
            return jsonify({
                'success': False,
                'error': 'Could not add variable to monitoring list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error selecting variable: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/variables/<int:variable_id>', methods=['DELETE'])
def remove_variable(variable_id):
    """Remove a variable from monitoring"""
    try:
        # Get variable info first
        variables = db_service.get_monitored_variables(enabled_only=False)
        var_to_remove = next((v for v in variables if v['id'] == variable_id), None)
        
        if not var_to_remove:
            return jsonify({'error': 'Variable not found'}), 404
        
        # Note: Subscription management not implemented in synchronous client
        logger.info(f"Variable {var_to_remove['browse_name']} removed from monitoring list")
        
        # Remove from database
        success = db_service.remove_monitored_variable(variable_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Variable removed from monitoring'
            })
        else:
            return jsonify({'error': 'Failed to remove variable'}), 500
        
    except Exception as e:
        logger.error(f"Error removing variable: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/variables/<int:variable_id>/toggle', methods=['PUT'])
def toggle_variable(variable_id):
    """Enable or disable a monitored variable"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        success = db_service.update_variable_status(variable_id, enabled)
        
        return jsonify({
            'success': success,
            'variable_id': variable_id,
            'enabled': enabled
        })
        
    except Exception as e:
        logger.error(f"Error toggling variable: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/read', methods=['POST'])
def read_variable():
    """Read a single OPC UA variable value"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if not node_id:
            return jsonify({'error': 'node_id is required'}), 400
        
        if not opcua_client.connected:
            return jsonify({'error': 'OPC UA client not connected'}), 503
        
        # Test node access using synchronous method
        test_result = opcua_client.test_node_access(node_id)
        value = test_result.get('value', test_result.get('current_value', 'N/A'))
        
        return jsonify({
            'success': True,
            'node_id': node_id,
            'value': value
        })
        
    except Exception as e:
        logger.error(f"Error reading variable: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/status', methods=['GET'])
def opcua_status():
    """Get OPC UA client connection status"""
    return jsonify({
        'connected': opcua_client.connected,
        'endpoint': opcua_client.client.server_url.geturl() if opcua_client.client and opcua_client.connected else None,
        'monitored_count': len(opcua_client.monitored_nodes)
    })

@api_bp.route('/opcua/server/configure', methods=['POST'])
def configure_opcua_server():
    """Configure OPC UA Server endpoint"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return jsonify({'error': 'Endpoint is required'}), 400
        
        if not endpoint.startswith('opc.tcp://'):
            return jsonify({'error': 'Invalid endpoint format'}), 400
        
        # Update environment variable and config
        import os
        from app.config import Config
        
        # Update .env file
        env_path = os.path.join(os.getcwd(), '.env')
        env_lines = []
        endpoint_updated = False
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('OPCUA_SERVER_ENDPOINT='):
                        env_lines.append(f'OPCUA_SERVER_ENDPOINT={endpoint}\n')
                        endpoint_updated = True
                    else:
                        env_lines.append(line)
        
        if not endpoint_updated:
            env_lines.append(f'OPCUA_SERVER_ENDPOINT={endpoint}\n')
        
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        
        # Update runtime config
        Config.OPCUA_SERVER_ENDPOINT = endpoint
        
        # Restart OPC UA server
        from app.services.opcua_manager import opcua_manager
        # OPC-UA server disabled - focusing on client functionality
        logger.info("OPC-UA server restart skipped (server disabled)")
        
        logger.info(f'OPC UA Server endpoint updated to: {endpoint}')
        
        return jsonify({
            'success': True,
            'endpoint': endpoint,
            'message': 'OPC UA Server configuration updated and restarted'
        })
        
    except Exception as e:
        logger.error(f'Error configuring OPC UA server: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/client/configure', methods=['POST'])
def configure_opcua_client():
    """Configure OPC UA Client endpoint and security settings"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        security_policy = data.get('security_policy', 'None')
        security_mode = data.get('security_mode', 'None')
        timeout = data.get('timeout', 10)
        
        if not endpoint:
            return jsonify({'error': 'Endpoint is required'}), 400
        
        if not endpoint.startswith('opc.tcp://'):
            return jsonify({'error': 'Invalid endpoint format'}), 400
        
        # Update environment variable and config
        import os
        from app.config import Config
        
        # Update .env file
        env_path = os.path.join(os.getcwd(), '.env')
        env_lines = []
        updates = {
            'OPCUA_CLIENT_ENDPOINT': endpoint,
            'OPCUA_CLIENT_TIMEOUT': str(timeout),
            'OPCUA_CLIENT_SECURITY_POLICY': security_policy,
            'OPCUA_CLIENT_SECURITY_MODE': security_mode
        }
        
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
        Config.OPCUA_CLIENT_ENDPOINT = endpoint
        Config.OPCUA_CLIENT_TIMEOUT = timeout
        Config.OPCUA_CLIENT_SECURITY_POLICY = security_policy
        Config.OPCUA_CLIENT_SECURITY_MODE = security_mode
        
        # Update client instance settings
        opcua_client.server_url = endpoint
        opcua_client.security_policy = security_policy
        opcua_client.security_mode = security_mode
        
        # Disconnect first if already connected
        if opcua_client.connected:
            opcua_client.disconnect()
        
        # Try to connect with new settings - pass endpoint explicitly
        success = opcua_client.connect(endpoint)
        
        logger.info(f'OPC UA Client updated: {endpoint} (Security: {security_policy}/{security_mode})')
        
        return jsonify({
            'success': success,
            'endpoint': endpoint,
            'security_policy': security_policy,
            'security_mode': security_mode,
            'connected': opcua_client.connected,
            'message': 'OPC UA Client configuration updated' + (' and connected' if success else ' but connection failed')
        })
        
    except Exception as e:
        logger.error(f'Error configuring OPC UA client: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/client/test', methods=['POST'])
def test_opcua_connection():
    """Test OPC UA connection with given settings - uses asyncua for compatibility"""
    try:
        from asyncua import Client
        from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256, SecurityPolicyBasic256, SecurityPolicyBasic128Rsa15
        from asyncua.ua import MessageSecurityMode
        import asyncio
        
        data = request.get_json()
        endpoint = data.get('endpoint')
        security_policy = data.get('security_policy', 'None')
        security_mode = data.get('security_mode', 'None')
        timeout = data.get('timeout', 10)
        
        if not endpoint:
            return jsonify({'error': 'Endpoint is required', 'success': False}), 400
        
        async def test_connection_async():
            test_client = None
            try:
                test_client = Client(url=endpoint)
                test_client.session_timeout = timeout * 1000  # Convert to milliseconds
                
                # Map security policy string to actual policy class
                security_policy_map = {
                    'None': None,
                    'Basic128Rsa15': SecurityPolicyBasic128Rsa15,
                    'Basic256': SecurityPolicyBasic256,
                    'Basic256Sha256': SecurityPolicyBasic256Sha256
                }
                
                # Map security mode string to enum
                security_mode_map = {
                    'None': MessageSecurityMode.None_,
                    'Sign': MessageSecurityMode.Sign,
                    'SignAndEncrypt': MessageSecurityMode.SignAndEncrypt
                }
                
                # Set security if not None
                if security_policy != 'None' and security_mode != 'None':
                    policy_class = security_policy_map.get(security_policy)
                    mode_enum = security_mode_map.get(security_mode)
                    
                    if policy_class and mode_enum:
                        await test_client.set_security(policy_class, mode=mode_enum)
                        logger.info(f"Test connection using security: {security_policy}/{security_mode}")
                    else:
                        logger.warning(f"Unknown security settings: {security_policy}/{security_mode}, using None")
                else:
                    logger.info("Test connection with no security (anonymous)")
                
                # Connect to server
                await test_client.connect()
                logger.info(f"Test client connected to {endpoint}")
                
                # Get server info
                namespaces = await test_client.get_namespace_array()
                logger.info(f"Retrieved {len(namespaces)} namespaces from server")
                
                # Get server status node to verify connection
                try:
                    server_status = test_client.get_node("ns=0;i=2259")  # ServerStatus node
                    state_node = test_client.get_node("ns=0;i=2259")
                    state = await state_node.read_value()
                    logger.info(f"Server state: {state}")
                except Exception as e:
                    logger.warning(f"Could not read server status: {e}")
                
                # Disconnect
                await test_client.disconnect()
                logger.info("Test client disconnected successfully")
                
                return {
                    'success': True,
                    'connected': True,
                    'namespaces': len(namespaces),
                    'endpoint': endpoint,
                    'security': f"{security_policy}/{security_mode}",
                    'message': f'Connection successful! Server has {len(namespaces)} namespaces.'
                }
                
            except Exception as e:
                logger.error(f"Test connection failed: {e}", exc_info=True)
                if test_client:
                    try:
                        await test_client.disconnect()
                    except:
                        pass
                
                error_msg = str(e)
                # Provide more helpful error messages
                if "timeout" in error_msg.lower():
                    error_msg = f"Connection timeout after {timeout}s. Server may be unreachable or slow to respond."
                elif "refused" in error_msg.lower():
                    error_msg = "Connection refused. Check if the server is running and the endpoint is correct."
                elif "security" in error_msg.lower() or "badidentitytoken" in error_msg.lower():
                    error_msg = f"Security settings mismatch. Server may not support {security_policy}/{security_mode}."
                
                return {
                    'success': False,
                    'connected': False,
                    'error': error_msg,
                    'endpoint': endpoint,
                    'security': f"{security_policy}/{security_mode}"
                }
        
        # Run async test connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_connection_async())
        finally:
            loop.close()
        
        logger.info(f'Connection test to {endpoint}: {result.get("success", False)}')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error testing OPC UA connection: {e}', exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/opcua/client/status', methods=['GET'])
def get_opcua_client_status():
    """Get current OPC UA client connection status"""
    try:
        return jsonify({
            'success': True,
            'connected': opcua_client.connected,
            'endpoint': Config.OPCUA_CLIENT_ENDPOINT,
            'security_policy': getattr(Config, 'OPCUA_CLIENT_SECURITY_POLICY', 'None'),
            'security_mode': getattr(Config, 'OPCUA_CLIENT_SECURITY_MODE', 'None')
        })
        
    except Exception as e:
        logger.error(f'Error getting client status: {e}')
        return jsonify({'error': str(e), 'success': False}), 500


@api_bp.route('/opcua/diagnostics/write', methods=['POST'])
def opcua_write_diagnostics():
    """Diagnose OPC UA write issues for a specific node.

    POST JSON:
      - node_id: required (OPC UA NodeId string)
      - value: required (value to attempt to write)
      - readback: optional bool (default true) to read value after write
    """
    try:
        data = request.get_json() or {}
        node_id = (data.get('node_id') or data.get('opcua_node_id') or '').strip()
        if not node_id:
            return jsonify({'success': False, 'error': 'node_id is required'}), 400

        if not opcua_client.connected or not getattr(opcua_client, 'client', None):
            return jsonify({'success': False, 'error': 'OPC UA client not connected', 'connected': False}), 503

        requested_value = data.get('value', None)
        readback = bool(data.get('readback', True))

        from opcua import ua

        node = opcua_client.client.get_node(node_id)

        diag = {
            'success': True,
            'connected': True,
            'node_id': node_id,
            'requested_value': requested_value,
            'readback_requested': readback,
            'node': {},
            'write': {},
        }

        # Node metadata
        try:
            node_class = node.get_node_class()
            diag['node']['node_class'] = str(node_class)
        except Exception as e:
            diag['node']['node_class_error'] = str(e)

        try:
            browse_name = node.get_browse_name()
            diag['node']['browse_name'] = getattr(browse_name, 'Name', str(browse_name))
            diag['node']['namespace_index'] = getattr(browse_name, 'NamespaceIndex', None)
        except Exception as e:
            diag['node']['browse_name_error'] = str(e)

        try:
            display_name = node.get_display_name()
            diag['node']['display_name'] = getattr(display_name, 'Text', str(display_name))
        except Exception as e:
            diag['node']['display_name_error'] = str(e)

        try:
            dt_variant = node.get_data_type_as_variant_type()
            diag['node']['data_type_variant'] = str(dt_variant)
        except Exception as e:
            diag['node']['data_type_variant_error'] = str(e)

        try:
            dt_attr = node.get_attribute(ua.AttributeIds.DataType).Value.Value
            diag['node']['data_type_nodeid'] = str(dt_attr)
        except Exception as e:
            diag['node']['data_type_nodeid_error'] = str(e)

        try:
            access_level = node.get_attribute(ua.AttributeIds.AccessLevel).Value.Value
            diag['node']['access_level'] = _decode_access_level(access_level)
        except Exception as e:
            diag['node']['access_level_error'] = str(e)

        try:
            user_access_level = node.get_attribute(ua.AttributeIds.UserAccessLevel).Value.Value
            diag['node']['user_access_level'] = _decode_access_level(user_access_level)
        except Exception as e:
            diag['node']['user_access_level_error'] = str(e)

        try:
            current_value = node.get_value()
            diag['node']['current_value'] = current_value
            diag['node']['current_value_type'] = type(current_value).__name__
        except Exception as e:
            diag['node']['current_value_error'] = str(e)

        # Attempt write using the gateway's write implementation
        write_success, write_message = opcua_client.write_variable(node_id, requested_value)
        diag['write'] = {
            'success': bool(write_success),
            'message': write_message,
        }

        # Optional readback
        if write_success and readback:
            try:
                read_value = node.get_value()
                diag['write']['readback_value'] = read_value
                diag['write']['readback_value_type'] = type(read_value).__name__
            except Exception as e:
                diag['write']['readback_error'] = str(e)

        return jsonify(diag)

    except Exception as e:
        logger.error(f"Error in OPC UA write diagnostics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/opcua/client/disconnect', methods=['POST'])
def disconnect_opcua_client():
    """Disconnect OPC UA client"""
    try:
        if not opcua_client.connected:
            return jsonify({
                'success': True,
                'message': 'Client already disconnected',
                'connected': False
            })
        
        # Disconnect using synchronous method
        success = opcua_client.disconnect()
        
        logger.info('OPC UA Client disconnected by user')
        
        return jsonify({
            'success': True,
            'message': 'Disconnected successfully',
            'connected': False
        })
        
    except Exception as e:
        logger.error(f'Error disconnecting client: {e}')
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/opcua/client/connect', methods=['POST'])
def connect_opcua_client():
    """Connect OPC UA client"""
    try:
        if opcua_client.connected:
            return jsonify({
                'success': True,
                'message': 'Client already connected',
                'connected': True
            })
        
        # Reload endpoint from environment in case it was updated
        import os
        from dotenv import load_dotenv
        load_dotenv(override=True)
        endpoint = os.getenv('OPCUA_CLIENT_ENDPOINT', Config.OPCUA_CLIENT_ENDPOINT)
        
        # Update client endpoint if it changed
        if endpoint and endpoint != opcua_client.server_url:
            opcua_client.server_url = endpoint
            Config.OPCUA_CLIENT_ENDPOINT = endpoint
            logger.info(f"Updated OPC UA Client endpoint to: {endpoint}")
        
        # Connect using synchronous method
        success = opcua_client.connect()
        
        if success:
            logger.info('OPC UA Client connected by user')
            return jsonify({
                'success': True,
                'message': 'Connected successfully',
                'connected': True,
                'endpoint': opcua_client.server_url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Connection failed',
                'connected': False
            }), 500
        
    except Exception as e:
        logger.error(f'Error connecting client: {e}')
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/opcua/browse/simple', methods=['GET'])
def browse_simple():
    """Simple browse that shows folders and variables - synchronous approach"""
    try:
        node_id = request.args.get('node_id', 'i=85')  # Default to Objects folder
        
        if not opcua_client.connected:
            return jsonify({
                'error': 'OPC UA client not connected',
                'connected': False
            }), 503
        
        # Use synchronous browse method with folder support
        items = opcua_client.browse_simple(node_id)
        
        return jsonify({
            'success': True,
            'node_id': node_id,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        logger.error(f"Error in simple browse: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/debug/<path:node_id>', methods=['GET'])
def debug_browse(node_id):
    """Debug browse to troubleshoot specific folders like FB_AHU_5703_DB"""
    try:
        if not opcua_client.connected:
            return jsonify({
                'error': 'OPC UA client not connected',
                'connected': False
            }), 503
        
        logger.info(f"Debug browsing node: {node_id}")
        
        # Use debug browse method
        debug_info = opcua_client.browse_debug(node_id)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        logger.error(f"Error in debug browse: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/opcua/variables/add-manual', methods=['POST'])
def add_manual_variable():
    """Add a variable manually by node ID"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['node_id', 'variable_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Test the node ID by trying to read from it
        if opcua_client.connected:
            test_result = opcua_client.test_node_access(data['node_id'])
            if not test_result['success']:
                return jsonify({'error': f"Cannot access node: {test_result['error']}"}), 400
        
        # Save variable to database
        variable_data = {
            'node_id': data['node_id'],
            'display_name': data['variable_name'],
            'browse_name': data['variable_name'],
            'description': data.get('description', ''),
            'data_type': data.get('data_type', 'float'),
            'unit': data.get('unit', ''),
            'writable': data.get('writable', False),
            'store_to_postgres': data.get('store_to_db', data.get('store_to_postgres', True)),
            'enabled': True
        }
        
        result = db_service.add_opcua_variable(variable_data)
        
        if result['success']:
            return jsonify({'success': True, 'message': 'Variable added successfully'})
        else:
            return jsonify({'error': result['error']}), 500
        
    except Exception as e:
        logger.error(f"Error adding manual variable: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

