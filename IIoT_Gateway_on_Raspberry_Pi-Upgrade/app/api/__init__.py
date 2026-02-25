"""
API Blueprint Registration
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api import opcua_routes, mqtt_routes, data_routes
