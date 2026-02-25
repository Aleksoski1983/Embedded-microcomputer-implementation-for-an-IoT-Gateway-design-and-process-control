# MQTT Integration Guide

This document describes the MQTT functionality added to the Pico W WiFi Sensor project.

## Overview

The Pico W sensor publishes temperature and humidity readings to an MQTT broker (tested with Mosquitto). MQTT is configurable at runtime from the web dashboard and persisted in flash.

## Features

- **MQTT Client**: Connects to Mosquitto broker using lwIP MQTT library
- **Web Configuration**: Configure MQTT broker IP/topic via the run-mode dashboard
- **Automatic Publishing**: Sensor data is automatically published to the configured topic every 5 seconds
- **JSON Format**: Data is published in JSON format: `{"temperature":25.5,"humidity":60.2}`
- **Status Monitoring**: View MQTT connection status on the dashboard
- **Flash Storage**: MQTT configuration is saved to flash memory

## Configuration

### Web Configuration

#### 1) Provision WiFi (setup/AP mode)

WiFi credentials are configured only in setup mode:

1. Hold GPIO22 to GND for ~3 seconds during boot
2. Connect to the AP `picow_config`
3. Open `http://192.168.0.1/`
4. Enter SSID/password → save → device reboots into run mode

#### 2) Configure MQTT (run mode)

MQTT settings are configured in run mode from the dashboard:

1. Open `http://<device-ip>/`
2. Set:
  - Enable MQTT
  - Broker IP
  - Topic
3. Save → device writes flash and reboots to apply changes

Tip: the dashboard uses a JSON API on port 8080; MQTT config can also be managed via `GET/POST http://<device-ip>:8080/api/config`.

### MQTT Broker Setup

To receive data, you need a Mosquitto broker running. Here's how to set it up:

#### On Linux/Raspberry Pi:
```bash
# Install Mosquitto
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start Mosquitto service
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Subscribe to topic (test)
mosquitto_sub -h localhost -t "sensor/picow"
```

#### On Windows:
```powershell
# Download and install from: https://mosquitto.org/download/
# Or use Chocolatey:
choco install mosquitto

# Subscribe to topic
mosquitto_sub -h localhost -t "sensor/picow"
```

#### Using Docker:
```bash
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto
docker exec -it mosquitto mosquitto_sub -t "sensor/picow"
```

## Message Format

The sensor publishes data in JSON format:

```json
{
  "temperature": 25.5,
  "humidity": 60.2
}
```

## Monitoring

### Web Dashboard

- Navigate to `http://<device-ip>/`
- The Status card shows MQTT state (Disabled/Connected/Disconnected)

### Serial Console
The device prints MQTT status to the serial console:
```
MQTT client initialized
Connecting to MQTT broker at 192.168.1.100:1883
MQTT topic: sensor/picow
MQTT connected to broker
Publishing to sensor/picow: {"temperature":25.5,"humidity":60.2}
MQTT message published successfully
```

## Integration Examples

### Node-RED
```json
[
    {
        "id": "mqtt_in",
        "type": "mqtt in",
        "topic": "sensor/picow",
        "broker": "localhost",
        "name": "Pico Sensor"
    },
    {
        "id": "json",
        "type": "json"
    },
    {
        "id": "dashboard",
        "type": "ui_chart",
        "name": "Temperature Chart"
    }
]
```

### Python Script
```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    print(f"Temperature: {data['temperature']}°C")
    print(f"Humidity: {data['humidity']}%")

client = mqtt.Client()
client.on_message = on_message
client.connect("192.168.1.100", 1883)
client.subscribe("sensor/picow")
client.loop_forever()
```

### Home Assistant
Add to `configuration.yaml`:
```yaml
mqtt:
  sensor:
    - name: "Pico Temperature"
      state_topic: "sensor/picow"
      value_template: "{{ value_json.temperature }}"
      unit_of_measurement: "°C"
      device_class: temperature
    
    - name: "Pico Humidity"
      state_topic: "sensor/picow"
      value_template: "{{ value_json.humidity }}"
      unit_of_measurement: "%"
      device_class: humidity
```

## Troubleshooting

### MQTT Not Connecting
1. **Check broker IP**: Ensure the broker IP is correct and reachable
2. **Verify broker is running**: Test with `mosquitto_sub`
3. **Check firewall**: Ensure port 1883 is open
4. **View serial console**: Check for error messages

### No Data Publishing
1. **Verify MQTT is enabled**: Check settings page
2. **Check connection status**: Should show "Connected"
3. **Verify topic**: Ensure topic name is correct
4. **Check sensor readings**: Ensure DHT22 is working

### Connection Drops
- MQTT keepalive is set to 60 seconds
- Check network stability
- Ensure broker is not overloaded
- Check broker logs for connection issues

## Technical Details

### Files Modified/Added
- `mqtt_client.h` / `mqtt_client.c` - MQTT client implementation
- `api_server.c` / `api_server.h` - JSON API (port 8080) for live data + MQTT config
- `wifi_setup/fs/index.html` / `wifi_setup/fs/app.js` - Run-mode dashboard UI
- `wifi_setup/fs/index.shtml` - Setup/AP portal (WiFi-only)
- `wifi_setup/fs/done.html` - Setup confirmation page
- `wifi_setup/http_server.c` - SSI/CGI for setup portal (WiFi credentials)
- `CMakeLists.txt` - Build integration

### Configuration Structure
```c
typedef struct _config {
    uint16_t magic;
    char ssid[33];
    char passwd[64];
    ip4_addr_t ip;
    ip4_addr_t mask;
    ip4_addr_t gw;
    ip4_addr_t mqtt_broker_ip;  // MQTT broker IP
    char mqtt_topic[65];         // MQTT topic
    uint8_t mqtt_enabled;        // MQTT enable flag
} config;
```

### MQTT Client Settings
- **Port**: 1883 (standard MQTT port)
- **Client ID**: "picow_sensor"
- **QoS**: 0 (fire and forget)
- **Retain**: false
- **Keepalive**: 60 seconds
- **Publish Interval**: 5 seconds (same as sensor reading interval)

## Future Enhancements

Possible future improvements:
- TLS/SSL support for secure MQTT (port 8883)
- Authentication (username/password)
- Configurable publish interval
- Multiple topics (separate for temperature/humidity)
- MQTT Last Will and Testament (LWT)
- Configurable QoS level
- MQTT subscriptions for remote control

## License

This MQTT integration maintains the same BSD-3-Clause license as the original project.

## Support

For issues or questions about MQTT functionality:
1. Check this guide first
2. Review serial console output
3. Test broker connectivity with mosquitto_sub
4. Verify network configuration
