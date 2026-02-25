"""
Main web routes for Flask application
"""

from flask import Blueprint, render_template, jsonify
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@main_bp.route('/variables')
def variables():
    """Variable browser page"""
    return render_template('variables.html')

@main_bp.route('/configuration')
def configuration():
    """Configuration page"""
    return render_template('configuration.html')

@main_bp.route('/logs')
def logs():
    """Logs viewer page"""
    return render_template('logs.html')

@main_bp.route('/mqtt-monitor')
def mqtt_monitor():
    """MQTT message monitor page"""
    return render_template('mqtt_monitor.html')

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'IIoT Gateway'
    })
