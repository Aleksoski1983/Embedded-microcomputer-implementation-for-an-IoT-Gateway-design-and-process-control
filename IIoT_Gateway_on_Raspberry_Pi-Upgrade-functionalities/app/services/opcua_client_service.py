"""
OPC UA Client Service
Connects to Siemens S7-1500 PLC using synchronous opcua library (working approach from OPC-UA Client)
"""

import logging
from opcua import Client, ua
from typing import List, Dict, Optional, Callable
from datetime import datetime
from app.config import Config
from app.services.database_service import db_service
import threading
import time

logger = logging.getLogger(__name__)

class OPCUAClientService:
    """OPC UA Client to connect to S7-1500 PLC - synchronous approach that works"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.server_url = Config.OPCUA_CLIENT_ENDPOINT or ''
        self.monitored_nodes: Dict[str, any] = {}
        self.running = False
        self.monitoring_thread = None
        self.previous_values = {}  # Track previous values for change detection
        # Load security settings from config
        self.security_policy = getattr(Config, 'OPCUA_CLIENT_SECURITY_POLICY', 'None')
        self.security_mode = getattr(Config, 'OPCUA_CLIENT_SECURITY_MODE', 'None')
        logger.info(f"OPC UA Client initialized with endpoint: {self.server_url}")
        
    def connect(self, url=None):
        """Connect to OPC UA server - working synchronous method"""
        try:
            if url:
                self.server_url = url
                Config.OPCUA_CLIENT_ENDPOINT = url  # Update config
            
            if not self.server_url or self.server_url.strip() == '':
                logger.error("OPC UA Client endpoint not configured")
                return False
            
            logger.info(f"Connecting to OPC UA server: {self.server_url}")
            
            self.client = Client(self.server_url)
            
            # Set security if needed (uncomment when required)
            # if self.security_policy != 'None':
            #     security_string = f"{self.security_policy},{self.security_mode}"
            #     self.client.set_security_string(security_string)
            
            self.client.connect()
            self.connected = True
            
            logger.info(f"Successfully connected to OPC UA server: {self.server_url}")
            
            # Update device status
            try:
                db_service.update_device_status(
                    device_type='opcua',
                    name='S7-1500 PLC',
                    connection_string=self.server_url,
                    status='connected'
                )
            except Exception as db_error:
                logger.warning(f"Could not update device status in database: {db_error}")
            
            # Start monitoring thread for variables configured to store data
            self.start_monitoring()
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to OPC UA server: {error_msg}")
            self.connected = False
            
            # Provide helpful hints based on error type
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                logger.error("HINT: Connection timeout. Check if server is running and reachable.")
            elif "refused" in error_msg.lower():
                logger.error("HINT: Connection refused. Check if OPC-UA server is enabled on S7-1500.")
            elif "name resolution" in error_msg.lower():
                logger.error("HINT: Use IP address instead of hostname.")
            
            return False
    
    def disconnect(self):
        """Disconnect from OPC UA server - working synchronous method"""
        try:
            # Stop monitoring first
            self.stop_monitoring()
            
            # Stop monitoring thread
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
                
            if self.client and self.connected:
                self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from OPC UA server")
                
                # Update device status
                try:
                    db_service.update_device_status(
                        device_type='opcua',
                        name='S7-1500 PLC',
                        connection_string=self.server_url,
                        status='disconnected'
                    )
                except Exception as db_error:
                    logger.warning(f"Could not update device status in database: {db_error}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            self.connected = False
            return False
    
    def write_variable(self, node_id: str, value: any) -> tuple:
        """
        Write value to OPC UA variable on S7-1500 PLC
        
        Args:
            node_id: OPC UA node ID (e.g., 'ns=3;s="FB_AHU_5703_DB"."Setpoint"')
            value: Value to write (will be converted to appropriate type)
            
        Returns:
            (success: bool, message: str) - True and 'OK' if write successful, False and error message otherwise
        """
        logger.info(f"write_variable called with node_id={node_id}, value={value}, connected={self.connected}")
        if not self.connected:
            msg = "Cannot write - not connected to OPC UA server"
            logger.error(msg)
            return False, msg
        try:
            logger.info(f"Getting node: {node_id}")
            node = self.client.get_node(node_id)

            # Optional pre-flight info to aid troubleshooting
            try:
                access_level = node.get_attribute(ua.AttributeIds.AccessLevel).Value.Value
                user_access_level = node.get_attribute(ua.AttributeIds.UserAccessLevel).Value.Value
                logger.debug(
                    f"Node access levels for {node_id}: AccessLevel={access_level}, UserAccessLevel={user_access_level}"
                )
            except Exception as access_err:
                logger.debug(f"Could not read access levels for {node_id}: {access_err}")

            # Get the variable's data type to convert value appropriately
            try:
                data_type = node.get_data_type_as_variant_type()
                logger.info(f"Variable data type: {data_type}")
                # Convert value based on data type and create properly typed Variant
                if data_type == ua.VariantType.Boolean:
                    if isinstance(value, bool):
                        typed_value = value
                    elif isinstance(value, (int, float)):
                        typed_value = float(value) != 0.0
                    else:
                        raw = str(value).strip().lower()
                        typed_value = raw in ['true', '1', '1.0', 'on', 'yes']
                    variant = ua.Variant(typed_value, ua.VariantType.Boolean)
                elif data_type == ua.VariantType.Int16:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Int16)
                elif data_type == ua.VariantType.Int32:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Int32)
                elif data_type == ua.VariantType.Int64:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Int64)
                elif data_type == ua.VariantType.UInt16:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.UInt16)
                elif data_type == ua.VariantType.UInt32:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.UInt32)
                elif data_type == ua.VariantType.UInt64:
                    typed_value = int(value)
                    variant = ua.Variant(typed_value, ua.VariantType.UInt64)
                elif data_type == ua.VariantType.Float:
                    typed_value = float(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Float)
                elif data_type == ua.VariantType.Double:
                    typed_value = float(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Double)
                elif data_type == ua.VariantType.String:
                    typed_value = str(value)
                    variant = ua.Variant(typed_value, ua.VariantType.String)
                else:
                    # For unknown types, try auto-detection
                    typed_value = float(value) if isinstance(value, (int, float)) else value
                    variant = ua.Variant(typed_value, data_type)
                logger.info(f"Writing typed value: {typed_value} (type: {data_type})")
            except Exception as type_err:
                logger.warning(f"Could not determine data type: {type_err}, trying default float")
                # If we can't determine type, try to convert to float (most common for PLC)
                try:
                    typed_value = float(value)
                    variant = ua.Variant(typed_value, ua.VariantType.Float)
                except Exception as conv_err:
                    typed_value = value
                    variant = ua.Variant(typed_value)
                    logger.warning(f"Could not convert value to float: {conv_err}")

            # Write the value (match the working approach from the standalone OPC-UA Client)
            try:
                node.set_value(variant)
                logger.info(f"Successfully wrote value {typed_value} to {node_id}")
                return True, "OK"
            except Exception as write_error:
                err_text = str(write_error)

                # Some servers reject DataValue writes with status/timestamps; retry value-only writes.
                if "BadWriteNotSupported" in err_text:
                    logger.warning(f"BadWriteNotSupported for {node_id}. Trying value-only write...")

                    # Method 1: low-level WriteValue with only Value set (no status/timestamps)
                    try:
                        write_request = ua.WriteValue()
                        write_request.NodeId = node.nodeid
                        write_request.AttributeId = ua.AttributeIds.Value

                        data_value = ua.DataValue()
                        data_value.Value = variant
                        write_request.Value = data_value

                        result = self.client.uaclient.write([write_request])
                        if result and result[0].is_good():
                            logger.info(f"Value-only write succeeded for {node_id}")
                            return True, "OK"
                        logger.error(f"Value-only write failed for {node_id}: {result[0] if result else 'no result'}")
                    except Exception as low_level_err:
                        logger.warning(f"Value-only write failed for {node_id}: {low_level_err}")

                    # Method 2: set_attribute on Value with minimal DataValue
                    try:
                        data_value = ua.DataValue(variant)
                        node.set_attribute(ua.AttributeIds.Value, data_value)
                        logger.info(f"set_attribute write succeeded for {node_id}")
                        return True, "OK"
                    except Exception as attr_err:
                        logger.warning(f"set_attribute write failed for {node_id}: {attr_err}")

                    # Method 3: final fallback, let library infer type from Python value
                    try:
                        node.set_value(typed_value)
                        logger.info(f"Auto-type write succeeded for {node_id}")
                        return True, "OK"
                    except Exception as final_err:
                        msg = f"All write methods failed for {node_id}: {final_err}"
                        logger.error(msg)
                        return False, msg

                if "BadTypeMismatch" in err_text:
                    logger.warning(f"BadTypeMismatch for {node_id}. Trying auto-type write...")
                    try:
                        node.set_value(typed_value)
                        logger.info(f"Auto-type write succeeded for {node_id}")
                        return True, "OK"
                    except Exception as auto_err:
                        msg = f"Auto-type write failed for {node_id}: {auto_err}"
                        logger.error(msg)
                        return False, msg

                msg = f"Error writing to {node_id}: {write_error}"
                logger.error(msg)
                return False, msg
        except Exception as e:
            msg = f"Error writing to {node_id}: {e}"
            logger.error(msg)
            return False, msg
    
    def start_monitoring(self):
        """Start monitoring thread for variables configured to store data"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.info("Monitoring thread already running")
            return True
        
        if not self.connected:
            logger.warning("Cannot start monitoring - not connected to OPC UA server")
            return False
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="OPCUAMonitoringThread"
        )
        self.monitoring_thread.start()
        logger.info("Started OPC UA monitoring thread (change detection enabled)")
        return True
    
    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.running = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.info("Stopping monitoring thread...")
            self.monitoring_thread.join(timeout=5)
            logger.info("Monitoring thread stopped")
        self.previous_values.clear()
    
    def _monitoring_loop(self):
        """Monitor variables and write to PostgreSQL only when values change"""
        logger.info("Monitoring loop started")
        
        while self.running:
            try:
                # Get variables configured for database storage
                variables = db_service.get_monitored_variables(enabled_only=True)
                
                for var in variables:
                    # Check if variable should be stored to database
                    if not var.get('store_to_postgres', True):
                        continue
                    
                    try:
                        # Read current value from PLC
                        node = self.client.get_node(var['node_id'])
                        current_value = node.get_value()
                        
                        # Get variable identifier for change tracking
                        var_id = var['id']
                        
                        # Check if value has changed
                        previous_value = self.previous_values.get(var_id)
                        
                        if previous_value is None or current_value != previous_value:
                            # Value changed or first read - store to PostgreSQL
                            try:
                                measurement = var.get('measurement_name') or var['browse_name']
                                
                                tags = {
                                    'source': 'opcua',
                                    'location': var['browse_name']
                                }
                                
                                # Convert to float if numeric, otherwise store as-is
                                try:
                                    field_value = float(current_value)
                                except (ValueError, TypeError):
                                    field_value = current_value
                                
                                fields = {
                                    var['browse_name']: field_value
                                }
                                
                                # Write to PostgreSQL
                                db_service.write_sensor_data(
                                    measurement=measurement,
                                    tags=tags,
                                    fields=fields,
                                    timestamp=datetime.now()
                                )
                                
                                # Update previous value
                                self.previous_values[var_id] = current_value
                                
                                # Log change (DEBUG level to avoid log spam)
                                if previous_value is None:
                                    logger.debug(f"First read: {var['browse_name']} = {current_value}")
                                else:
                                    logger.debug(f"Value changed: {var['browse_name']} = {previous_value} → {current_value}")
                                    
                            except Exception as write_error:
                                logger.error(f"Error writing {var['browse_name']} to PostgreSQL: {write_error}")
                        
                    except Exception as read_error:
                        logger.error(f"Error reading {var['browse_name']}: {read_error}")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Poll every 1 second
            time.sleep(1)
        
        logger.info("Monitoring loop stopped")
    
    def browse_simple(self, node_id: str = "i=85") -> List[Dict]:
        """Simple browse method that shows both folders and variables - synchronous approach"""
        try:
            if not self.connected:
                logger.error("Not connected to OPC UA server")
                return []
                
            logger.info(f"Starting simple browse from node: {node_id}")
            results = []
            
            try:
                # Get the starting node
                start_node = self.client.get_node(node_id)
                logger.debug(f"Successfully got start node: {start_node}")
                
                # Get direct children of this node
                children = start_node.get_children()
                logger.info(f"Found {len(children)} children for node {node_id}")
                
                for i, child in enumerate(children):
                    try:
                        logger.debug(f"Processing child {i+1}/{len(children)}: {child.nodeid}")
                        
                        node_class = child.get_node_class()
                        browse_name = child.get_browse_name()
                        display_name = child.get_display_name()
                        
                        logger.debug(f"Child info - Class: {node_class}, Browse: {browse_name.Name}, Display: {display_name.Text}")
                        
                        item_info = {
                            'node_id': child.nodeid.to_string(),
                            'browse_name': browse_name.Name,
                            'display_name': display_name.Text,
                            'namespace_index': browse_name.NamespaceIndex,
                        }
                        
                        if node_class == ua.NodeClass.Variable:
                            # This is a variable
                            item_info['type'] = 'variable'
                            item_info['is_variable'] = True
                            item_info['can_select'] = True
                            
                            # Try to read current value and data type
                            try:
                                value = child.get_value()
                                item_info['current_value'] = str(value)
                                
                                data_type = child.get_data_type()
                                item_info['data_type'] = self._simplify_data_type(data_type.to_string())
                                
                            except Exception as val_error:
                                logger.debug(f"Could not read value for {browse_name.Name}: {val_error}")
                                item_info['current_value'] = 'N/A'
                                item_info['data_type'] = 'unknown'
                                
                        elif node_class == ua.NodeClass.Object:
                            # This is a folder/object
                            item_info['type'] = 'folder'
                            item_info['is_variable'] = False
                            item_info['can_select'] = False
                            
                            # Check if it has children - be more thorough
                            try:
                                child_nodes = child.get_children()
                                children_count = len(child_nodes)
                                item_info['has_children'] = children_count > 0
                                item_info['children_count'] = children_count
                                logger.debug(f"Folder {browse_name.Name} has {children_count} children")
                            except Exception as child_error:
                                logger.warning(f"Could not get children for folder {browse_name.Name}: {child_error}")
                                item_info['has_children'] = False
                                item_info['children_count'] = 0
                                
                        elif node_class == ua.NodeClass.VariableType:
                            # Variable types might also be browsable
                            item_info['type'] = 'variable_type'
                            item_info['is_variable'] = False
                            item_info['can_select'] = False
                            
                            # Check for children 
                            try:
                                child_nodes = child.get_children()
                                item_info['has_children'] = len(child_nodes) > 0
                            except:
                                item_info['has_children'] = False
                                
                        else:
                            # Other node types (methods, data types, etc.)
                            item_info['type'] = 'other'
                            item_info['is_variable'] = False
                            item_info['can_select'] = False
                            
                            # Still check for children
                            try:
                                child_nodes = child.get_children()
                                item_info['has_children'] = len(child_nodes) > 0
                            except:
                                item_info['has_children'] = False
                            
                        results.append(item_info)
                        logger.debug(f"Added item: {item_info}")
                        
                    except Exception as e:
                        logger.warning(f"Error processing child node {i+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to browse node {node_id}: {e}")
                return []
            
            # Sort results: folders first, then variables
            results.sort(key=lambda x: (x['type'] != 'folder', x['browse_name'].lower()))
            
            logger.info(f"Browse found {len(results)} items from {node_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error in simple browse: {e}")
            return []
    
    def _extract_variable_info(self, node, variables_list, depth=0, max_depth=2):
        """Extract variable information from a node - synchronous"""
        if depth > max_depth:
            return
            
        try:
            node_class = node.get_node_class()
            
            if node_class == ua.NodeClass.Variable:
                # This is a variable, extract its info
                try:
                    browse_name = node.get_browse_name()
                    display_name = node.get_display_name()
                    
                    variable_info = {
                        'node_id': node.nodeid.to_string(),
                        'browse_name': browse_name.Name,
                        'display_name': display_name.Text,
                        'namespace_index': browse_name.NamespaceIndex,
                        'is_variable': True,
                        'depth': depth
                    }
                    
                    # Try to read current value and data type
                    try:
                        value = node.get_value()
                        variable_info['current_value'] = str(value)
                        
                        data_type = node.get_data_type()
                        variable_info['data_type'] = self._simplify_data_type(data_type.to_string())
                        
                    except:
                        variable_info['current_value'] = 'N/A'
                        variable_info['data_type'] = 'unknown'
                    
                    variables_list.append(variable_info)
                    logger.debug(f"Found variable: {browse_name.Name}")
                    
                except Exception as e:
                    logger.debug(f"Error extracting variable info: {e}")
                    
            elif node_class == ua.NodeClass.Object and depth < max_depth:
                # This is an object, browse its children
                try:
                    children = node.get_children()
                    for child in children[:5]:  # Limit children per object
                        self._extract_variable_info(child, variables_list, depth + 1, max_depth)
                except:
                    pass  # Skip if can't browse children
                    
        except Exception as e:
            logger.debug(f"Error processing node: {e}")
    
    def _simplify_data_type(self, data_type_str):
        """Simplify complex data type strings"""
        if 'Boolean' in data_type_str:
            return 'boolean'
        elif 'Int' in data_type_str:
            return 'int'
        elif 'Float' in data_type_str or 'Double' in data_type_str:
            return 'float'
        elif 'String' in data_type_str:
            return 'string'
        else:
            return 'unknown'
    
    def test_node_access(self, node_id: str) -> Dict:
        """Test if a node ID can be accessed - synchronous"""
        try:
            if not self.connected:
                return {'success': False, 'error': 'Not connected to server', 'accessible': False}
            
            node = self.client.get_node(node_id)
            
            # Try to read basic properties
            browse_name = node.get_browse_name()
            node_class = node.get_node_class()
            
            result = {
                'success': True,
                'browse_name': browse_name.Name,
                'node_class': node_class.name,
                'accessible': True
            }
            
            # If it's a variable, try to read value
            if node_class == ua.NodeClass.Variable:
                try:
                    value = node.get_value()
                    result['current_value'] = str(value)
                    result['value'] = value
                    result['can_read'] = True
                except:
                    result['current_value'] = 'Cannot read'
                    result['value'] = None
                    result['can_read'] = False
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'accessible': False
            }
    
    def get_namespaces(self) -> List[Dict]:
        """Get available namespaces - synchronous"""
        try:
            if not self.connected:
                return []
            
            namespaces = self.client.get_namespace_array()
            ns_list = []
            
            for i, ns in enumerate(namespaces):
                ns_info = {
                    'index': i,
                    'uri': ns,
                    'is_siemens': any(keyword in ns.lower() for keyword in ['siemens', 's7', 'plc', 'db', 'datablock'])
                }
                ns_list.append(ns_info)
            
            return ns_list
            
        except Exception as e:
            logger.error(f"Error getting namespaces: {e}")
            return []
    
    def run(self):
        """Main run loop - simplified for manual control"""
        self.running = True
        
        # Only auto-connect if endpoint is properly configured
        if not Config.OPCUA_CLIENT_ENDPOINT or Config.OPCUA_CLIENT_ENDPOINT.strip() == '':
            logger.info("OPC UA Client endpoint not configured - waiting for manual configuration")
            while self.running and (not Config.OPCUA_CLIENT_ENDPOINT or Config.OPCUA_CLIENT_ENDPOINT.strip() == ''):
                time.sleep(5)
            if not self.running:
                return
        
        # Try to connect once, then wait for manual control
        if not self.connected:
            logger.info("Attempting initial connection...")
            self.connect()
        
        # Keep service alive
        while self.running:
            time.sleep(5)
            # Simple connection check
            if self.connected and self.client:
                try:
                    # Simple keep-alive check
                    root = self.client.get_root_node()
                    root.get_browse_name()
                except:
                    logger.warning("Connection lost, marking as disconnected")
                    self.connected = False
        
        logger.info("OPC UA Client service stopped")
    
    def stop(self):
        """Stop the client"""
        self.running = False
        self.disconnect()
        
    def browse_debug(self, node_id: str) -> Dict:
        """Debug method to get detailed information about a specific node"""
        try:
            if not self.connected:
                return {'error': 'Not connected to OPC UA server'}
                
            logger.info(f"Debug browsing node: {node_id}")
            
            node = self.client.get_node(node_id)
            
            # Get basic node info
            node_class = node.get_node_class()
            browse_name = node.get_browse_name()
            display_name = node.get_display_name()
            
            debug_info = {
                'node_id': node_id,
                'node_class': str(node_class),
                'browse_name': browse_name.Name,
                'display_name': display_name.Text,
                'namespace_index': browse_name.NamespaceIndex,
            }
            
            # Try different ways to get children
            children_methods = []
            
            # Method 1: get_children()
            try:
                children = node.get_children()
                children_methods.append({
                    'method': 'get_children()',
                    'count': len(children),
                    'success': True,
                    'children': [{'node_id': c.nodeid.to_string(), 'browse_name': c.get_browse_name().Name} for c in children[:5]]
                })
            except Exception as e:
                children_methods.append({
                    'method': 'get_children()',
                    'success': False,
                    'error': str(e)
                })
            
            # Method 2: browse references directly
            try:
                references = node.get_references()
                ref_count = len(references)
                children_methods.append({
                    'method': 'get_references()',
                    'count': ref_count,
                    'success': True,
                    'sample_refs': [str(ref) for ref in references[:3]]
                })
            except Exception as e:
                children_methods.append({
                    'method': 'get_references()',
                    'success': False,
                    'error': str(e)
                })
                
            # Method 3: browse with specific reference types
            try:
                hierarchical_refs = node.get_children_descriptions(refs=ua.ObjectIds.HierarchicalReferences)
                children_methods.append({
                    'method': 'get_children_descriptions(HierarchicalReferences)',
                    'count': len(hierarchical_refs),
                    'success': True,
                    'sample_children': [{'browse_name': desc.BrowseName.Name, 'node_class': str(desc.NodeClass)} for desc in hierarchical_refs[:5]]
                })
            except Exception as e:
                children_methods.append({
                    'method': 'get_children_descriptions(HierarchicalReferences)',
                    'success': False,
                    'error': str(e)
                })
            
            debug_info['children_methods'] = children_methods
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Error in debug browse: {e}")
            return {'error': str(e)}

    def search_variables(self, query: str, start_node_id: str = 'i=85', max_results: int = 50,
                         max_depth: int = 6, max_nodes: int = 5000) -> List[Dict]:
        """Search for variables by browse_name (substring, case-insensitive).

        This is a bounded BFS to avoid huge traversals on large servers.
        Returns variable nodes with node_id + browse_name (+ optional display_name/current_value).
        """
        if not self.connected or not self.client:
            return []

        query = (query or '').strip()
        if not query:
            return []

        try:
            start_node = self.client.get_node(start_node_id)
        except Exception:
            start_node = self.client.get_node('i=85')

        needle = query.lower()
        results: List[Dict] = []
        visited = set()

        # (node, depth)
        queue = [(start_node, 0)]
        visited.add(start_node.nodeid.to_string())
        nodes_processed = 0

        while queue and len(results) < max_results and nodes_processed < max_nodes:
            node, depth = queue.pop(0)
            nodes_processed += 1

            try:
                node_class = node.get_node_class()
            except Exception:
                continue

            # Match variables
            if node_class == ua.NodeClass.Variable:
                try:
                    browse_name = node.get_browse_name().Name
                except Exception:
                    browse_name = ''

                if browse_name and needle in browse_name.lower():
                    item = {
                        'node_id': node.nodeid.to_string(),
                        'browse_name': browse_name,
                    }
                    try:
                        item['display_name'] = node.get_display_name().Text
                    except Exception:
                        pass
                    try:
                        item['current_value'] = str(node.get_value())
                    except Exception:
                        pass
                    results.append(item)

            # Traverse objects/folders
            if depth >= max_depth:
                continue

            if node_class in (ua.NodeClass.Object, ua.NodeClass.View):
                try:
                    children = node.get_children()
                except Exception:
                    continue

                for child in children:
                    child_id = child.nodeid.to_string()
                    if child_id in visited:
                        continue
                    visited.add(child_id)
                    queue.append((child, depth + 1))

        return results

# Global OPC UA client instance
opcua_client = OPCUAClientService()