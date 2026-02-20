#!/usr/bin/env python3
"""
Test script for new MQTT subscription and bridging features
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001/api"

def test_mqtt_subscription():
    """Test dynamic topic subscription"""
    print("\n=== Testing MQTT Topic Subscription ===")
    
    # Subscribe to a topic
    response = requests.post(
        f"{BASE_URL}/mqtt/subscribe",
        json={"topic": "test/sensor/#", "qos": 1}
    )
    print(f"Subscribe response: {response.json()}")
    
    # List subscriptions
    response = requests.get(f"{BASE_URL}/mqtt/subscriptions")
    print(f"Active subscriptions: {response.json()}")
    
    return response.json().get('success', False)

def test_mqtt_bridge():
    """Test MQTT message bridging"""
    print("\n=== Testing MQTT Message Bridging ===")
    
    # Add a simple bridge rule
    response = requests.post(
        f"{BASE_URL}/mqtt/bridge",
        json={
            "source_topic": "raw/temperature",
            "target_topic": "processed/temperature"
        }
    )
    print(f"Add bridge rule: {response.json()}")
    
    # Add a bridge with transformation
    response = requests.post(
        f"{BASE_URL}/mqtt/bridge",
        json={
            "source_topic": "sensor/data",
            "target_topic": "transformed/data",
            "transform": "json_extract",
            "field": "value"
        }
    )
    print(f"Add bridge with transform: {response.json()}")
    
    # List bridge rules
    response = requests.get(f"{BASE_URL}/mqtt/bridge")
    print(f"Active bridge rules: {response.json()}")
    
    return response.json().get('success', False)

def test_mqtt_publish():
    """Test publishing to MQTT"""
    print("\n=== Testing MQTT Publishing ===")
    
    # Publish a simple message
    response = requests.post(
        f"{BASE_URL}/mqtt/publish",
        json={
            "topic": "test/temperature",
            "payload": "23.5",
            "qos": 1
        }
    )
    print(f"Publish response: {response.json()}")
    
    # Publish JSON data
    response = requests.post(
        f"{BASE_URL}/mqtt/publish",
        json={
            "topic": "sensor/data",
            "payload": json.dumps({"sensor_id": "temp001", "value": 24.3, "unit": "C"}),
            "qos": 1
        }
    )
    print(f"Publish JSON: {response.json()}")
    
    return response.json().get('success', False)

def test_mqtt_status():
    """Check MQTT connection status"""
    print("\n=== Checking MQTT Status ===")
    
    response = requests.get(f"{BASE_URL}/mqtt/status")
    print(f"MQTT Status: {response.json()}")
    
    return response.json().get('connected', False)

def cleanup_test_data():
    """Clean up test subscriptions and bridge rules"""
    print("\n=== Cleaning Up Test Data ===")
    
    # Get bridge rules
    response = requests.get(f"{BASE_URL}/mqtt/bridge")
    if response.json().get('success'):
        rules = response.json().get('rules', [])
        for rule in rules:
            print(f"Removing bridge rule {rule['id']}...")
            requests.delete(f"{BASE_URL}/mqtt/bridge/{rule['id']}")
    
    # Unsubscribe from test topic
    requests.post(
        f"{BASE_URL}/mqtt/unsubscribe",
        json={"topic": "test/sensor/#"}
    )
    print("Cleanup complete")

def main():
    """Run all tests"""
    print("=" * 60)
    print("MQTT Subscription & Bridging Feature Tests")
    print("=" * 60)
    
    try:
        # Check MQTT status first
        if not test_mqtt_status():
            print("\n⚠️  MQTT is not connected. Make sure the broker is running.")
            return
        
        # Run tests
        test_mqtt_subscription()
        time.sleep(1)
        
        test_mqtt_bridge()
        time.sleep(1)
        
        test_mqtt_publish()
        time.sleep(2)  # Wait for messages to flow through bridge
        
        # Show final status
        print("\n=== Final Status ===")
        response = requests.get(f"{BASE_URL}/mqtt/bridge")
        if response.json().get('success'):
            rules = response.json().get('rules', [])
            for rule in rules:
                print(f"Bridge: {rule['source_topic']} → {rule['target_topic']}")
                print(f"  Messages: {rule['message_count']}, Last: {rule['last_message']}")
        
        # Cleanup
        cleanup_test_data()
        
        print("\n✓ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
