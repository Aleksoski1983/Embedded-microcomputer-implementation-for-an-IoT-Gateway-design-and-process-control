#!/bin/bash
# Installation script for IIoT Gateway on Raspberry Pi
# Run as regular user (pi), not root

set -e

echo "==================================="
echo "IIoT Gateway Installation Script"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root!"
    echo "Run as regular user (pi): ./install.sh"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

echo ""
echo -e "${YELLOW}Step 2: Installing system dependencies...${NC}"
sudo apt install -y python3-pip python3-venv mosquitto mosquitto-clients \
    influxdb2 influxdb2-cli grafana git

echo ""
echo -e "${YELLOW}Step 3: Enabling system services...${NC}"
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl enable influxdb
sudo systemctl start influxdb
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

echo ""
echo -e "${YELLOW}Step 4: Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo ""
echo -e "${YELLOW}Step 5: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo -e "${YELLOW}Step 6: Creating environment file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}Created .env file${NC}"
    echo "IMPORTANT: Edit .env file with your configuration!"
else
    echo ".env file already exists, skipping..."
fi

echo ""
echo -e "${YELLOW}Step 7: Initializing database...${NC}"
python database/init_db.py

echo ""
echo -e "${YELLOW}Step 8: Setting up systemd service...${NC}"
sudo cp iiot-gateway.service /etc/systemd/system/
sudo sed -i "s|/home/pi/iiot-gateway|$(pwd)|g" /etc/systemd/system/iiot-gateway.service
sudo sed -i "s|User=pi|User=$USER|g" /etc/systemd/system/iiot-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable iiot-gateway

echo ""
echo -e "${YELLOW}Step 9: Configuring firewall (if enabled)...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw allow 5000/tcp comment 'IIoT Gateway Web Interface'
    sudo ufw allow 1883/tcp comment 'MQTT Broker'
    sudo ufw allow 4840/tcp comment 'OPC UA Server'
    sudo ufw allow 3000/tcp comment 'Grafana'
    sudo ufw allow 8086/tcp comment 'InfluxDB'
    echo -e "${GREEN}Firewall rules added${NC}"
else
    echo "UFW not installed, skipping firewall configuration"
fi

echo ""
echo -e "${GREEN}==================================="
echo "Installation Complete!"
echo "===================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration:"
echo "   nano .env"
echo ""
echo "2. Configure your Siemens S7-1500 OPC UA endpoint in .env"
echo "   OPCUA_CLIENT_ENDPOINT=opc.tcp://YOUR_PLC_IP:4840"
echo ""
echo "3. Configure InfluxDB:"
echo "   - Visit http://$(hostname -I | awk '{print $1}'):8086"
echo "   - Create organization, bucket, and token"
echo "   - Update .env with InfluxDB credentials"
echo ""
echo "4. Start the gateway:"
echo "   sudo systemctl start iiot-gateway"
echo ""
echo "5. Check status:"
echo "   sudo systemctl status iiot-gateway"
echo ""
echo "6. View logs:"
echo "   sudo journalctl -u iiot-gateway -f"
echo ""
echo "7. Access web interface:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "8. Access Grafana:"
echo "   http://$(hostname -I | awk '{print $1}'):3000"
echo "   Default credentials: admin/admin"
echo ""
