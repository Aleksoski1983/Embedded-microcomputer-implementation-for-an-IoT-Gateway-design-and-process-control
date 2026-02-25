"""
OPC UA Server Service - SIMPLIFIED/DISABLED
OPC UA Server functionality disabled to focus on client connectivity to S7-1500
"""

import logging
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
        
    async def start_server(self):
        """Start server - disabled"""
        logger.info("OPC UA Server start disabled")
        self.running = True
        return True
        
    async def stop_server(self):
        """Stop server - disabled"""
        logger.info("OPC UA Server stop disabled")
        self.running = False
        return True
        
    def update_variable(self, topic: str, value: any):
        """Update variable - disabled"""
        logger.debug(f"OPC UA Server update disabled for {topic}: {value}")
        pass
    
    async def create_mqtt_variable(self, topic: str, browse_name: str, data_type: str = 'Double', 
                                   initial_value: any = 0.0, unit: str = None):
        """Create MQTT variable - disabled but returns success for compatibility"""
        logger.debug(f"OPC UA Server create_mqtt_variable disabled for {browse_name}")
        return {
            'node_id': f"ns=2;s=MQTT.{browse_name}",
            'browse_name': browse_name,
            'data_type': data_type,
            'unit': unit
        }
        
    def get_status(self):
        """Get server status"""
        return {
            'running': False,
            'endpoint': 'disabled',
            'variables_count': 0,
            'status': 'disabled'
        }

# Create global instance
opcua_server = OPCUAServerService()