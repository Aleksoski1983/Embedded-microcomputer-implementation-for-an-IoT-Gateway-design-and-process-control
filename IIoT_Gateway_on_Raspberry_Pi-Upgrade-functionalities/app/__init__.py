"""
Flask Application Factory
"""

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio = SocketIO()

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    from app.config import Config
    app.config.from_object(Config)
    
    # Initialize extensions
    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register main routes
    from app import routes
    app.register_blueprint(routes.main_bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'path': request.path}), 404
        return error
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            logger.error(f"Internal server error on {request.path}: {error}", exc_info=True)
            return jsonify({'error': 'Internal server error', 'details': str(error)}), 500
        return error
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        if request.path.startswith('/api/'):
            logger.error(f"Unhandled exception on {request.path}: {error}", exc_info=True)
            return jsonify({'error': 'An unexpected error occurred', 'details': str(error)}), 500
        raise error
    
    logger.info("Flask application created successfully")
    
    return app

def init_services(app):
    """Initialize background services"""
    import os
    import threading
    from app.services import database_service
    from app.services import mqtt_service
    from app.services import opcua_manager
    
    logger.info("Initializing services...")
    logger.info(f"Debug mode: {app.debug}, WERKZEUG_RUN_MAIN: {os.environ.get('WERKZEUG_RUN_MAIN')}")
    
    # Initialize database
    database_service.init_database()
    
    # Only start MQTT and OPC UA services in the main process (not in Flask reloader)
    # Check if we're in the main process or the reloader subprocess
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        # Start MQTT service (now runs in background via loop_start)
        mqtt_service.mqtt_service.start()
        logger.info("MQTT service started")
        
        # Start OPC UA services in separate thread
        opcua_thread = threading.Thread(target=opcua_manager.start_opcua_services, daemon=True)
        opcua_thread.start()
        logger.info("OPC UA services started")
    else:
        logger.info("Skipping service initialization in Flask reloader parent process")
    
    logger.info("All services initialized successfully")
