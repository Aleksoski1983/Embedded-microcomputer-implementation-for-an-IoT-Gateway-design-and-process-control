"""
OPC UA Server Service - DISABLED
OPC UA Server functionality disabled to focus on client connectivity to S7-1500
"""

import logging
# import asyncio
# from asyncua import Server, ua  
# from asyncua.common.methods import uamethod
from datetime import datetime
from typing import Dict, Optional
from app.config import Config

logger = logging.getLogger(__name__)

class OPCUAServerService:
    """OPC UA Server - DISABLED to focus on client functionality"""
    
    def __init__(self):
        self.server = None
        self.namespace_idx = None
        self.mqtt_folder = None
        self.variables: Dict[str, any] = {}
        self.running = False
        logger.info("OPC UA Server service initialized (disabled - focusing on client connectivity)")
        
    async def init_server(self):
        """Server initialization disabled"""
        logger.info("OPC UA Server disabled - focusing on client connectivity to S7-1500")
        return True
            
            # Set endpoint
            self.server.set_endpoint(Config.OPCUA_SERVER_ENDPOINT)
            self.server.set_server_name(Config.OPCUA_SERVER_NAME)
            
            # Setup security (optional - can be enhanced)
            self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
            
            # Register namespace
            self.namespace_idx = await self.server.register_namespace(Config.OPCUA_SERVER_NAMESPACE)
            
            # Create address space structure
            await self._create_address_space()
            
            logger.info(f"OPC UA Server initialized at {Config.OPCUA_SERVER_ENDPOINT}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OPC UA server: {e}", exc_info=True)
            raise
    
    async def _create_address_space(self):
        """Create the OPC UA address space structure"""
        # Get Objects node
        objects = self.server.nodes.objects
        
        # Create main MQTT Devices folder
        self.mqtt_folder = await objects.add_folder(self.namespace_idx, "MQTT_Devices")
        
        # Create Pico Sensors folder
        pico_folder = await self.mqtt_folder.add_folder(self.namespace_idx, "PicoSensors")
        
        # Create default Pico001 device
        await self._create_pico_device(pico_folder, "pico001")
        
        logger.info("OPC UA address space created")
    
    async def _create_pico_device(self, parent_folder, device_name: str):
        """Create a Pico device with temperature variable"""
        # Create device object
        device_obj = await parent_folder.add_object(self.namespace_idx, device_name)
        
        # Create Temperature variable
        temp_var = await device_obj.add_variable(
            self.namespace_idx,
            "Temperature",
            0.0,
            varianttype=ua.VariantType.Double
        )
        await temp_var.set_writable()
        await temp_var.set_attr_bit(ua.AttributeIds.Value, ua.AccessLevel.CurrentRead | ua.AccessLevel.CurrentWrite)
        
        # Set description
        await temp_var.write_attribute(
            ua.AttributeIds.Description,
            ua.DataValue(ua.LocalizedText("Temperature from Raspberry Pi Pico in °C"))
        )
        
        # Create Timestamp variable
        timestamp_var = await device_obj.add_variable(
            self.namespace_idx,
            "Timestamp",
            datetime.now(),
            varianttype=ua.VariantType.DateTime
        )
        await timestamp_var.set_writable()
        
        # Create Status variable
        status_var = await device_obj.add_variable(
            self.namespace_idx,
            "Status",
            "offline",
            varianttype=ua.VariantType.String
        )
        await status_var.set_writable()
        
        # Store variable references
        self.variables[f"{device_name}_temperature"] = temp_var
        self.variables[f"{device_name}_timestamp"] = timestamp_var
        self.variables[f"{device_name}_status"] = status_var
        
        logger.info(f"Created Pico device: {device_name}")
    
    async def create_mqtt_variable(self, topic: str, browse_name: str, data_type: str = 'Double',
                                  initial_value = 0.0, unit: str = None):
        """Dynamically create a new OPC UA variable for MQTT topic"""
        try:
            # Determine variant type
            variant_type = ua.VariantType.Double
            if data_type == 'String':
                variant_type = ua.VariantType.String
            elif data_type == 'Int':
                variant_type = ua.VariantType.Int32
            elif data_type == 'Boolean':
                variant_type = ua.VariantType.Boolean
            
            # Create variable under MQTT folder
            var = await self.mqtt_folder.add_variable(
                self.namespace_idx,
                browse_name,
                initial_value,
                varianttype=variant_type
            )
            await var.set_writable()
            
            # Set description with unit if provided
            description = f"MQTT Topic: {topic}"
            if unit:
                description += f" (Unit: {unit})"
            
            await var.write_attribute(
                ua.AttributeIds.Description,
                ua.DataValue(ua.LocalizedText(description))
            )
            
            # Store reference
            var_key = f"mqtt_{topic.replace('/', '_')}"
            self.variables[var_key] = var
            
            logger.info(f"Created OPC UA variable '{browse_name}' for MQTT topic '{topic}'")
            return var
            
        except Exception as e:
            logger.error(f"Failed to create MQTT variable: {e}")
            return None
    
    async def update_variable(self, variable_key: str, value, timestamp: datetime = None):
        """Update an OPC UA variable value"""
        try:
            if variable_key in self.variables:
                var = self.variables[variable_key]
                await var.write_value(value)
                
                # Update timestamp if available
                timestamp_key = variable_key.replace('_temperature', '_timestamp')
                if timestamp and timestamp_key in self.variables:
                    await self.variables[timestamp_key].write_value(timestamp)
                
                logger.debug(f"Updated variable {variable_key} = {value}")
                return True
            else:
                logger.warning(f"Variable {variable_key} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update variable {variable_key}: {e}")
            return False
    
    async def update_pico_temperature(self, device_name: str, temperature: float, 
                                     timestamp: datetime = None):
        """Update Pico temperature value"""
        var_key = f"{device_name}_temperature"
        success = await self.update_variable(var_key, temperature, timestamp)
        
        if success:
            # Update status to online
            status_key = f"{device_name}_status"
            await self.update_variable(status_key, "online")
        
        return success
    
    async def start(self):
        """Start the OPC UA server"""
        try:
            await self.init_server()
            
            async with self.server:
                self.running = True
                logger.info("OPC UA Server started successfully")
                
                # Keep server running
                while self.running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"OPC UA Server error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("OPC UA Server stopped")
    
    async def stop(self):
        """Stop the OPC UA server"""
        self.running = False
        if self.server:
            await self.server.stop()
            logger.info("OPC UA Server stop requested")


# Global server instance
opcua_server = OPCUAServerService()
