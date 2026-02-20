"""
Fix MQTT Broker Status in Database
Updates the MQTT broker device status to match the current configuration
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.database_service import db_service
from app.config import Config

def fix_mqtt_broker_status():
    """Update MQTT broker device status with correct IP"""
    
    # Initialize database connection
    print("Initializing database connection...")
    db_service.init_postgresql()
    print("✓ Database connected")
    print()
    
    # Get current configuration
    mqtt_broker = Config.MQTT_BROKER
    mqtt_port = Config.MQTT_PORT
    connection_string = f"{mqtt_broker}:{mqtt_port}"
    
    print(f"Current MQTT configuration from .env:")
    print(f"  MQTT_BROKER: {mqtt_broker}")
    print(f"  MQTT_PORT: {mqtt_port}")
    print(f"  Connection String: {connection_string}")
    print()
    
    # Get current devices from database
    print("Current devices in database:")
    devices = db_service.get_devices()
    for device in devices:
        print(f"  {device['device_type']}: {device['name']} - {device['connection_string']} ({device['status']})")
    print()
    
    # Update MQTT broker device status
    print(f"Updating MQTT broker device status to: {connection_string}")
    db_service.update_device_status(
        device_type='mqtt',
        name='Mosquitto Broker',
        connection_string=connection_string,
        status='disconnected'  # Will be updated to 'connected' when MQTT connects
    )
    
    print("✓ Device status updated successfully!")
    print()
    print("Updated devices in database:")
    devices = db_service.get_devices()
    for device in devices:
        print(f"  {device['device_type']}: {device['name']} - {device['connection_string']} ({device['status']})")

if __name__ == '__main__':
    try:
        fix_mqtt_broker_status()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
