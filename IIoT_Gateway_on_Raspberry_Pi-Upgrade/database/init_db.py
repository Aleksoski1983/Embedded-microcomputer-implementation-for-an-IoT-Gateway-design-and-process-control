"""
Database Initialization Script
Run this to create the SQLite database schema
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.database_service import db_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database"""
    logger.info("Initializing database...")
    db_service.init_sqlite()
    logger.info("Database initialized successfully")
    
    # Add default MQTT mapping for Pico temperature
    try:
        mapping_id = db_service.add_mqtt_mapping(
            mqtt_topic='pico/temperature',
            opcua_node_id='ns=2;s=MQTT.Pico.Temperature',
            opcua_browse_name='PicoTemperature',
            data_type='Double',
            unit='°C',
            measurement_name='temperature'
        )
        if mapping_id > 0:
            logger.info(f"Added default MQTT mapping (ID: {mapping_id})")
    except Exception as e:
        logger.warning(f"Could not add default mapping: {e}")

if __name__ == '__main__':
    main()
