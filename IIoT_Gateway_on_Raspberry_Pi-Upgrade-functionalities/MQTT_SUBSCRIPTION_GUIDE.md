# MQTT Subscription & Bridging Guide

## Overview

The IIoT Gateway now supports dynamic MQTT topic subscription and broker-to-broker data bridging/forwarding. This allows you to:

1. **Subscribe dynamically** to any MQTT topic without pre-configuration
2. **Forward/bridge messages** between different topics
3. **Transform data** as it flows through the gateway
4. **Exchange data** between different MQTT brokers

## Features

### 1. Dynamic Topic Subscription

Subscribe to MQTT topics on-the-fly with support for wildcards:

**API Endpoint:** `POST /api/mqtt/subscribe`

**Example:**
```json
{
  "topic": "sensor/+/temperature",
  "qos": 1
}
```

**Wildcard Support:**
- `+` - Single level wildcard (e.g., `sensor/+/temp` matches `sensor/device1/temp`, `sensor/device2/temp`)
- `#` - Multi-level wildcard (e.g., `sensor/#` matches all topics under `sensor/`)

**Web UI:** Go to Configuration → MQTT Topic Subscriptions

### 2. Message Bridging/Forwarding

Forward messages from one topic to another, optionally transforming the data:

**API Endpoint:** `POST /api/mqtt/bridge`

**Basic Example:**
```json
{
  "source_topic": "device/sensor1/temp",
  "target_topic": "processed/temperature"
}
```

**With JSON Extraction:**
```json
{
  "source_topic": "device/+/data",
  "target_topic": "processed/values",
  "transform": "json_extract",
  "field": "temperature"
}
```

**With Multiplication:**
```json
{
  "source_topic": "sensor/celsius",
  "target_topic": "sensor/fahrenheit",
  "transform": "multiply",
  "factor": 1.8
}
```

**With Prefix:**
```json
{
  "source_topic": "raw/data",
  "target_topic": "tagged/data",
  "transform": "prefix",
  "prefix": "DEVICE_01:"
}
```

### 3. Broker-to-Broker Exchange

You can use the bridging feature to exchange data between different MQTT brokers:

1. Subscribe to topics from Broker A
2. Create bridge rules to forward to topics that will be published back to Broker A or to Broker B (if you have multiple connections)

**Example Use Cases:**
- Aggregate data from multiple sources
- Route sensor data to different processing pipelines
- Implement data filtering and transformation
- Create topic hierarchies and organization

## API Reference

### Subscribe to Topic

```http
POST /api/mqtt/subscribe
Content-Type: application/json

{
  "topic": "sensor/temperature",
  "qos": 1  // 0, 1, or 2
}
```

**Response:**
```json
{
  "success": true,
  "topic": "sensor/temperature",
  "qos": 1,
  "message": "Subscribed to topic: sensor/temperature"
}
```

### Unsubscribe from Topic

```http
POST /api/mqtt/unsubscribe
Content-Type: application/json

{
  "topic": "sensor/temperature"
}
```

### List Subscriptions

```http
GET /api/mqtt/subscriptions
```

**Response:**
```json
{
  "success": true,
  "subscriptions": [
    "sensor/+/temperature",
    "device/#",
    "pico/temperature"
  ],
  "count": 3
}
```

### Add Bridge Rule

```http
POST /api/mqtt/bridge
Content-Type: application/json

{
  "source_topic": "raw/sensor1",
  "target_topic": "processed/sensor1",
  "transform": "json_extract",
  "field": "value"
}
```

**Response:**
```json
{
  "success": true,
  "rule_id": 1,
  "source_topic": "raw/sensor1",
  "target_topic": "processed/sensor1",
  "message": "Bridge rule added: raw/sensor1 → processed/sensor1"
}
```

### Remove Bridge Rule

```http
DELETE /api/mqtt/bridge/1
```

### List Bridge Rules

```http
GET /api/mqtt/bridge
```

**Response:**
```json
{
  "success": true,
  "rules": [
    {
      "id": 1,
      "source_topic": "raw/sensor1",
      "target_topic": "processed/sensor1",
      "message_count": 42,
      "last_message": "2025-12-18T10:30:00"
    }
  ],
  "count": 1
}
```

## Usage Examples

### Example 1: Monitor All Sensors

```bash
# Subscribe to all sensor topics
curl -X POST http://localhost:5001/api/mqtt/subscribe \
  -H "Content-Type: application/json" \
  -d '{"topic": "sensor/#", "qos": 1}'
```

### Example 2: Temperature Conversion Pipeline

```bash
# Convert Celsius to Fahrenheit
curl -X POST http://localhost:5001/api/mqtt/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "source_topic": "temp/celsius",
    "target_topic": "temp/fahrenheit",
    "transform": "multiply",
    "factor": 1.8
  }'
```

### Example 3: Extract JSON Field

If your MQTT messages are JSON like:
```json
{"sensor_id": "temp001", "value": 23.5, "unit": "C"}
```

You can extract just the value:
```bash
curl -X POST http://localhost:5001/api/mqtt/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "source_topic": "devices/+/data",
    "target_topic": "values/temperature",
    "transform": "json_extract",
    "field": "value"
  }'
```

### Example 4: Tag Messages with Source

```bash
curl -X POST http://localhost:5001/api/mqtt/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "source_topic": "raw/data",
    "target_topic": "tagged/data",
    "transform": "prefix",
    "prefix": "[GATEWAY-01] "
  }'
```

## Python Client Example

```python
import requests
import json

BASE_URL = "http://localhost:5001/api"

# Subscribe to topic
response = requests.post(
    f"{BASE_URL}/mqtt/subscribe",
    json={"topic": "sensor/+/temp", "qos": 1}
)
print(response.json())

# Add bridge rule
response = requests.post(
    f"{BASE_URL}/mqtt/bridge",
    json={
        "source_topic": "raw/temp",
        "target_topic": "processed/temp",
        "transform": "multiply",
        "factor": 1.8
    }
)
print(response.json())

# List all subscriptions
response = requests.get(f"{BASE_URL}/mqtt/subscriptions")
print(response.json())

# List all bridge rules
response = requests.get(f"{BASE_URL}/mqtt/bridge")
print(response.json())
```

## Web Interface

Access the configuration page at: `http://localhost:5001/configuration`

You'll find:

1. **MQTT Topic Subscriptions** section
   - Enter topic pattern
   - Select QoS level
   - Click Subscribe
   - View and manage active subscriptions

2. **MQTT Topic Bridging** section
   - Enter source and target topics
   - Select optional transformation
   - Add bridge rules
   - Monitor message counts and activity

## Notes

- Subscriptions persist until explicitly removed or the service restarts
- Bridge rules are processed in order
- Wildcard subscriptions work with standard MQTT patterns
- All operations require an active MQTT connection
- Transform functions are applied before publishing to target topic
- You can chain multiple bridge rules for complex pipelines

## Troubleshooting

**Subscription not working:**
- Check MQTT broker connection status
- Verify topic pattern is correct
- Check broker permissions

**Bridge not forwarding:**
- Ensure source topic is subscribed
- Check transform parameters
- Verify target topic is valid
- Look for errors in logs

**Performance:**
- Minimize wildcard subscriptions for high-throughput scenarios
- Use appropriate QoS levels (0 for high-speed, 1 for reliability)
- Monitor bridge rule message counts
