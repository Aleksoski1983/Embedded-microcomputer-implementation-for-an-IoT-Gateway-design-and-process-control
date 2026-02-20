// Dashboard JavaScript

// Initialize Dashboard
async function initDashboard() {
    // Load initial data
    await loadSystemInfo();
    await loadStats();
    await loadDevices();
    await loadDatabaseStatus();
    
    // Start real-time updates
    setInterval(loadSystemInfo, 5000);
    setInterval(loadStats, 10000);
    setInterval(loadDevices, 15000);
    setInterval(loadDatabaseStatus, 30000);
}

// Load System Information
async function loadSystemInfo() {
    try {
        const data = await API.get('/system/info');
        
        console.log('System info response:', data);
        
        if (data.success) {
            const { mqtt, opcua_client } = data.system;
            
            console.log('MQTT connected:', mqtt.connected);
            console.log('OPC UA connected:', opcua_client.connected);
            
            // Update MQTT status
            updateStatus('mqtt-status', mqtt.connected, 
                mqtt.connected ? 'Connected' : 'Disconnected');
            document.getElementById('mqtt-broker').textContent = mqtt.broker;
            
            // Update OPC UA Client status
            updateStatus('opcua-client-status', opcua_client.connected,
                opcua_client.connected ? 'Connected' : 'Disconnected');
            document.getElementById('opcua-client-endpoint').textContent = opcua_client.endpoint;
        } else {
            console.error('System info request failed:', data.error);
        }
    } catch (error) {
        console.error('Error loading system info:', error);
        // Set all to disconnected on error
        updateStatus('mqtt-status', false, 'Disconnected');
        updateStatus('opcua-client-status', false, 'Disconnected');
    }
}

// Load Statistics
async function loadStats() {
    try {
        const data = await API.get('/stats');
        
        if (data.success) {
            document.getElementById('stat-variables').textContent = data.stats.monitored_variables;
            document.getElementById('stat-mappings').textContent = data.stats.mqtt_mappings;
            document.getElementById('stat-devices').textContent = 
                `${data.stats.devices_online}/${data.stats.devices}`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load Devices
async function loadDevices() {
    try {
        const data = await API.get('/devices');
        
        if (data.success) {
            const tbody = document.getElementById('devices-tbody');
            tbody.innerHTML = '';
            
            if (data.devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No devices found</td></tr>';
                return;
            }
            
            data.devices.forEach(device => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${device.device_type.toUpperCase()}</td>
                    <td>${device.name}</td>
                    <td>${device.connection_string || 'N/A'}</td>
                    <td><span class="status-dot ${device.status === 'connected' ? 'online' : 'offline'}"></span> ${device.status}</td>
                    <td>${formatTimestamp(device.last_seen)}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading devices:', error);
    }
}

// Load Database Status
async function loadDatabaseStatus() {
    try {
        const data = await API.get('/database/status');
        
        if (data.success) {
            const db = data.database;
            const dbStatusDot = document.getElementById('db-status-dot');
            const dbStatusText = document.getElementById('db-status-text');
            const dbInfo = document.getElementById('db-info');
            
            const postgresOk = db.postgresql && db.postgresql.connected;
            
            if (dbStatusDot) {
                dbStatusDot.classList.remove('online', 'offline');
                dbStatusDot.classList.add(postgresOk ? 'online' : 'offline');
            }
            
            if (dbStatusText) {
                dbStatusText.textContent = postgresOk ? 'PostgreSQL Connected' : 'PostgreSQL Not Connected';
            }
            
            if (dbInfo) {
                if (postgresOk) {
                    dbInfo.textContent = `${db.postgresql.host}:${db.postgresql.port}/${db.postgresql.database}`;
                } else {
                    dbInfo.textContent = 'Not connected to PostgreSQL';
                }
            }
        }
    } catch (error) {
        console.error('Error loading database status:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
