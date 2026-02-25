// Configuration Page JavaScript

// Show notification helper
function showNotification(message, type = 'info') {
    // Use alert for now, can be replaced with toast notification
    if (type === 'success') {
        alert('✓ ' + message);
    } else if (type === 'error') {
        alert('✗ ' + message);
    } else {
        alert(message);
    }
}

// Initialize Configuration Page
async function initConfigPage() {
    // MQTT Mapping handlers
    const addMappingBtn = document.getElementById('add-mqtt-mapping-btn');
    if (addMappingBtn) {
        addMappingBtn.addEventListener('click', openMappingModal);
    }
    
    // Modal handlers
    const modal = document.getElementById('mqtt-mapping-modal');
    if (modal) {
        document.querySelectorAll('.close').forEach(el => {
            el.addEventListener('click', () => modal.style.display = 'none');
        });
    }
    
    const mappingForm = document.getElementById('add-mqtt-mapping-form');
    if (mappingForm) {
        mappingForm.addEventListener('submit', addMQTTMapping);
    }
    
    // OPC UA Client config handlers
    const saveClientBtn = document.getElementById('save-opcua-client-btn');
    if (saveClientBtn) {
        saveClientBtn.addEventListener('click', saveOPCUAClientConfig);
    }
    
    const testBtn = document.getElementById('test-connection-btn');
    if (testBtn) {
        testBtn.addEventListener('click', testOPCUAConnection);
    }
    
    const disconnectBtn = document.getElementById('disconnect-btn');
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', disconnectOPCUA);
    }
    
    const connectBtn = document.getElementById('connect-btn');
    if (connectBtn) {
        connectBtn.addEventListener('click', connectOPCUA);
    }
    
    // MQTT Broker handlers
    const testMqttBtn = document.getElementById('test-mqtt-btn');
    if (testMqttBtn) {
        testMqttBtn.addEventListener('click', testMQTTConnection);
    }
    
    const saveMqttBtn = document.getElementById('save-mqtt-btn');
    if (saveMqttBtn) {
        saveMqttBtn.addEventListener('click', saveMQTTConfig);
    }
    
    const connectMqttBtn = document.getElementById('connect-mqtt-btn');
    if (connectMqttBtn) {
        connectMqttBtn.addEventListener('click', connectMQTT);
    }
    
    const disconnectMqttBtn = document.getElementById('disconnect-mqtt-btn');
    if (disconnectMqttBtn) {
        disconnectMqttBtn.addEventListener('click', disconnectMQTT);
    }
    
    // Database handlers
    const testDbBtn = document.getElementById('test-db-btn');
    if (testDbBtn) {
        testDbBtn.addEventListener('click', testDatabaseConnection);
    }
    
    const connectDbBtn = document.getElementById('connect-db-btn');
    if (connectDbBtn) {
        connectDbBtn.addEventListener('click', connectDatabase);
    }
    
    const disconnectDbBtn = document.getElementById('disconnect-db-btn');
    if (disconnectDbBtn) {
        disconnectDbBtn.addEventListener('click', disconnectDatabase);
    }
    
    const saveDbBtn = document.getElementById('save-db-btn');
    if (saveDbBtn) {
        saveDbBtn.addEventListener('click', saveDatabaseConfig);
    }
    
    const initDbBtn = document.getElementById('init-db-btn');
    if (initDbBtn) {
        initDbBtn.addEventListener('click', initializeDatabase);
    }
    
    // MQTT Subscription handlers
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', subscribeTopic);
    }
    
    // Bridge transform selector
    const bridgeTransform = document.getElementById('bridge-transform');
    if (bridgeTransform) {
        bridgeTransform.addEventListener('change', function() {
            const param = document.getElementById('transform-param');
            if (this.value) {
                param.style.display = 'inline-block';
                if (this.value === 'json_extract') {
                    param.placeholder = 'Field name (e.g., value)';
                } else if (this.value === 'multiply') {
                    param.placeholder = 'Factor (e.g., 1.8)';
                } else if (this.value === 'prefix') {
                    param.placeholder = 'Prefix text';
                }
            } else {
                param.style.display = 'none';
            }
        });
    }
    
    // Bridge rule handler
    const addBridgeBtn = document.getElementById('add-bridge-btn');
    if (addBridgeBtn) {
        addBridgeBtn.addEventListener('click', addBridgeRule);
    }
    
    // Load data
    await loadMQTTMappings();
    await loadSystemConfig();
    await loadDatabaseStatus();
    await loadSubscriptions();
    await loadBridgeRules();
    
    // Start polling connection status
    setInterval(updateConnectionStatus, 5000);
    setInterval(updateMQTTStatus, 5000);
    updateConnectionStatus();
    updateMQTTStatus();
}

// Load MQTT Mappings
async function loadMQTTMappings() {
    try {
        const data = await API.get('/mqtt/topics');
        
        if (data.success) {
            const tbody = document.getElementById('mqtt-mappings-tbody');
            tbody.innerHTML = '';
            
            if (data.topics.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No MQTT mappings configured</td></tr>';
                return;
            }
            
            data.topics.forEach(mapping => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${mapping.mqtt_topic}</td>
                    <td title="${mapping.opcua_node_id}">${mapping.opcua_browse_name}</td>
                    <td>${mapping.json_key || 'value'}</td>
                    <td>${mapping.data_type}</td>
                    <td>${mapping.unit || 'N/A'}</td>
                    <td>${mapping.store_to_postgres || mapping.store_to_influxdb ? '✓' : '✗'}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="removeMQTTMapping(${mapping.id})">Remove</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading MQTT mappings:', error);
    }
}

// Load System Configuration
async function loadSystemConfig() {
    try {
        console.log('Loading system config...');
        const data = await API.get('/system/info');
        console.log('System config loaded:', data);
        
        if (data.success) {
            const opcuaClient = data.system.opcua_client || {};
            const mqtt = data.system.mqtt || {};
            console.log('OPC UA Client data:', opcuaClient);
            console.log('MQTT data:', mqtt);
            
            document.getElementById('config-mqtt-broker').textContent = mqtt.broker || 'Not configured';
            document.getElementById('config-opcua-client').textContent = opcuaClient.endpoint || 'Not configured';
            document.getElementById('config-postgresql').textContent = data.system.database.postgresql || 'Not configured';
            
            // Populate OPC UA Client field
            const endpointInput = document.getElementById('opcua-client-endpoint');
            if (endpointInput) {
                endpointInput.value = opcuaClient.endpoint || '';
                // Set placeholder with example
                if (!opcuaClient.endpoint) {
                    endpointInput.placeholder = 'opc.tcp://192.168.1.100:4840';
                }
            }
            
            // Populate security settings if available
            if (opcuaClient.security_policy) {
                document.getElementById('security-policy').value = opcuaClient.security_policy;
            }
            if (opcuaClient.security_mode) {
                document.getElementById('security-mode').value = opcuaClient.security_mode;
            }
            if (opcuaClient.timeout) {
                document.getElementById('connection-timeout').value = opcuaClient.timeout;
            }
            
            // Populate MQTT Broker fields
            if (mqtt.broker) {
                console.log('MQTT broker from API:', mqtt.broker);
                const brokerParts = mqtt.broker.split(':');
                console.log('Broker parts:', brokerParts);
                const brokerAddr = document.getElementById('mqtt-broker-address');
                const brokerPort = document.getElementById('mqtt-port');
                if (brokerAddr) {
                    brokerAddr.value = brokerParts[0] || 'localhost';
                    console.log('Set broker address field to:', brokerAddr.value);
                }
                if (brokerPort) {
                    brokerPort.value = brokerParts[1] || '1883';
                    console.log('Set broker port field to:', brokerPort.value);
                }
            } else {
                console.warn('No MQTT broker in API response');
            }
            
            // Update MQTT status
            updateMQTTStatusUI(mqtt.connected);
            
            console.log('System config loaded successfully');
        }
    } catch (error) {
        console.error('Error loading system config:', error);
        alert('Error loading configuration: ' + error.message);
    }
}

// Open MQTT Mapping Modal
function openMappingModal() {
    document.getElementById('mqtt-mapping-modal').style.display = 'block';
}

// Add MQTT Mapping
async function addMQTTMapping(e) {
    e.preventDefault();
    
    // Get form elements
    const mqttTopicEl = document.getElementById('mqtt-topic');
    const opcuaBrowseNameEl = document.getElementById('opcua-browse-name');
    const opcuaNodeIdEl = document.getElementById('opcua-node-id');
    const jsonKeyEl = document.getElementById('json-key');
    const dataTypeEl = document.getElementById('data-type');
    const unitEl = document.getElementById('unit');
    const measurementNameEl = document.getElementById('measurement-name');
    const storeToDbEl = document.getElementById('store-to-db');
    
    // Check if all required elements exist
    if (!mqttTopicEl || !opcuaBrowseNameEl) {
        alert('Error: Required form fields not found');
        return;
    }
    
    const data = {
        mqtt_topic: mqttTopicEl.value,
        opcua_browse_name: opcuaBrowseNameEl.value,
        opcua_node_id: opcuaNodeIdEl ? (opcuaNodeIdEl.value || null) : null,
        json_key: jsonKeyEl ? (jsonKeyEl.value || 'value') : 'value',
        data_type: dataTypeEl ? dataTypeEl.value : 'Double',
        unit: unitEl ? unitEl.value : '',
        measurement_name: measurementNameEl ? measurementNameEl.value : '',
        store_to_postgres: storeToDbEl ? storeToDbEl.checked : true
    };
    
    console.log('Submitting mapping data:', data);
    
    try {
        const result = await API.post('/mqtt/expose', data);
        
        if (result.success) {
            alert('MQTT mapping created successfully');
            document.getElementById('mqtt-mapping-modal').style.display = 'none';
            document.getElementById('add-mqtt-mapping-form').reset();
            await loadMQTTMappings();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error creating mapping:', error);
        alert('Error creating mapping: ' + error.message);
    }
}

// Remove MQTT Mapping
async function removeMQTTMapping(mappingId) {
    if (!confirm('Remove this MQTT mapping?')) return;
    
    try {
        const result = await API.delete(`/mqtt/mappings/${mappingId}`);
        
        if (result.success) {
            await loadMQTTMappings();
            alert('Mapping removed');
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error removing mapping: ' + error.message);
    }
}

// Save OPC UA Client Configuration
async function saveOPCUAClientConfig() {
    const endpoint = document.getElementById('opcua-client-endpoint').value.trim();
    const securityPolicy = document.getElementById('security-policy').value;
    const securityMode = document.getElementById('security-mode').value;
    const timeout = parseInt(document.getElementById('connection-timeout').value);
    
    if (!endpoint) {
        showNotification('Please enter OPC UA Client endpoint', 'error');
        return;
    }
    
    if (!endpoint.startsWith('opc.tcp://')) {
        showNotification('Endpoint must start with opc.tcp://\n\nExample: opc.tcp://192.168.1.100:4840', 'error');
        return;
    }
    
    // Validate endpoint format
    try {
        const url = new URL(endpoint);
        if (!url.hostname) {
            showNotification('Invalid endpoint format. Please enter a valid URL.\n\nExample: opc.tcp://192.168.1.100:4840', 'error');
            return;
        }
    } catch (e) {
        showNotification('Invalid endpoint format. Please enter a valid URL.\n\nExample: opc.tcp://192.168.1.100:4840', 'error');
        return;
    }
    
    if (!confirm(`Save and apply OPC UA Client settings:\nEndpoint: ${endpoint}\nSecurity: ${securityPolicy}/${securityMode}\nTimeout: ${timeout}s\n\nThis will reconnect to the server. Continue?`)) {
        return;
    }
    
    const saveBtn = document.getElementById('save-opcua-client-btn');
    const originalText = saveBtn.textContent;
    
    try {
        saveBtn.textContent = 'Saving...';
        saveBtn.disabled = true;
        
        const result = await API.post('/opcua/client/configure', { 
            endpoint,
            security_policy: securityPolicy,
            security_mode: securityMode,
            timeout
        });
        
        if (result.success) {
            showNotification('OPC UA configuration saved successfully!', 'success');
            
            // Reload configuration to show saved values
            await loadSystemConfig();
            
            // Update connection status
            setTimeout(() => {
                updateConnectionStatus();
                // Notify other pages via socket
                if (window.socket) {
                    window.socket.emit('config_updated', { type: 'opcua' });
                }
            }, 1000);
        } else {
            showNotification('Error: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showNotification('Error saving configuration: ' + error.message, 'error');
    } finally {
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    }
}

// Test OPC UA Connection
async function testOPCUAConnection() {
    const endpoint = document.getElementById('opcua-client-endpoint').value.trim();
    const securityPolicy = document.getElementById('security-policy').value;
    const securityMode = document.getElementById('security-mode').value;
    const timeout = parseInt(document.getElementById('connection-timeout').value);
    
    console.log('Testing connection with:', { endpoint, securityPolicy, securityMode, timeout });
    
    if (!endpoint) {
        showNotification('Please enter OPC UA Client endpoint', 'error');
        return;
    }
    
    if (!endpoint.startsWith('opc.tcp://')) {
        showNotification('Endpoint must start with opc.tcp://\nExample: opc.tcp://192.168.1.100:4840', 'error');
        return;
    }
    
    const testBtn = document.getElementById('test-connection-btn');
    const originalText = testBtn.textContent;
    const statusSpan = document.getElementById('opcua-connection-status');
    
    try {
        testBtn.textContent = '⏳ Testing...';
        testBtn.disabled = true;
        statusSpan.textContent = 'Testing...';
        statusSpan.className = 'badge badge-info';
        
        console.log('Sending test request...');
        const result = await API.post('/opcua/client/test', { 
            endpoint,
            security_policy: securityPolicy,
            security_mode: securityMode,
            timeout
        });
        
        console.log('Test result:', result);
        
        if (result.success) {
            statusSpan.textContent = '✓ Test Passed';
            statusSpan.className = 'badge badge-success';
            
            const message = `✓ Connection Test Successful!\n\n` +
                `Endpoint: ${endpoint}\n` +
                `Security: ${securityPolicy}/${securityMode}\n` +
                `Timeout: ${timeout}s\n` +
                `Namespaces: ${result.namespaces || 'N/A'}\n\n` +
                `The server is reachable and responding correctly.`;
            
            showNotification(message, 'success');
            
            // Reset status after 3 seconds
            setTimeout(updateConnectionStatus, 3000);
        } else {
            statusSpan.textContent = '✗ Test Failed';
            statusSpan.className = 'badge badge-danger';
            
            const message = `✗ Connection Test Failed!\n\n` +
                `Error: ${result.error || 'Unknown error'}\n\n` +
                `Please check:\n` +
                `• Endpoint URL is correct\n` +
                `• Server is running and accessible\n` +
                `• Network connectivity\n` +
                `• Firewall settings\n` +
                `• Security settings match server`;
            
            showNotification(message, 'error');
            
            // Reset status after 3 seconds
            setTimeout(updateConnectionStatus, 3000);
        }
    } catch (error) {
        console.error('Test connection error:', error);
        statusSpan.textContent = '✗ Error';
        statusSpan.className = 'badge badge-danger';
        showNotification('Test connection failed: ' + error.message, 'error');
        setTimeout(updateConnectionStatus, 3000);
    } finally {
        testBtn.textContent = originalText;
        testBtn.disabled = false;
    }
}

// Update Connection Status
async function updateConnectionStatus() {
    try {
        const result = await API.get('/opcua/client/status');
        console.log('Connection status:', result);
        
        const statusBadge = document.getElementById('opcua-connection-status');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const connectBtn = document.getElementById('connect-btn');
        const testBtn = document.getElementById('test-connection-btn');
        const saveBtn = document.getElementById('save-opcua-client-btn');
        
        if (!statusBadge) {
            console.error('Status badge element not found!');
            return;
        }
        
        if (result.success && result.connected) {
            statusBadge.className = 'badge badge-success';
            statusBadge.textContent = '✓ Connected';
            
            // Show disconnect button, hide connect button
            if (disconnectBtn) {
                disconnectBtn.style.display = 'inline-block';
                disconnectBtn.disabled = false;
            }
            if (connectBtn) {
                connectBtn.style.display = 'none';
            }
            
            // Keep test and save buttons enabled
            if (testBtn) testBtn.disabled = false;
            if (saveBtn) saveBtn.disabled = false;
            
        } else {
            statusBadge.className = 'badge badge-secondary';
            statusBadge.textContent = '✗ Disconnected';
            
            // Hide disconnect button, show connect button
            if (disconnectBtn) {
                disconnectBtn.style.display = 'none';
            }
            if (connectBtn) {
                connectBtn.style.display = 'inline-block';
                connectBtn.disabled = false;
            }
            
            // Keep test and save buttons enabled
            if (testBtn) testBtn.disabled = false;
            if (saveBtn) saveBtn.disabled = false;
        }
        
        // Notify dashboard page if in sync mode
        if (window.socket && result.connected !== undefined) {
            window.socket.emit('status_sync', { 
                type: 'opcua_client',
                connected: result.connected 
            });
        }
        
    } catch (error) {
        console.error('Error updating connection status:', error);
        const statusBadge = document.getElementById('opcua-connection-status');
        if (statusBadge) {
            statusBadge.className = 'badge badge-danger';
            statusBadge.textContent = '⚠ Error';
        }
    }
}

// Disconnect OPC UA Client
async function disconnectOPCUA() {
    if (!confirm('Disconnect from OPC UA server?')) return;
    
    const btn = document.getElementById('disconnect-btn');
    const originalText = btn.textContent;
    const statusBadge = document.getElementById('opcua-connection-status');
    
    try {
        btn.textContent = '🔌 Disconnecting...';
        btn.disabled = true;
        
        if (statusBadge) {
            statusBadge.className = 'badge badge-warning';
            statusBadge.textContent = 'Disconnecting...';
        }
        
        const result = await API.post('/opcua/client/disconnect', {});
        
        if (result.success) {
            showNotification('✓ Disconnected from OPC UA server successfully', 'success');
            
            // Update status immediately
            await updateConnectionStatus();
        } else {
            showNotification('✗ Disconnect failed: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showNotification('✗ Disconnect error: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
        
        // Update status after a brief delay
        setTimeout(updateConnectionStatus, 500);
    }
}

// Connect OPC UA Client
async function connectOPCUA() {
    const btn = document.getElementById('connect-btn');
    const originalText = btn.textContent;
    const statusBadge = document.getElementById('opcua-connection-status');
    
    try {
        btn.textContent = '🔌 Connecting...';
        btn.disabled = true;
        
        if (statusBadge) {
            statusBadge.className = 'badge badge-info';
            statusBadge.textContent = 'Connecting...';
        }
        
        const result = await API.post('/opcua/client/connect', {});
        
        if (result.success) {
            showNotification('✓ Connected to OPC UA server successfully', 'success');
            
            // Update status immediately
            await updateConnectionStatus();
        } else {
            showNotification('✗ Connection failed: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showNotification('✗ Connection error: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
        
        // Update status after a brief delay
        setTimeout(updateConnectionStatus, 500);
    }
}

// Export functions
window.removeMQTTMapping = removeMQTTMapping;

// ==========================================
// MQTT Broker Configuration Functions
// ==========================================

async function testMQTTConnection() {
    const broker = document.getElementById('mqtt-broker-address').value.trim() || 'localhost';
    const port = parseInt(document.getElementById('mqtt-port').value) || 1883;
    const username = document.getElementById('mqtt-username').value.trim();
    const password = document.getElementById('mqtt-password').value;
    
    const btn = document.getElementById('test-mqtt-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Testing...';
        btn.disabled = true;
        
        const result = await API.post('/mqtt/test', {
            broker,
            port,
            username: username || null,
            password: password || null
        });
        
        if (result.success) {
            alert(`MQTT Connection Test Successful!\n\nBroker: ${broker}:${port}\nTCP Reachable: ${result.tcp_reachable ? 'Yes' : 'No'}`);
        } else {
            alert(`MQTT Connection Test Failed!\n\nError: ${result.error || 'Unknown error'}\n\nPlease check:\n- Broker address is correct\n- Mosquitto is running\n- Network connectivity`);
        }
    } catch (error) {
        console.error('Test MQTT error:', error);
        alert(`MQTT Connection Test Error!\n\n${error.message}`);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function saveMQTTConfig() {
    const broker = document.getElementById('mqtt-broker-address').value.trim();
    const port = parseInt(document.getElementById('mqtt-port').value) || 1883;
    const username = document.getElementById('mqtt-username').value.trim();
    const password = document.getElementById('mqtt-password').value;
    
    console.log('Saving MQTT config:', { broker, port, username });
    
    if (!broker) {
        alert('Please enter MQTT broker address');
        return;
    }
    
    if (!confirm(`Save MQTT configuration?\n\nBroker: ${broker}:${port}\n\nThis will update the configuration. You may need to reconnect.`)) {
        return;
    }
    
    try {
        console.log('Sending save request to /mqtt/configure...');
        const result = await API.post('/mqtt/configure', {
            broker,
            port,
            username: username || '',
            password: password || '',
            reconnect: true
        });
        
        console.log('Save result:', result);
        
        if (result.success) {
            alert('MQTT configuration saved successfully!');
            console.log('Reloading system config...');
            await loadSystemConfig();
            console.log('System config reloaded');
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving MQTT configuration:', error);
        alert('Error saving MQTT configuration: ' + error.message);
    }
}

async function connectMQTT() {
    const btn = document.getElementById('connect-mqtt-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Connecting...';
        btn.disabled = true;
        
        const result = await API.post('/mqtt/connect', {});
        
        if (result.success) {
            updateMQTTStatusUI(true);
            alert('Connected to MQTT broker successfully!');
        } else {
            alert('Connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Connection error: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function disconnectMQTT() {
    if (!confirm('Disconnect from MQTT broker?')) return;
    
    const btn = document.getElementById('disconnect-mqtt-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Disconnecting...';
        btn.disabled = true;
        
        const result = await API.post('/mqtt/disconnect', {});
        
        if (result.success) {
            updateMQTTStatusUI(false);
            alert('Disconnected from MQTT broker');
        } else {
            alert('Disconnect failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Disconnect error: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function updateMQTTStatus() {
    try {
        const result = await API.get('/system/info');
        
        if (result.success && result.system.mqtt) {
            updateMQTTStatusUI(result.system.mqtt.connected);
        }
    } catch (error) {
        console.error('Error updating MQTT status:', error);
    }
}

function updateMQTTStatusUI(connected) {
    const statusBadge = document.getElementById('mqtt-connection-status');
    const connectBtn = document.getElementById('connect-mqtt-btn');
    const disconnectBtn = document.getElementById('disconnect-mqtt-btn');
    
    if (statusBadge) {
        statusBadge.className = connected ? 'badge badge-success' : 'badge badge-secondary';
        statusBadge.textContent = connected ? 'Connected' : 'Disconnected';
    }
    
    if (connectBtn) connectBtn.style.display = connected ? 'none' : 'inline-block';
    if (disconnectBtn) disconnectBtn.style.display = connected ? 'inline-block' : 'none';
}

// ==========================================
// Database Configuration Functions
// ==========================================

async function loadDatabaseStatus() {
    try {
        const result = await API.get('/database/status');
        
        if (result.success) {
            const db = result.database;
            
            // PostgreSQL status
            const postgresStatus = document.getElementById('postgres-status');
            if (postgresStatus) {
                const isConnected = db.postgresql && db.postgresql.connected;
                postgresStatus.className = isConnected ? 'badge badge-success' : 'badge badge-warning';
                postgresStatus.textContent = isConnected ? 'Connected ✓' : 'Not Connected';
                
                // Log for debugging
                console.log('PostgreSQL status:', db.postgresql);
            }
            
            // Populate PostgreSQL fields
            if (document.getElementById('postgres-host')) {
                document.getElementById('postgres-host').value = db.postgresql?.host || 'localhost';
            }
            if (document.getElementById('postgres-port')) {
                document.getElementById('postgres-port').value = db.postgresql?.port || '5432';
            }
            if (document.getElementById('postgres-db')) {
                document.getElementById('postgres-db').value = db.postgresql?.database || 'iiot_gateway';
            }
            if (document.getElementById('postgres-user')) {
                document.getElementById('postgres-user').value = db.postgresql?.user || 'iiot_user';
            }
        }
    } catch (error) {
        console.error('Error loading database status:', error);
    }
}

async function connectDatabase() {
    const btn = document.getElementById('connect-db-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Connecting...';
        btn.disabled = true;
        
        const result = await API.post('/database/init', {});
        
        if (result.success) {
            alert('✅ PostgreSQL connected successfully!');
            await loadDatabaseStatus();
        } else {
            alert('❌ Connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Connect database error:', error);
        alert('❌ Connection error: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function disconnectDatabase() {
    const btn = document.getElementById('disconnect-db-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Disconnecting...';
        btn.disabled = true;
        
        const result = await API.post('/database/disconnect', {});
        
        if (result.success) {
            alert('✅ PostgreSQL disconnected successfully!');
            await loadDatabaseStatus();
        } else {
            alert('❌ Disconnect failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Disconnect database error:', error);
        alert('❌ Disconnect error: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function testDatabaseConnection() {
    const btn = document.getElementById('test-db-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Testing...';
        btn.disabled = true;
        
        const result = await API.post('/database/test', { type: 'postgresql' });
        
        if (result.success) {
            let message = 'PostgreSQL Connection Test:\n\n';
            
            // PostgreSQL result
            if (result.tests.postgresql) {
                const pg = result.tests.postgresql;
                message += `Status: ${pg.success ? '✅ Connected' : '❌ Failed'}\n`;
                if (pg.success) {
                    message += `Host: ${pg.host}:${pg.port}\n`;
                    message += `Database: ${pg.database}\n`;
                    message += `Version: ${pg.version}\n`;
                    message += `Table exists: ${pg.table_exists ? 'Yes' : 'No'}\n`;
                    if (pg.table_exists) {
                        message += `Row count: ${pg.row_count}\n`;
                    }
                } else {
                    message += `Error: ${pg.error}\n`;
                }
            }
            
            alert(message);
            await loadDatabaseStatus();
        } else {
            alert('Database test failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Test database error:', error);
        alert('Database test error: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function saveDatabaseConfig() {
    const postgresHost = document.getElementById('postgres-host').value.trim();
    const postgresPort = document.getElementById('postgres-port').value.trim();
    const postgresDb = document.getElementById('postgres-db').value.trim();
    const postgresUser = document.getElementById('postgres-user').value.trim();
    const postgresPassword = document.getElementById('postgres-password').value.trim();
    
    if (!postgresHost) {
        alert('Please enter PostgreSQL host');
        return;
    }
    
    if (!confirm('Save database configuration? This will reconnect to PostgreSQL.')) {
        return;
    }
    
    try {
        const data = {
            postgres_host: postgresHost,
            postgres_port: postgresPort || '5432',
            postgres_db: postgresDb || 'iiot_gateway',
            postgres_user: postgresUser || 'iiot_user'
        };
        
        if (postgresPassword) data.postgres_password = postgresPassword;
        
        const result = await API.post('/database/configure', data);
        
        if (result.success) {
            alert('Database configuration saved successfully!');
            await loadDatabaseStatus();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error saving database configuration: ' + error.message);
    }
}

async function initializeDatabase() {
    if (!confirm('Initialize database tables? This will create any missing tables.')) {
        return;
    }
    
    const btn = document.getElementById('init-db-btn');
    const originalText = btn.textContent;
    
    try {
        btn.textContent = 'Initializing...';
        btn.disabled = true;
        
        const result = await API.post('/database/init', {});
        
        if (result.success) {
            alert('Database initialized successfully!');
            await loadDatabaseStatus();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error initializing database: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// ===== MQTT Subscription Functions =====

async function loadSubscriptions() {
    try {
        const result = await API.get('/mqtt/subscriptions');
        const tbody = document.getElementById('subscriptions-tbody');
        
        if (!result.success || result.subscriptions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #7f8c8d;">No active subscriptions. Subscribe to topics above to start monitoring messages.</td></tr>';
            return;
        }
        
        tbody.innerHTML = result.subscriptions.map(topic => `
            <tr>
                <td><code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${escapeHtml(topic)}</code></td>
                <td><span class="badge badge-info">1</span></td>
                <td><span class="badge" style="background: #9e9e9e;">Monitoring</span></td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="unsubscribeTopic('${escapeHtml(topic)}')">Unsubscribe</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading subscriptions:', error);
    }
}

async function subscribeTopic() {
    const topic = document.getElementById('subscribe-topic').value.trim();
    const qos = parseInt(document.getElementById('subscribe-qos').value);
    
    if (!topic) {
        alert('Please enter a topic');
        return;
    }
    
    try {
        console.log('Subscribing to:', topic, 'QoS:', qos);
        const result = await API.post('/mqtt/subscribe', { topic, qos });
        console.log('Subscribe result:', result);
        
        if (result.success) {
            showNotification(`Subscribed to topic: ${topic}`, 'success');
            document.getElementById('subscribe-topic').value = '';
            await loadSubscriptions();
        } else {
            showNotification(result.error || 'Subscription failed', 'error');
        }
    } catch (error) {
        showNotification('Error subscribing: ' + error.message, 'error');
    }
}

async function unsubscribeTopic(topic) {
    if (!confirm(`Unsubscribe from topic: ${topic}?`)) {
        return;
    }
    
    try {
        const result = await API.post('/mqtt/unsubscribe', { topic });
        
        if (result.success) {
            showNotification(`Unsubscribed from: ${topic}`, 'success');
            await loadSubscriptions();
        } else {
            showNotification(result.error || 'Unsubscribe failed', 'error');
        }
    } catch (error) {
        showNotification('Error unsubscribing: ' + error.message, 'error');
    }
}

// ===== MQTT Bridge Functions =====

async function loadBridgeRules() {
    try {
        const result = await API.get('/mqtt/bridge');
        const tbody = document.getElementById('bridge-rules-tbody');
        
        if (!result.success || result.rules.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No bridge rules configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = result.rules.map(rule => `
            <tr>
                <td>
                    <code>${escapeHtml(rule.source_topic)}</code> → <code>${escapeHtml(rule.target_topic)}</code>
                    ${rule.target_type === 'opcua' ? '<span class="badge" style="margin-left:8px;background:#8e44ad;color:#fff;">OPC-UA</span>' : ''}
                </td>
                <td>${rule.message_count}</td>
                <td>
                    ${rule.last_message ? new Date(rule.last_message).toLocaleString() : 'N/A'}
                    ${rule.last_error ? `<div style="color:#c0392b;font-size:12px;margin-top:4px;">${escapeHtml(rule.last_error)}</div>` : ''}
                </td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="removeBridgeRule(${rule.id})">Remove</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading bridge rules:', error);
    }
}

async function addBridgeRule() {
    const sourceTopic = document.getElementById('bridge-source').value.trim();
    const targetTopic = document.getElementById('bridge-target').value.trim();
    const transformType = document.getElementById('bridge-transform').value;
    const transformParam = document.getElementById('transform-param').value.trim();
    
    if (!sourceTopic || !targetTopic) {
        alert('Please enter both source and target topics');
        return;
    }
    
    const payload = {
        source_topic: sourceTopic,
        target_topic: targetTopic
    };
    
    // Add transform if selected
    if (transformType) {
        payload.transform = transformType;
        
        if (transformType === 'json_extract') {
            payload.field = transformParam || 'value';
        } else if (transformType === 'multiply') {
            payload.factor = parseFloat(transformParam) || 1.0;
        } else if (transformType === 'prefix') {
            payload.prefix = transformParam || '';
        }
    }
    
    try {
        const result = await API.post('/mqtt/bridge', payload);
        
        if (result.success) {
            showNotification(`Bridge rule added: ${sourceTopic} → ${targetTopic}`, 'success');
            document.getElementById('bridge-source').value = '';
            document.getElementById('bridge-target').value = '';
            document.getElementById('bridge-transform').value = '';
            document.getElementById('transform-param').style.display = 'none';
            await loadBridgeRules();
        } else {
            showNotification(result.error || 'Failed to add bridge rule', 'error');
        }
    } catch (error) {
        showNotification('Error adding bridge rule: ' + error.message, 'error');
    }
}

async function removeBridgeRule(ruleId) {
    if (!confirm('Remove this bridge rule?')) {
        return;
    }
    
    try {
        const result = await API.delete(`/mqtt/bridge/${ruleId}`);
        
        if (result.success) {
            showNotification('Bridge rule removed', 'success');
            await loadBridgeRules();
        } else {
            showNotification(result.error || 'Failed to remove bridge rule', 'error');
        }
    } catch (error) {
        showNotification('Error removing bridge rule: ' + error.message, 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initConfigPage);
