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
            
            # Set a reasonable session timeout (S7-1500 typically allows max 30 seconds)
            # Default asyncua requests 1 hour which S7-1500 rejects
            self.client.session_timeout = 30000  # 30 seconds in milliseconds
            
            # For asyncua, we don't need to call set_security_string for 'None'
            # Only set it if we're using actual security
            if self.security_policy != 'None':
                security_string = f"{self.security_policy},{self.security_mode}"
                logger.info(f"Setting security string: {security_string}")
                await self.client.set_security_string(security_string)
            else:
                logger.info("Using no security (anonymous connection)")
            
            logger.info("Initiating connection...")
            await self.client.connect()
            
            self.connected = True
            logger.info(f"Successfully connected to OPC UA server: {Config.OPCUA_CLIENT_ENDPOINT}")
            
            # Update device status (ignore errors - non-critical)
            try:
                db_service.update_device_status(
                    device_type='opcua',
                    name='S7-1500 PLC',
                    connection_string=Config.OPCUA_CLIENT_ENDPOINT,
                    status='connected'
                )
            except Exception as db_error:
                logger.warning(f"Could not update device status in database: {db_error}")
            
            # Create subscription
            await self._create_subscription()
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to OPC UA server: {error_msg}", exc_info=True)
            logger.error(f"Connection details: Endpoint={Config.OPCUA_CLIENT_ENDPOINT}, Security={self.security_policy}/{self.security_mode}")
            
            # Provide helpful hints based on error type
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                logger.error("HINT: Connection timeout. Check if server is running and reachable.")
            elif "security" in error_msg.lower() or "certificate" in error_msg.lower():
                logger.error("HINT: Security/certificate issue. Try setting security policy to 'None' for S7-1500.")
            elif "refused" in error_msg.lower():
                logger.error("HINT: Connection refused. Check if OPC UA server is enabled on the PLC.")
            
            self.connected = False
            
            # Update device status (ignore errors - non-critical)
            try:
                db_service.update_device_status(
                    device_type='opcua',
                    name='S7-1500 PLC',
                    connection_string=Config.OPCUA_CLIENT_ENDPOINT,
                    status='disconnected'
                )
            except Exception as db_error:
                logger.warning(f"Could not update device status in database: {db_error}")
            
            return False
    
    async def disconnect(self):
        """Disconnect from OPC UA server"""
        try:
            if self.subscription:
                await self.subscription.delete()
                self.subscription = None
            
            if self.client:
                await self.client.disconnect()
                self.client = None
            
            self.connected = False
            logger.info("Disconnected from OPC UA server")
            
            db_service.update_device_status(
                device_type='opcua',
                name='S7-1500 PLC',
                connection_string=Config.OPCUA_CLIENT_ENDPOINT,
                status='disconnected'
            )
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def _create_subscription(self):
        """Create OPC UA subscription for monitored items"""
        try:
            handler = SubscriptionHandler(callback=self._on_data_change)
            self.subscription = await self.client.create_subscription(
                Config.OPCUA_SUBSCRIPTION_INTERVAL,
                handler
            )
            logger.info(f"Created subscription with {Config.OPCUA_SUBSCRIPTION_INTERVAL}ms interval")
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
    
    def _on_data_change(self, node, value, data):
        """Callback when subscribed variable changes"""
        try:
            node_id = node.nodeid.to_string()
            
            # Store to database if configured
            monitored_vars = db_service.get_monitored_variables()
            for var in monitored_vars:
                if var['node_id'] == node_id and var['store_to_influxdb']:
                    measurement = var['measurement_name'] or var['browse_name']
                    
                    db_service.write_sensor_data(
                        measurement=measurement,
                        tags={
                            'source': 'opcua',
                            'node_id': node_id,
                            'device': 'S7-1500'
                        },
                        fields={
                            'value': value
                        },
                        timestamp=datetime.now()
                    )
                    break
                    
        except Exception as e:
            logger.error(f"Error processing data change: {e}")
            
    async def _browse_s7_1500_specific(self) -> List[Dict]:
        """Browse S7-1500 specific node paths"""
        results = []
        
        # First, try to get namespaces to understand the structure
        try:
            namespaces = await self.client.get_namespace_array()
            logger.info(f"Available namespaces: {namespaces}")
            
            # Look for Siemens-specific namespace URIs
            siemens_ns_indexes = []
            for i, ns_uri in enumerate(namespaces):
                if any(keyword in ns_uri.lower() for keyword in ['siemens', 's7', 'plc', 'db', 'datablock']):
                    siemens_ns_indexes.append(i)
                    logger.info(f"Found Siemens namespace {i}: {ns_uri}")
            
            if not siemens_ns_indexes:
                # If no specific Siemens namespaces found, try namespace indexes 3 and 4 (common for S7)
                siemens_ns_indexes = [3, 4]
                logger.info(f"No Siemens namespaces found, trying default indexes: {siemens_ns_indexes}")
                
        except Exception as e:
            logger.warning(f"Could not get namespaces: {e}")
            siemens_ns_indexes = [3, 4]
        
        # Common S7-1500 node paths to try (updated with dynamic namespace indexes)
        s7_paths = [
            "i=2253",  # Server namespace
            "i=2254",  # Server array
            "i=2255",  # Namespace array
            "i=85",    # Objects folder
        ]
        
        # Add namespace-specific paths
        for ns_idx in siemens_ns_indexes:
            s7_paths.extend([
                f"ns={ns_idx};s=\"DataBlocksGlobal\"",
                f"ns={ns_idx};s=\"DB\"",
                f"ns={ns_idx};s=\"DB1\"", 
                f"ns={ns_idx};s=\"PLC_1\"",
                f"ns={ns_idx};s=\"Program\"",
                f"ns={ns_idx};s=\"Static\"",
                f"ns={ns_idx};s=\"MAIN\"",
                f"ns={ns_idx};s=\"Global\"",
                f"ns={ns_idx};s=\"Application\"",
                f"ns={ns_idx};s=\"CPU\"",
                f"ns={ns_idx};i=1000",  # Often used starting point
            ])
        
        logger.info(f"Trying {len(s7_paths)} S7-1500 specific paths")
        
        for path in s7_paths:
            try:
                logger.debug(f"Trying path: {path}")
                node = self.client.get_node(path)
                
                # Try to read basic info with short timeout
                node_class = await asyncio.wait_for(node.read_node_class(), timeout=2.0)
                browse_name = await asyncio.wait_for(node.read_browse_name(), timeout=2.0)
                display_name = await asyncio.wait_for(node.read_display_name(), timeout=2.0)
                
                node_info = {
                    'node_id': path,
                    'browse_name': browse_name.Name,
                    'display_name': display_name.Text,
                    'namespace_index': browse_name.NamespaceIndex,
                    'node_class': node_class.name,
                    'depth': 0,
                    'is_variable': node_class == ua.NodeClass.Variable,
                    'children': []
                }
                
                if node_class == ua.NodeClass.Variable:
                    try:
                        value = await asyncio.wait_for(node.read_value(), timeout=2.0)
                        node_info['current_value'] = str(value)
                        logger.info(f"Found S7-1500 variable: {path} = {value}")
                    except:
                        node_info['current_value'] = "N/A"
                
                results.append(node_info)
                logger.info(f"Found S7-1500 node: {path} ({browse_name.Name})")
                
                # If it's an object, try to browse one level deeper
                if node_class == ua.NodeClass.Object:
                    try:
                        children = await asyncio.wait_for(node.get_children(), timeout=3.0)
                        children_info = []
                        
                        for child in children[:20]:  # Limit to first 20 children
                            try:
                                child_class = await asyncio.wait_for(child.read_node_class(), timeout=1.0)
                                child_browse = await asyncio.wait_for(child.read_browse_name(), timeout=1.0)
                                child_display = await asyncio.wait_for(child.read_display_name(), timeout=1.0)
                                
                                child_info = {
                                    'node_id': child.nodeid.to_string(),
                                    'browse_name': child_browse.Name,
                                    'display_name': child_display.Text,
                                    'namespace_index': child_browse.NamespaceIndex,
                                    'node_class': child_class.name,
                                    'depth': 1,
                                    'is_variable': child_class == ua.NodeClass.Variable,
                                    'children': []
                                }
                                
                                if child_class == ua.NodeClass.Variable:
                                    try:
                                        value = await asyncio.wait_for(child.read_value(), timeout=1.0)
                                        child_info['current_value'] = str(value)
                                        logger.info(f"Found child variable: {child.nodeid.to_string()} = {value}")
                                    except:
                                        child_info['current_value'] = "N/A"
                                
                                children_info.append(child_info)
                                
                            except Exception as e:
                                logger.debug(f"Error reading child {child}: {e}")
                                continue
                        
                        node_info['children'] = children_info
                        logger.info(f"Found {len(children_info)} children for {path}")
                        
                    except Exception as e:
                        logger.debug(f"Error browsing children of {path}: {e}")
                
            except Exception as e:
                logger.debug(f"Error accessing S7-1500 path {path}: {e}")
                continue
        
        logger.info(f"S7-1500 specific browse completed, found {len(results)} top-level nodes")
        return results
    
    async def browse_comprehensive(self) -> List[Dict]:
        """Fast comprehensive browse using optimized strategies"""
        all_results = []
        
        logger.info("Starting fast comprehensive browse")
        
        # Strategy 1: Try key root nodes with limited depth
        key_roots = [
            "i=85",   # Objects (most important)
            "i=2253", # Server
        ]
        
        for root_id in key_roots:
            try:
                logger.info(f"Trying root node: {root_id}")
                node = self.client.get_node(root_id)
                
                # Quick check if node exists
                browse_name = await asyncio.wait_for(node.read_browse_name(), timeout=1.0)
                logger.info(f"Root {root_id}: {browse_name.Name}")
                
                # Get children quickly
                children = await asyncio.wait_for(node.get_children(), timeout=3.0)
                logger.info(f"Root {root_id} has {len(children)} children")
                
                # Process only first 15 children for speed
                for child in children[:15]:
                    try:
                        child_browse = await asyncio.wait_for(child.read_browse_name(), timeout=0.5)
                        child_class = await asyncio.wait_for(child.read_node_class(), timeout=0.5)
                        
                        child_info = {
                            'node_id': child.nodeid.to_string(),
                            'browse_name': child_browse.Name,
                            'display_name': child_browse.Name,
                            'namespace_index': child_browse.NamespaceIndex,
                            'node_class': child_class.name,
                            'depth': 1,
                            'is_variable': child_class == ua.NodeClass.Variable,
                            'parent_root': root_id,
                            'children': []
                        }
                        
                        # If it's a variable, try to read value quickly
                        if child_class == ua.NodeClass.Variable:
                            try:
                                value = await asyncio.wait_for(child.read_value(), timeout=0.5)
                                child_info['current_value'] = str(value)
                                logger.info(f"Variable: {child_browse.Name} = {value}")
                            except:
                                child_info['current_value'] = "N/A"
                        
                        # If it's an object, try one level deeper (max 10 children)
                        elif child_class == ua.NodeClass.Object:
                            try:
                                grandchildren = await asyncio.wait_for(child.get_children(), timeout=2.0)
                                
                                gc_list = []
                                for gc in grandchildren[:10]:  # Limit to 10 for speed
                                    try:
                                        gc_browse = await asyncio.wait_for(gc.read_browse_name(), timeout=0.3)
                                        gc_class = await asyncio.wait_for(gc.read_node_class(), timeout=0.3)
                                        
                                        gc_info = {
                                            'node_id': gc.nodeid.to_string(),
                                            'browse_name': gc_browse.Name,
                                            'display_name': gc_browse.Name,
                                            'namespace_index': gc_browse.NamespaceIndex,
                                            'node_class': gc_class.name,
                                            'depth': 2,
                                            'is_variable': gc_class == ua.NodeClass.Variable,
                                            'children': []
                                        }
                                        
                                        if gc_class == ua.NodeClass.Variable:
                                            try:
                                                value = await asyncio.wait_for(gc.read_value(), timeout=0.3)
                                                gc_info['current_value'] = str(value)
                                                logger.info(f"Nested variable: {gc_browse.Name} = {value}")
                                            except:
                                                gc_info['current_value'] = "N/A"
                                        
                                        gc_list.append(gc_info)
                                        
                                    except:
                                        continue  # Skip problematic grandchildren
                                
                                child_info['children'] = gc_list
                                
                            except:
                                pass  # Skip if can't browse children
                        
                        all_results.append(child_info)
                        
                    except:
                        continue  # Skip problematic children
                    
            except Exception as e:
                logger.warning(f"Error with root {root_id}: {e}")
                continue
        
        # Strategy 2: Quick S7-1500 specific paths (only most common ones)
        s7_quick_paths = [
            "ns=3;s=\"DB1\"",
            "ns=4;s=\"DB1\"",
            "ns=3;s=\"DataBlocksGlobal\"",
            "ns=4;s=\"DataBlocksGlobal\"",
        ]
        
        for path in s7_quick_paths:
            try:
                node = self.client.get_node(path)
                browse_name = await asyncio.wait_for(node.read_browse_name(), timeout=0.5)
                node_class = await asyncio.wait_for(node.read_node_class(), timeout=0.5)
                
                path_info = {
                    'node_id': path,
                    'browse_name': browse_name.Name,
                    'display_name': browse_name.Name,
                    'namespace_index': browse_name.NamespaceIndex,
                    'node_class': node_class.name,
                    'depth': 0,
                    'is_variable': node_class == ua.NodeClass.Variable,
                    'source': 's7_specific',
                    'children': []
                }
                
                if node_class == ua.NodeClass.Variable:
                    try:
                        value = await asyncio.wait_for(node.read_value(), timeout=0.5)
                        path_info['current_value'] = str(value)
                        logger.info(f"S7 variable: {browse_name.Name} = {value}")
                    except:
                        path_info['current_value'] = "N/A"
                
                all_results.append(path_info)
                
            except:
                continue  # Skip if path doesn't exist
        
        logger.info(f"Fast comprehensive browse completed, found {len(all_results)} nodes")
        return all_results
    
    async def browse_simple(self) -> List[Dict]:
        """Simple browse method that actually works - inspired by working OPC-UA Client"""
        try:
            logger.info("Starting simple browse for variables...")
            
            variables = []
            
            # Try common S7-1500 paths with known variables
            common_paths = [
                # Namespace 3 is commonly used by Siemens
                "ns=3;s=\"DB1\"",
                "ns=3;s=\"DataBlocksGlobal\"", 
                "ns=3;s=\"Global\"",
                "ns=3;s=\"PLC_1\"",
                # Namespace 4 is also common
                "ns=4;s=\"DB1\"",
                "ns=4;s=\"DataBlocksGlobal\"",
                "ns=4;s=\"Global\"",
                "ns=4;s=\"PLC_1\"",
                # Standard OPC-UA paths
                "i=85",  # Objects folder
                "i=86",  # Types folder
            ]
            
            for base_path in common_paths:
                try:
                    logger.debug(f"Trying base path: {base_path}")
                    base_node = self.client.get_node(base_path)
                    
                    # Try to browse this node and its children
                    children = await asyncio.wait_for(base_node.get_children(), timeout=3.0)
                    
                    for child in children[:10]:  # Limit to first 10 children
                        try:
                            await self._extract_variable_info(child, variables, depth=0, max_depth=2)
                        except:
                            continue  # Skip problematic children
                            
                except Exception as e:
                    logger.debug(f"Failed to browse {base_path}: {e}")
                    continue
            
            # Remove duplicates based on node_id
            unique_variables = []
            seen_node_ids = set()
            
            for var in variables:
                if var['node_id'] not in seen_node_ids:
                    unique_variables.append(var)
                    seen_node_ids.add(var['node_id'])
            
            logger.info(f"Simple browse found {len(unique_variables)} unique variables")
            return unique_variables
            
        except Exception as e:
            logger.error(f"Error in simple browse: {e}", exc_info=True)
            return []
    
    async def _extract_variable_info(self, node, variables_list, depth=0, max_depth=2):
        """Extract variable information from a node"""
        if depth > max_depth:
            return
            
        try:
            node_class = await asyncio.wait_for(node.read_node_class(), timeout=1.0)
            
            if node_class == ua.NodeClass.Variable:
                # This is a variable, extract its info
                try:
                    browse_name = await asyncio.wait_for(node.read_browse_name(), timeout=1.0)
                    display_name = await asyncio.wait_for(node.read_display_name(), timeout=1.0)
                    
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
                        value = await asyncio.wait_for(node.read_value(), timeout=1.0)
                        variable_info['current_value'] = str(value)
                        
                        data_type = await asyncio.wait_for(node.read_data_type(), timeout=1.0)
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
                    children = await asyncio.wait_for(node.get_children(), timeout=2.0)
                    for child in children[:5]:  # Limit children per object
                        await self._extract_variable_info(child, variables_list, depth + 1, max_depth)
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
    
    async def test_node_access(self, node_id: str) -> Dict:
        """Test if a node ID can be accessed"""
        try:
            node = self.client.get_node(node_id)
            
            # Try to read basic properties
            browse_name = await asyncio.wait_for(node.read_browse_name(), timeout=2.0)
            node_class = await asyncio.wait_for(node.read_node_class(), timeout=2.0)
            
            result = {
                'success': True,
                'browse_name': browse_name.Name,
                'node_class': node_class.name,
                'accessible': True
            }
            
            # If it's a variable, try to read value
            if node_class == ua.NodeClass.Variable:
                try:
                    value = await asyncio.wait_for(node.read_value(), timeout=2.0)
                    result['current_value'] = str(value)
                    result['can_read'] = True
                except:
                    result['current_value'] = 'Cannot read'
                    result['can_read'] = False
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'accessible': False
            }
    
    async def is_session_valid(self) -> bool:
        """Check if the current OPC UA session is still valid"""
        if not self.connected:
            return False
        
        try:
            # Try a simple operation to test session validity
            root = self.client.get_root_node()
            await root.read_browse_name()
            return True
        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return False
    
    async def ensure_connection(self) -> bool:
        """Ensure we have a valid connection, reconnect if necessary"""
        if not self.connected:
            logger.info("Not connected, attempting to connect...")
            return await self.connect()
        
        # Check if session is still valid
        if not await self.is_session_valid():
            logger.info("Session invalid, reconnecting...")
            try:
                await self.disconnect()
            except:
                pass  # Ignore disconnect errors
            return await self.connect()
        
        return True

    async def browse_node(self, node_id: str = "i=85", max_depth: int = 10) -> List[Dict]:
        """Browse OPC UA node recursively"""
        if not self.connected:
            logger.error("Not connected to OPC UA server")
            return []
        
        try:
            # Check cache
            cache_key = f"{node_id}_{max_depth}"
            if cache_key in self.browse_cache:
                logger.debug(f"Returning cached browse result for {node_id}")
                return self.browse_cache[cache_key]
            
            # Browse from node
            node = self.client.get_node(node_id)
            result = await self._browse_recursive(node, depth=0, max_depth=max_depth)
            
            # Cache result
            self.browse_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to browse node {node_id}: {e}", exc_info=True)
            return []
    
    async def browse_node_safe(self, node_id: str = "i=85", max_depth: int = 2) -> List[Dict]:
        """Safe browse method optimized for S7-1500 PLCs"""
        
        # Ensure we have a valid connection
        if not await self.ensure_connection():
            logger.error("Could not establish valid connection for browsing")
            return []
        
        try:
            logger.info(f"Starting safe browse of node {node_id} with max_depth {max_depth}")
            
            # Check cache first
            cache_key = f"safe_{node_id}_{max_depth}"
            if cache_key in self.browse_cache:
                logger.debug(f"Returning cached safe browse result for {node_id}")
                return self.browse_cache[cache_key]
            
            # For S7-1500, try specific known paths first
            if node_id == "i=85":
                result = await self._browse_s7_1500_specific()
                if result:
                    self.browse_cache[cache_key] = result
                    logger.info(f"S7-1500 specific browse found {len(result)} nodes")
                    return result
            
            # Browse with timeout protection
            node = self.client.get_node(node_id)
            
            # Use asyncio.wait_for with timeout for the browse operation
            result = await asyncio.wait_for(
                self._browse_safe_recursive(node, depth=0, max_depth=max_depth),
                timeout=15.0  # Reduced to 15 second timeout for browse operation
            )
            
            # Cache successful result
            self.browse_cache[cache_key] = result
            logger.info(f"Safe browse completed successfully, found {len(result)} nodes")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Browse operation timed out for node {node_id}")
            return []
        except Exception as e:
            logger.error(f"Failed to safely browse node {node_id}: {e}", exc_info=True)
            return []
    
    async def _browse_recursive(self, node, depth: int = 0, max_depth: int = 10) -> List[Dict]:
        """Recursively browse OPC UA address space"""
        if depth > max_depth:
            return []
        
        results = []
        
        try:
            children = await node.get_children()
            
            for child in children:
                try:
                    node_class = await child.read_node_class()
                    browse_name = await child.read_browse_name()
                    display_name = await child.read_display_name()
                    node_id = child.nodeid.to_string()
                    
                    node_info = {
                        'node_id': node_id,
                        'browse_name': browse_name.Name,
                        'display_name': display_name.Text,
                        'namespace_index': browse_name.NamespaceIndex,
                        'node_class': node_class.name,
                        'depth': depth
                    }
                    
                    if node_class == ua.NodeClass.Variable:
                        # Get variable details
                        try:
                            data_type = await child.read_data_type()
                            data_type_name = data_type.to_string()
                            
                            try:
                                value = await child.read_value()
                                current_value = str(value)
                            except:
                                current_value = "N/A"
                            
                            node_info.update({
                                'data_type': data_type_name,
                                'current_value': current_value,
                                'is_variable': True,
                                'children': []
                            })
                        except Exception as e:
                            logger.debug(f"Could not read variable details: {e}")
                            node_info['is_variable'] = True
                            node_info['children'] = []
                        
                        results.append(node_info)
                        
                    elif node_class == ua.NodeClass.Object:
                        # Recursively browse objects
                        node_info['is_variable'] = False
                        node_info['children'] = await self._browse_recursive(
                            child, 
                            depth + 1, 
                            max_depth
                        )
                        results.append(node_info)
                        
                except Exception as e:
                    logger.debug(f"Error browsing child node: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error browsing children: {e}")
        
        return results
    
    async def _browse_safe_recursive(self, node, depth: int = 0, max_depth: int = 2) -> List[Dict]:
        """Safely browse OPC UA address space with S7-1500 optimizations"""
        if depth > max_depth:
            return []
        
        results = []
        
        try:
            # Add shorter timeout for get_children operation
            try:
                children = await asyncio.wait_for(node.get_children(), timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout browsing children of {node.nodeid.to_string()}")
                return []
            
            # Limit the number of children processed to prevent overwhelming S7-1500
            max_children = 20 if depth == 0 else 10
            children = children[:max_children]
            
            for child in children:
                try:
                    # Add shorter timeouts for each child operation
                    node_class = await asyncio.wait_for(child.read_node_class(), timeout=1.0)
                    browse_name = await asyncio.wait_for(child.read_browse_name(), timeout=1.0)
                    display_name = await asyncio.wait_for(child.read_display_name(), timeout=1.0)
                    node_id = child.nodeid.to_string()
                    
                    node_info = {
                        'node_id': node_id,
                        'browse_name': browse_name.Name,
                        'display_name': display_name.Text,
                        'namespace_index': browse_name.NamespaceIndex,
                        'node_class': node_class.name,
                        'depth': depth
                    }
                    
                    if node_class == ua.NodeClass.Variable:
                        # Simplified variable handling for S7-1500 compatibility
                        node_info['is_variable'] = True
                        node_info['children'] = []
                        
                        # Only try to read value if we're at a reasonable depth
                        if depth <= 1:
                            try:
                                value = await asyncio.wait_for(child.read_value(), timeout=3.0)
                                node_info['current_value'] = str(value)
                            except (asyncio.TimeoutError, Exception):
                                node_info['current_value'] = "N/A"
                        else:
                            node_info['current_value'] = "N/A"
                        
                        results.append(node_info)
                        
                    elif node_class == ua.NodeClass.Object and depth < max_depth:
                        # Only recurse into objects if we haven't reached max depth
                        node_info['is_variable'] = False
                        
                        # Recursively browse objects with timeout
                        try:
                            children_result = await asyncio.wait_for(
                                self._browse_safe_recursive(child, depth + 1, max_depth),
                                timeout=10.0
                            )
                            node_info['children'] = children_result
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout browsing children of {node_id}")
                            node_info['children'] = []
                        
                        results.append(node_info)
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout processing child node at depth {depth}")
                    continue
                except Exception as e:
                    logger.debug(f"Error browsing child node: {e}")
                    continue
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting children at depth {depth}")
        except Exception as e:
            logger.error(f"Error browsing children: {e}")
        
        return results
    
    async def subscribe_to_variable(self, node_id: str):
        """Subscribe to a specific variable"""
        if not self.connected or not self.subscription:
            logger.error("Cannot subscribe: not connected or no subscription")
            return False
        
        try:
            node = self.client.get_node(node_id)
            handle = await self.subscription.subscribe_data_change(node)
            
            self.monitored_nodes[node_id] = {
                'node': node,
                'handle': handle
            }
            
            logger.info(f"Subscribed to variable: {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {node_id}: {e}")
            return False
    
    async def unsubscribe_from_variable(self, node_id: str):
        """Unsubscribe from a variable"""
        if node_id in self.monitored_nodes:
            try:
                handle = self.monitored_nodes[node_id]['handle']
                await self.subscription.unsubscribe(handle)
                del self.monitored_nodes[node_id]
                
                logger.info(f"Unsubscribed from variable: {node_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {node_id}: {e}")
                return False
        
        return False
    
    async def read_variable(self, node_id: str):
        """Read a single variable value"""
        if not self.connected:
            logger.error("Not connected to OPC UA server")
            return None
        
        try:
            node = self.client.get_node(node_id)
            value = await node.read_value()
            return value
            
        except Exception as e:
            logger.error(f"Failed to read variable {node_id}: {e}")
            return None
    
    async def setup_monitored_variables(self):
        """Subscribe to all configured monitored variables from database"""
        monitored_vars = db_service.get_monitored_variables(enabled_only=True)
        
        for var in monitored_vars:
            await self.subscribe_to_variable(var['node_id'])
        
        logger.info(f"Subscribed to {len(monitored_vars)} monitored variables")
    
    async def run(self):
        """Main run loop with reconnection logic - only if endpoint is configured"""
        self.running = True
        
        # Only auto-connect if endpoint is properly configured
        if not Config.OPCUA_CLIENT_ENDPOINT or Config.OPCUA_CLIENT_ENDPOINT.strip() == '':
            logger.info("OPC UA Client endpoint not configured - waiting for manual configuration")
            while self.running and (not Config.OPCUA_CLIENT_ENDPOINT or Config.OPCUA_CLIENT_ENDPOINT.strip() == ''):
                await asyncio.sleep(5)
            if not self.running:
                return
        
        reconnect_delay = 5
        max_reconnect_delay = 60
        
        while self.running:
            try:
                if not self.connected:
                    logger.info("Attempting to connect to OPC UA server...")
                    if await self.connect():
                        # Setup monitored variables after connection
                        await self.setup_monitored_variables()
                        reconnect_delay = 5  # Reset delay on successful connection
                    else:
                        # Connection failed - apply backoff
                        logger.info(f"Connection failed. Retrying in {reconnect_delay} seconds...")
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        continue
                
                # Keep connection alive - check every 5 seconds instead of 1
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in OPC UA client run loop: {e}")
                self.connected = False
                
                # Exponential backoff for reconnection
                logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        
        await self.disconnect()
        logger.info("OPC UA Client stopped")
    
    async def stop(self):
        """Stop the client"""
        self.running = False


# Global client instance
opcua_client = OPCUAClientService()
