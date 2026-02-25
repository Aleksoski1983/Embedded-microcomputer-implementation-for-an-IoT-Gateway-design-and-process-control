# IIoT Gateway - Raspberry Pi 5

Industrial IoT Gateway application for Raspberry Pi 5 that bridges MQTT sensors (Raspberry Pi Pico) with OPC UA, connects to Siemens S7-1500 PLC, and provides web-based monitoring and configuration.

## ✨ Latest Updates (v2.1.0)

### UI/UX Improvements
- **Redesigned Dashboard**: Streamlined interface with focus on system status
- **Unified Design**: All pages now share consistent styling, colors, and button designs
- **Navigation Update**: "Variables" renamed to "OPC-UA Variables" for clarity
- **Enhanced Responsiveness**: Improved mobile and tablet experience

### Bug Fixes
- **Fixed Unicode Encoding**: Resolved Windows console crash with Unicode characters (→, emojis)
- **Fixed Status Display**: Dashboard now correctly reflects actual connection states
- **Removed Deprecated Features**: Cleaned up unused temperature chart code

📖 **[View Complete Changelog](CHANGELOG.md)** for detailed information.

## Features

- **MQTT to OPC UA Bridge**: Converts temperature data from Raspberry Pi Pico (MQTT) to OPC UA variables
- **OPC UA Client**: Connects to Siemens S7-1500 PLC and browses/subscribes to variables
- **Variable Selection**: Web UI to browse and select which variables to store in database
- **Time-Series Storage**: PostgreSQL for sensor data and configuration
- **Real-Time Dashboard**: Flask web interface with live updates via WebSocket
- **Grafana Integration**: Visualization of historical and real-time data

## Architecture

```
Raspberry Pi Pico (MQTT) → Gateway → OPC UA Server (expose MQTT data)
                              ↓
Siemens S7-1500 (OPC UA) → Gateway → PostgreSQL → Grafana
                              ↓
                        Flask Web UI
```

## Installation

### Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS
- Python 3.9+
- Mosquitto MQTT Broker
- PostgreSQL 12+
- Grafana

### Quick Setup

1. Clone or copy this project to Raspberry Pi:
```bash
cd ~
git clone <repository-url> iiot-gateway
cd iiot-gateway
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

5. Initialize database:
```bash
python -m app.database.init_db
```

6. Run the application:
```bash
python run.py
```

### System Services Installation

For production deployment with auto-start:

```bash
# Install system dependencies
sudo apt update
sudo apt install mosquitto mosquitto-clients postgresql grafana -y

# Setup systemd service
sudo cp iiot-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable iiot-gateway
sudo systemctl start iiot-gateway
```

## Configuration

### MQTT Topics

Default structure for Raspberry Pi Pico:
- `pico/temperature` - Temperature sensor data

### OPC UA Endpoints

- **Gateway Server**: `opc.tcp://[PI-IP]:4840/iiot/gateway/`
- **S7-1500 PLC**: Configure in `.env` file

### Database

- **PostgreSQL**: Time-series sensor data, variable configurations, and device metadata

## Usage

### Web Interface

Access the dashboard at `http://[PI-IP]:5000`

1. **Dashboard**: View real-time sensor values and system status
2. **Variable Browser**: Browse OPC UA variables from S7-1500
3. **Configuration**: Select variables to store, configure MQTT mappings
4. **Logs**: View application logs and connection status

### REST API

#### OPC UA Endpoints
- `GET /api/opcua/browse?node_id=ns=2;i=84` - Browse OPC UA namespace
- `GET /api/opcua/namespaces` - Get list of OPC UA namespaces
- `GET /api/opcua/variables/selected` - Get monitored variables
- `POST /api/opcua/variables/select` - Add variable to monitoring
- `DELETE /api/opcua/variables/{id}` - Remove variable
- `POST /api/opcua/read` - Read a single OPC UA variable value
- `GET /api/opcua/status` - Get OPC UA client connection status
- `POST /api/opcua/client/configure` - Configure OPC UA client settings
- `POST /api/opcua/client/test` - Test OPC UA connection
- `POST /api/opcua/client/connect` - Connect OPC UA client
- `POST /api/opcua/client/disconnect` - Disconnect OPC UA client

#### MQTT Endpoints
- `GET /api/mqtt/topics` - List MQTT topic mappings
- `POST /api/mqtt/expose` - Expose MQTT topic as OPC UA variable
- `DELETE /api/mqtt/mappings/{id}` - Remove MQTT mapping
- `GET /api/mqtt/status` - Get MQTT connection status
- `POST /api/mqtt/test` - Test MQTT broker connection
- `POST /api/mqtt/connect` - Connect to MQTT broker
- `POST /api/mqtt/disconnect` - Disconnect from MQTT broker
- `POST /api/mqtt/configure` - Configure MQTT broker settings
- `POST /api/mqtt/publish` - Publish message to MQTT topic

#### Database Endpoints
- `GET /api/database/status` - Get database connection status
- `POST /api/database/test` - Test database connections
- `POST /api/database/init` - Initialize database tables
- `POST /api/database/configure` - Configure database settings
- `GET /api/database/tables` - Get list of database tables

#### System Endpoints
- `GET /api/system/info` - Get system information
- `GET /api/stats` - Get statistics
- `GET /api/devices` - Get list of all devices
- `GET /api/data/query` - Query sensor data from PostgreSQL
- `GET /api/data/latest/{measurement}` - Get latest value for a measurement

## Development

### Project Structure

```
iiot-gateway/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration
│   ├── api/                  # REST API endpoints
│   ├── services/             # Background services
│   │   ├── mqtt_service.py
│   │   ├── opcua_server_service.py
│   │   ├── opcua_client_service.py
│   │   └── database_service.py
│   ├── models/               # Data models
│   ├── static/               # CSS, JS, images
│   └── templates/            # HTML templates
├── database/                 # Database initialization
├── logs/                     # Application logs
├── run.py                    # Development entry point
└── wsgi.py                   # Production entry point
```

### Running Tests

```bash
pytest tests/
```

## Troubleshooting

### Common Issues

1. **OPC UA connection fails**: Check firewall, PLC endpoint URL, and network connectivity
2. **MQTT not receiving**: Verify Mosquitto is running and credentials are correct
3. **PostgreSQL errors**: Ensure PostgreSQL service is running and database is configured
4. **Dashboard shows disconnected**: Clear browser cache and check console (F12)
5. **Unicode encoding errors**: Update to v2.1.0+ for Windows console fix

### Logs

Check logs at `logs/iiot-gateway.log` or:
```bash
sudo journalctl -u iiot-gateway -f
```

For detailed troubleshooting, see [QUICK_START.md](QUICK_START.md#troubleshooting)

## Documentation

- **[Quick Start Guide](QUICK_START.md)** - Installation and initial setup
- **[Changelog](CHANGELOG.md)** - Version history and updates
- **[UI Style Guide](UI_STYLE_GUIDE.md)** - Design system and component usage
- **[Testing Guide](TESTING_GUIDE.md)** - Testing procedures and validation
- **[MQTT Subscription Guide](MQTT_SUBSCRIPTION_GUIDE.md)** - MQTT configuration details
- **[OPC-UA Troubleshooting](OPCUA_TROUBLESHOOTING.md)** - OPC-UA connection issues
- **[PostgreSQL Setup](database/POSTGRESQL_SETUP.md)** - Database configuration
- **[Data Flow](database/DATA_FLOW.md)** - Data architecture overview

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
