"""
Application Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'iiot_gateway')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'iiot_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    
    SQLITE_DB_PATH = 'database/iiot_gateway.db'
    
    # MQTT
    MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
    MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    MQTT_TOPIC_TEMPERATURE = os.getenv('MQTT_TOPIC_TEMPERATURE', 'pico/temperature')
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'iiot-gateway')
    
    # OPC UA Server
    OPCUA_SERVER_ENDPOINT = os.getenv('OPCUA_SERVER_ENDPOINT', 'opc.tcp://0.0.0.0:4840/iiot/gateway/')
    OPCUA_SERVER_NAME = os.getenv('OPCUA_SERVER_NAME', 'IIoT Gateway Server')
    OPCUA_SERVER_NAMESPACE = os.getenv('OPCUA_SERVER_NAMESPACE', 'http://gateway.local/mqtt')
    
    # OPC UA Client (S7-1500)
    OPCUA_CLIENT_ENDPOINT = os.getenv('OPCUA_CLIENT_ENDPOINT', 'opc.tcp://10.210.76.161:4840')
    OPCUA_CLIENT_TIMEOUT = int(os.getenv('OPCUA_CLIENT_TIMEOUT', 10))
    OPCUA_SUBSCRIPTION_INTERVAL = int(os.getenv('OPCUA_SUBSCRIPTION_INTERVAL', 1000))
    OPCUA_CLIENT_SECURITY_POLICY = os.getenv('OPCUA_CLIENT_SECURITY_POLICY', 'None')
    OPCUA_CLIENT_SECURITY_MODE = os.getenv('OPCUA_CLIENT_SECURITY_MODE', 'None')
    
    # Grafana
    GRAFANA_URL = os.getenv('GRAFANA_URL', 'http://localhost:3000')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/iiot-gateway.log')
