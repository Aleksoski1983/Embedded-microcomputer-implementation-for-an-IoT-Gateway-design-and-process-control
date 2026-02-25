"""
OPC UA Manager
Manages both OPC UA server and client in a single asyncio event loop
"""

import asyncio
import logging
from app.services.opcua_server_service import opcua_server
from app.services.opcua_client_service import opcua_client
from app.services.mqtt_service import mqtt_service

logger = logging.getLogger(__name__)

class OPCUAManager:
    """Manages OPC UA server and client lifecycle"""
    
    def __init__(self):
        self.loop = None
        self.running = False
    
    async def restart_server(self):
        """Restart OPC UA server with new configuration"""
        try:
            logger.info("Restarting OPC UA server...")
            
            # Stop the server
            await opcua_server.stop()
            
            # Reinitialize with new config
            opcua_server.__init__()
            
            # Start the server in background
            asyncio.create_task(opcua_server.start())
            
            logger.info("OPC UA server restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting OPC UA server: {e}", exc_info=True)
            return False

opcua_manager = OPCUAManager()

async def run_opcua_services():
    """Run OPC UA client only (server disabled)"""
    try:
        logger.info("Starting OPC UA Client service only (server disabled)")
        
        # Run only the OPC UA client
        opcua_client.run()
        
    except Exception as e:
        logger.error(f"Error in OPC UA services: {e}", exc_info=True)

def start_opcua_services():
    """Start OPC UA services (called from thread)"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run services
        loop.run_until_complete(run_opcua_services())
        
    except Exception as e:
        logger.error(f"Failed to start OPC UA services: {e}", exc_info=True)
    finally:
        loop.close()
