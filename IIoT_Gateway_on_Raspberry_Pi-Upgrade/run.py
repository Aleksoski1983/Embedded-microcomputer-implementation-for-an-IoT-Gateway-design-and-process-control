#!/usr/bin/env python3
"""
IIoT Gateway Application Entry Point
Raspberry Pi 5 - MQTT to OPC UA Bridge with S7-1500 Integration
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
log_file = os.getenv('LOG_FILE', 'logs/iiot-gateway.log')

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging handlers with UTF-8 encoding to support Unicode characters
file_handler = logging.FileHandler(log_file, encoding='utf-8')
stream_handler = logging.StreamHandler(sys.stdout)

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    try:
        # Reconfigure stdout to use UTF-8 encoding
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')
    except Exception as e:
        # Fallback: if reconfiguration fails, just continue
        pass

# Set formatter for both handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logging.basicConfig(
    level=getattr(logging, log_level),
    handlers=[file_handler, stream_handler]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        from app import create_app, init_services
        
        logger.info("Starting IIoT Gateway Application...")
        
        # Create Flask application
        app = create_app()
        
        # Initialize background services (MQTT, OPC UA)
        init_services(app)
        
        # Get configuration
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', 5001))
        debug = False  # Disable debug mode to avoid Flask reloader issues with MQTT
        
        logger.info(f"Starting Flask server on {host}:{port}")
        
        # Run the application
        from app import socketio
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
