"""Check current configuration values"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("ENVIRONMENT VARIABLES FROM .env FILE:")
print("=" * 60)
print(f"MQTT_BROKER from os.getenv: {os.getenv('MQTT_BROKER')}")
print(f"MQTT_PORT from os.getenv: {os.getenv('MQTT_PORT')}")
print()

# Import Config class
from app.config import Config

print("=" * 60)
print("CONFIG CLASS VALUES:")
print("=" * 60)
print(f"Config.MQTT_BROKER: {Config.MQTT_BROKER}")
print(f"Config.MQTT_PORT: {Config.MQTT_PORT}")
print(f"Config.MQTT_USERNAME: {Config.MQTT_USERNAME}")
print(f"Config.MQTT_PASSWORD: {Config.MQTT_PASSWORD}")
print()

print("=" * 60)
print("EXPECTED VALUES:")
print("=" * 60)
print(f"Should be: 192.168.100.52:1883")
print("=" * 60)
