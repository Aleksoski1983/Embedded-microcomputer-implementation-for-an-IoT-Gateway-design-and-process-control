# MQTT Quick Start Guide

## Quick Configuration Steps

### 1. Setup Mosquitto Broker (One-time)

**Windows:**
```powershell
# Install via Chocolatey
choco install mosquitto

# Or download from https://mosquitto.org/download/
```

**Linux/Raspberry Pi:**
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

**Docker:**
```bash
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto
```

### 2. Configure Pico W Sensor

#### Step A: Provision WiFi (setup/AP mode)

1. Hold GPIO22 to GND for ~3 seconds during boot
2. Connect to WiFi: `picow_config`
3. Open browser: `http://192.168.0.1/`
4. Enter SSID/password → **Save & Restart**

#### Step B: Configure MQTT (run mode)

1. Open the dashboard: `http://<device-ip>/`
2. Set:
  - Enable MQTT
  - MQTT Broker IP (example: `192.168.1.100`)
  - MQTT Topic (example: `sensor/picow`)
3. Click **Save MQTT Settings**
4. Device reboots and applies MQTT settings

### 3. Subscribe to Data

```bash
# On the machine running Mosquitto
mosquitto_sub -h localhost -t "sensor/picow"

# Or specify broker IP
mosquitto_sub -h 192.168.1.100 -t "sensor/picow"
```

You should see JSON messages every 5 seconds:
```json
{"temperature":25.5,"humidity":60.2}
```

## Status Check

### Web Interface
- Navigate to: `http://<pico-ip>/`
- Check MQTT status (Disabled/Connected/Disconnected)

### Serial Console
- Connect USB cable
- Open serial monitor (115200 baud)
- Look for:
  ```
  MQTT connected to broker
  Publishing to sensor/picow: {"temperature":25.5,"humidity":60.2}
  ```

## Common Issues

| Problem | Solution |
|---------|----------|
| "MQTT not connected" | Check broker IP is correct and reachable |
| No messages received | Verify topic name matches, check broker is running |
| Connection drops | Check network stability, broker capacity |
| "MQTT disabled" | Enable MQTT checkbox in configuration |

## Example: Python Consumer

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    temp = data['temperature']
    hum = data['humidity']
    print(f"Temp: {temp}°C, Humidity: {hum}%")

client = mqtt.Client()
client.on_message = on_message
client.connect("192.168.1.100", 1883, 60)
client.subscribe("sensor/picow")
client.loop_forever()
```

Install paho-mqtt:
```bash
pip install paho-mqtt
```

## Configuration URLs

- **Setup Mode (AP)**: `http://192.168.0.1/` (hold GPIO22 to GND)
- **Run Mode Dashboard**: `http://<device-ip>/`
- **Run Mode JSON API**: `http://<device-ip>:8080/api/*`

## Default Values

| Setting | Value |
|---------|-------|
| MQTT Port | 1883 |
| Client ID | picow_sensor |
| QoS | 0 |
| Keepalive | 60 seconds |
| Publish Interval | 5 seconds |

## Need More Help?

- See `MQTT_GUIDE.md` for detailed documentation
- See `MQTT_IMPLEMENTATION.md` for technical details
- Check serial console for error messages
- Verify broker with: `mosquitto_sub -v -t "#"`
