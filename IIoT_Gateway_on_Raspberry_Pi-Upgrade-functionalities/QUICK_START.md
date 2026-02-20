# Quick Start Guide - IIoT Gateway

## Installation Steps (Raspberry Pi)

### 1. Clone or copy the project
```bash
cd ~
git clone <your-repo-url> iiot-gateway
cd iiot-gateway
```

### 2. Run installation script
```bash
chmod +x install.sh
./install.sh
```

### 3. Configure environment
```bash
nano .env
```

Update these key settings:
- `OPCUA_CLIENT_ENDPOINT` - Your S7-1500 PLC address
- `POSTGRES_PASSWORD` - Your PostgreSQL password
- `MQTT_USERNAME` and `MQTT_PASSWORD` - If using authentication

### 4. Configure Mosquitto MQTT Broker
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd admin
sudo cp config/mosquitto.conf /etc/mosquitto/mosquitto.conf
sudo systemctl restart mosquitto
```

### 5. Setup PostgreSQL
```bash
# Setup PostgreSQL database and user
sudo -u postgres psql

# Run these commands in PostgreSQL:
CREATE DATABASE iiot_gateway;
CREATE USER iiot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;
\q

# Initialize database tables
python database/init_db.py
```

### 6. Start the gateway
```bash
sudo systemctl start iiot-gateway
sudo systemctl status iiot-gateway
```

### 7. Access web interface
```
http://<raspberry-pi-ip>:5000
```

## Web Interface Overview

The gateway provides a modern, unified web interface with consistent styling across all pages:

### 📊 Dashboard (Main Page)
- **System Status Cards**: Real-time connection status for MQTT Broker, OPC UA Client, and Database
- **Statistics**: Monitored variables count, MQTT mappings, and device status
- **Connected Devices**: Table showing all connected devices and their status
- **Auto-Refresh**: Status updates every 5 seconds automatically

### 🔧 OPC-UA Variables
- **Browse Variables**: Navigate the OPC UA server's address space
- **Add Variables**: Select variables to monitor and store in database
- **Monitor Status**: View current values and connection states
- **Database Toggle**: Enable/disable database storage per variable
- **Real-Time Updates**: Live value updates from PLC

### 📡 MQTT Monitor
- **Live Messages**: Real-time MQTT message display
- **Topic Statistics**: Message counts per topic
- **Message Filtering**: Filter by topic pattern
- **Auto-Scroll**: Optional auto-scrolling for live monitoring
- **Payload Preview**: JSON formatting for structured data

### ⚙️ Configuration
- **MQTT Settings**: Configure broker connection (address, port, credentials)
- **OPC UA Client**: Configure S7-1500 PLC connection endpoint
- **Database Settings**: PostgreSQL connection configuration
- **Topic Subscriptions**: Dynamic MQTT topic subscription management
- **Message Bridging**: Forward and transform messages between topics
- **Topic Mappings**: Expose MQTT topics as OPC UA variables (optional)
- **Test Connections**: Built-in connection testing for all services

### 📋 Logs
- **Real-Time Logs**: Live application log viewer
- **Auto-Scroll**: Optional auto-scrolling
- **Refresh**: Manual log refresh
- **Monospace Display**: Terminal-style log formatting

### Navigation
All pages are accessible via the top navigation bar with consistent styling and visual indicators for the active page.

## Testing MQTT (from Raspberry Pi Pico)

### Pico MicroPython Code Example
```python
import network
import time
from umqtt.simple import MQTTClient
import machine

# WiFi configuration
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# MQTT configuration
MQTT_BROKER = "192.168.1.100"  # Raspberry Pi IP
MQTT_TOPIC = b"pico/temperature"

# Connect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while not wlan.isconnected():
    time.sleep(1)

print("Connected to WiFi:", wlan.ifconfig())

# Connect to MQTT
client = MQTTClient("pico001", MQTT_BROKER)
client.connect()

# Simulate temperature sensor
while True:
    temperature = 22.5 + (machine.RTC().datetime()[6] % 10) / 10
    payload = f'{{"temperature": {temperature}}}'
    client.publish(MQTT_TOPIC, payload)
    print(f"Published: {payload}")
    time.sleep(5)
```

## Testing OPC UA Connection

### From Web Interface
1. Go to http://<pi-ip>:5000 (navigate to "OPC-UA Variables" in the menu)
2. Click "🔍 Browse Variables" button
3. Navigate through S7-1500 PLC address space
4. Click "Add" on variables you want to monitor
5. Enable "💾 DB" toggle to store data in PostgreSQL

### Using Test Script
```bash
# Activate virtual environment
source venv/bin/activate

# Run simple connection test
python test_opcua_connection_simple.py

# Or detailed connection test
python test_opcua_connection.py
```

## Grafana Dashboard Setup

1. Access Grafana: http://<pi-ip>:3000
   - Username: admin
   - Password: admin (change on first login)

2. Add PostgreSQL Data Source:
   - Configuration → Data Sources → Add PostgreSQL
   - Host: localhost:5432
   - Database: iiot_gateway
   - User: iiot_user
   - Password: (from .env file)
   - SSL Mode: disable (for local connections)

3. Create Dashboard:
   - Create → Dashboard → Add Panel
   - Select PostgreSQL data source
   - SQL query example:
```sql
SELECT
  timestamp,
  value
FROM sensor_data
WHERE variable_name = 'temperature'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp ASC
```

## Troubleshooting

### Dashboard shows everything disconnected (red status)
**Symptoms**: Configuration page shows connections as working, but Dashboard shows red/disconnected.

**Solutions**:
1. **Clear browser cache**: Press Ctrl+Shift+Delete and clear cached images and files
2. **Check browser console**: Press F12 → Console tab to see any JavaScript errors
3. **Verify API endpoint**: 
   ```bash
   curl http://localhost:5000/api/system/info
   ```
   Should return JSON with connection states
4. **Check application logs**:
   ```bash
   tail -f logs/iiot-gateway.log
   ```
   Look for "system info" debug messages
5. **Restart application**:
   ```bash
   sudo systemctl restart iiot-gateway
   ```

### Unicode/Encoding Errors on Windows
**Symptoms**: Application crashes with `UnicodeEncodeError: 'charmap' codec can't encode character`

**Solution**: This has been fixed in v2.1.0. Update to latest version:
```bash
git pull
python run.py
```

The fix automatically configures UTF-8 encoding for Windows console.

### Gateway won't start
```bash
# Check logs
sudo journalctl -u iiot-gateway -f

# Check Python errors
source venv/bin/activate
python run.py
```

### MQTT not connecting
```bash
# Test Mosquitto
mosquitto_sub -h localhost -t "test" -v

# Check Mosquitto logs
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### OPC UA connection fails
- Check PLC IP address in .env
- Verify PLC OPC UA server is enabled
- Check firewall on PLC allows port 4840
- Verify network connectivity: `ping <plc-ip>`

### PostgreSQL errors
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Test database connection
psql -h localhost -U iiot_user -d iiot_gateway
```

## Useful Commands

```bash
# Service management
sudo systemctl start iiot-gateway
sudo systemctl stop iiot-gateway
sudo systemctl restart iiot-gateway
sudo systemctl status iiot-gateway

# View logs
sudo journalctl -u iiot-gateway -f

# Update application
cd ~/iiot-gateway
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart iiot-gateway
```

## API Endpoints

### OPC UA
- `GET /api/opcua/browse?node_id=i=85` - Browse OPC UA nodes
- `GET /api/opcua/variables/selected` - Get monitored variables
- `POST /api/opcua/variables/select` - Add variable to monitoring
- `GET /api/opcua/status` - Get OPC UA client status
- `POST /api/opcua/client/test` - Test OPC UA connection
- `POST /api/opcua/client/connect` - Connect OPC UA client
- `POST /api/opcua/client/disconnect` - Disconnect OPC UA client

### MQTT
- `GET /api/mqtt/topics` - Get MQTT mappings
- `POST /api/mqtt/expose` - Expose MQTT topic as OPC UA
- `POST /api/mqtt/test` - Test MQTT broker connection
- `POST /api/mqtt/connect` - Connect to MQTT broker
- `POST /api/mqtt/disconnect` - Disconnect from MQTT broker
- `POST /api/mqtt/configure` - Configure MQTT settings

### Database
- `GET /api/database/status` - Get database connection status
- `POST /api/database/test` - Test database connections
- `POST /api/database/init` - Initialize database tables
- `GET /api/database/tables` - Get database table info

### System
- `GET /api/devices` - Get device status
- `GET /api/system/info` - Get system information
- `GET /api/stats` - Get statistics

## Support

For issues and questions, check the logs first:
```bash
cat logs/iiot-gateway.log
```
