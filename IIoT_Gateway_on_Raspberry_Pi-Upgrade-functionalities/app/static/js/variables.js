// Variables Page JavaScript

let currentModal = null;
let currentVariableData = null;
let refreshInterval = null;

// Initialize Variables Page
async function initVariablesPage() {
    document.getElementById('browse-simple-btn').addEventListener('click', browseSimple);
    document.getElementById('add-manual-btn').addEventListener('click', openManualAddModal);
    document.getElementById('view-namespaces-btn').addEventListener('click', viewNamespaces);
    document.getElementById('refresh-btn').addEventListener('click', refreshTree);
    document.getElementById('reload-selected-btn').addEventListener('click', loadSelectedVariables);
    
    // Modal handlers
    const modal = document.getElementById('variable-modal');
    const manualModal = document.getElementById('manual-variable-modal');
    
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
            manualModal.style.display = 'none';
        });
    });
    
    document.getElementById('modal-cancel').addEventListener('click', () => modal.style.display = 'none');
    document.getElementById('manual-cancel').addEventListener('click', () => manualModal.style.display = 'none');
    document.getElementById('add-variable-form').addEventListener('submit', addVariable);
    document.getElementById('manual-variable-form').addEventListener('submit', addManualVariable);
    
    // Load selected variables and update status
    await loadSelectedVariables();
    await updateConnectionStatus();
    
    // Auto-refresh disabled - use Reload button to refresh manually
    // refreshInterval = setInterval(async () => {
    //     await loadSelectedVariables();
    //     await updateConnectionStatus();
    // }, 10000);
}

// Update connection status indicators
async function updateConnectionStatus() {
    try {
        const statusData = await API.get('/opcua/client/status');
        
        const connectionEl = document.getElementById('opcua-connection-status');
        if (statusData.connected) {
            connectionEl.textContent = 'Connected';
            connectionEl.className = 'status-badge connected';
        } else {
            connectionEl.textContent = 'Disconnected';
            connectionEl.className = 'status-badge disconnected';
        }
        
        // Get monitored variables count
        const varsData = await API.get('/opcua/variables/selected');
        if (varsData.success) {
            const totalCount = varsData.variables.length;
            const loggingCount = varsData.variables.filter(v => v.store_to_influxdb).length;
            
            document.getElementById('monitored-count').textContent = totalCount;
            document.getElementById('logging-count').textContent = loggingCount;
            
            // Update monitoring status
            const monitoringEl = document.getElementById('monitoring-status');
            if (statusData.connected && loggingCount > 0) {
                monitoringEl.textContent = 'Active';
                monitoringEl.className = 'status-badge connected';
            } else {
                monitoringEl.textContent = 'Stopped';
                monitoringEl.className = 'status-badge disconnected';
            }
        }
    } catch (error) {
        console.error('Error updating connection status:', error);
    }
}

// Simple Browse with folder support
async function browseSimple(nodeId = 'i=85') {
    const statusEl = document.getElementById('browse-status');
    statusEl.textContent = 'Browsing OPC-UA tree...';
    statusEl.className = 'status-message';
    
    try {
        const params = nodeId !== 'i=85' ? `?node_id=${encodeURIComponent(nodeId)}` : '';
        const data = await API.get(`/opcua/browse/simple${params}`);
        
        if (data.success) {
            renderBrowseTree(data.items, nodeId);
            statusEl.textContent = `Found ${data.count} items in ${nodeId}`;
            statusEl.className = 'status-message success';
        } else {
            statusEl.textContent = data.error || 'Failed to browse';
            statusEl.className = 'status-message error';
        }
    } catch (error) {
        statusEl.textContent = 'Error: ' + error.message;
        statusEl.className = 'status-message error';
    }
}

// Open Manual Add Modal
function openManualAddModal() {
    document.getElementById('manual-variable-modal').style.display = 'block';
    document.getElementById('manual-node-id').focus();
}

// View Available Namespaces
async function viewNamespaces() {
    const statusEl = document.getElementById('browse-status');
    statusEl.textContent = 'Getting namespaces...';
    statusEl.className = 'status-message';
    
    try {
        const data = await API.get('/opcua/namespaces');
        
        if (data.success) {
            // Display namespaces in the tree area
            const container = document.getElementById('opcua-tree');
            container.innerHTML = '<h4>Available Namespaces:</h4>';
            
            data.namespaces.forEach(ns => {
                const nsDiv = document.createElement('div');
                nsDiv.className = 'namespace-item';
                nsDiv.innerHTML = `
                    <strong>Index ${ns.index}:</strong> ${ns.uri}
                    ${ns.is_siemens ? '<span style="color: green;">[Siemens]</span>' : ''}
                `;
                container.appendChild(nsDiv);
            });
            
            if (data.server_info && data.server_info.server_array) {
                const serverDiv = document.createElement('div');
                serverDiv.innerHTML = `<h4>Server Info:</h4><pre>${JSON.stringify(data.server_info, null, 2)}</pre>`;
                container.appendChild(serverDiv);
            }
            
            statusEl.textContent = `Found ${data.count} namespaces`;
            statusEl.className = 'status-message success';
        } else {
            statusEl.textContent = data.error || 'Failed to get namespaces';
            statusEl.className = 'status-message error';
        }
    } catch (error) {
        statusEl.textContent = 'Error: ' + error.message;
        statusEl.className = 'status-message error';
    }
}

// Render OPC UA Tree
function renderTree(nodes, parentElement = null) {
    const container = parentElement || document.getElementById('opcua-tree');
    
    if (!parentElement) {
        container.innerHTML = '';
    }
    
    nodes.forEach(node => {
        const div = document.createElement('div');
        div.className = `tree-item ${node.is_variable ? 'variable' : 'folder'}`;
        div.style.marginLeft = `${node.depth * 20}px`;
        
        let icon = node.is_variable ? '📊' : '📁';
        let valueText = node.is_variable ? ` = ${node.current_value}` : '';
        
        div.innerHTML = `
            ${icon} ${node.display_name} ${valueText}
            ${node.is_variable ? '<button class="btn btn-sm add-btn">Add</button>' : ''}
        `;
        
        if (node.is_variable) {
            div.querySelector('.add-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                openAddModal(node);
            });
        }
        
        container.appendChild(div);
        
        if (node.children && node.children.length > 0) {
            renderTree(node.children, container);
        }
    });
}

// Open Add Variable Modal
function openAddModal(nodeData) {
    currentVariableData = nodeData;
    
    document.getElementById('modal-node-id').value = nodeData.node_id;
    document.getElementById('modal-browse-name').value = nodeData.browse_name;
    document.getElementById('modal-display-name').value = nodeData.display_name;
    document.getElementById('modal-measurement-name').value = nodeData.browse_name.toLowerCase();
    
    document.getElementById('variable-modal').style.display = 'block';
}

// Add Variable
async function addVariable(e) {
    e.preventDefault();
    
    const data = {
        node_id: document.getElementById('modal-node-id').value,
        browse_name: document.getElementById('modal-browse-name').value,
        display_name: document.getElementById('modal-display-name').value,
        measurement_name: document.getElementById('modal-measurement-name').value,
        namespace_index: currentVariableData.namespace_index,
        data_type: currentVariableData.data_type
    };
    
    try {
        const result = await API.post('/opcua/variables/select', data);
        
        if (result.success) {
            showMessage('browse-status', 'Variable added successfully', 'success');
            document.getElementById('variable-modal').style.display = 'none';
            await loadSelectedVariables();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error adding variable: ' + error.message);
    }
}

// Load Selected Variables
async function loadSelectedVariables() {
    try {
        const data = await API.get('/opcua/variables/selected');
        
        if (data.success) {
            const tbody = document.getElementById('selected-tbody');
            tbody.innerHTML = '';
            
            if (data.variables.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No variables monitored yet. Browse and add variables from the left panel.</td></tr>';
                return;
            }
            
            // Get current values if connected
            let currentValues = {};
            try {
                const valuesData = await API.get('/opcua/variables/values');
                if (valuesData.success) {
                    valuesData.values.forEach(v => {
                        currentValues[v.node_id] = v.value;
                    });
                }
            } catch (e) {
                console.log('Could not fetch current values:', e);
            }
            
            data.variables.forEach(variable => {
                const row = document.createElement('tr');
                
                // Format value display
                let valueDisplay = currentValues[variable.node_id] !== undefined 
                    ? currentValues[variable.node_id] 
                    : '---';
                
                let valueClass = 'variable-value';
                if (typeof valueDisplay === 'boolean') {
                    valueClass += valueDisplay ? ' boolean-true' : ' boolean-false';
                    valueDisplay = valueDisplay ? 'TRUE' : 'FALSE';
                }
                
                // Database indicator
                const dbIcon = variable.store_to_influxdb 
                    ? '<span class="db-indicator active" title="Logging to PostgreSQL">💾</span>'
                    : '<span class="db-indicator inactive" title="Not logging">💾</span>';
                
                // Status indicator
                const statusHtml = variable.enabled
                    ? '<span class="status-indicator enabled">Active</span>'
                    : '<span class="status-indicator disabled">Disabled</span>';
                
                row.innerHTML = `
                    <td title="${variable.node_id}">
                        <strong>${variable.display_name || variable.browse_name}</strong>
                        <br><small style="color: #95a5a6;">${variable.node_id.substring(0, 30)}...</small>
                    </td>
                    <td><span class="${valueClass}">${valueDisplay}</span></td>
                    <td><span class="variable-type-badge">${variable.data_type || 'Unknown'}</span></td>
                    <td style="text-align: center;">${dbIcon}</td>
                    <td>${statusHtml}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="removeVariable(${variable.id})">❌ Remove</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading selected variables:', error);
    }
}

// Remove Variable
async function removeVariable(variableId) {
    if (!confirm('Remove this variable from monitoring?')) return;
    
    try {
        const result = await API.delete(`/opcua/variables/${variableId}`);
        
        if (result.success) {
            await loadSelectedVariables();
            showMessage('browse-status', 'Variable removed', 'success');
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error removing variable: ' + error.message);
    }
}

function refreshTree() {
    browseSimple();
}

// View Available Namespaces
async function viewNamespaces() {
    const statusEl = document.getElementById('browse-status');
    statusEl.textContent = 'Getting namespaces...';
    statusEl.className = 'status-message';
    
    try {
        const data = await API.get('/opcua/namespaces');
        
        if (data.success) {
            // Display namespaces in the tree area
            const container = document.getElementById('opcua-tree');
            container.innerHTML = '<h4>Available Namespaces:</h4>';
            
            data.namespaces.forEach(ns => {
                const nsDiv = document.createElement('div');
                nsDiv.className = 'namespace-item';
                nsDiv.innerHTML = `
                    <div style="padding: 8px; border: 1px solid #ddd; margin: 4px 0; background: #f9f9f9;">
                        <strong>Index ${ns.index}:</strong> ${ns.uri}
                        ${ns.is_siemens ? '<span style="color: green;">[Siemens]</span>' : ''}
                        <br><small>Use in node IDs as: ns=${ns.index};s="VariableName"</small>
                    </div>
                `;
                container.appendChild(nsDiv);
            });
            
            // Add helpful examples
            const exampleDiv = document.createElement('div');
            exampleDiv.innerHTML = `
                <h4>Example Node IDs:</h4>
                <ul>
                    <li>ns=3;s="DB1".Temperature</li>
                    <li>ns=3;s="DataBlockGlobal".Pressure</li>
                    <li>ns=4;s="PLC_1"."Program"."Static".Level</li>
                    <li>i=1234 (for numeric node IDs)</li>
                </ul>
            `;
            container.appendChild(exampleDiv);
            
            statusEl.textContent = `Found ${data.count} namespaces`;
            statusEl.className = 'status-message success';
        } else {
            statusEl.textContent = data.error || 'Failed to get namespaces';
            statusEl.className = 'status-message error';
        }
    } catch (error) {
        statusEl.textContent = 'Error: ' + error.message;
        statusEl.className = 'status-message error';
    }
}

// Render Simple Tree (flattened variables list)
// Render browse tree with folders and variables
function renderBrowseTree(items, currentNodeId = 'i=85') {
    const container = document.getElementById('opcua-tree');
    container.innerHTML = '';
    
    // Add navigation header if not at root
    if (currentNodeId !== 'i=85') {
        const navDiv = document.createElement('div');
        navDiv.className = 'tree-navigation';
        navDiv.style.cssText = 'margin-bottom: 10px; padding: 8px; background: #e9ecef; border-radius: 4px;';
        navDiv.innerHTML = `
            <button class="btn btn-sm" onclick="browseSimple('i=85')" title="Go to Root">
                🏠 Root
            </button>
            <span style="margin: 0 8px;">Current: ${currentNodeId}</span>
        `;
        container.appendChild(navDiv);
    }
    
    if (!items || items.length === 0) {
        const noResults = document.createElement('p');
        noResults.className = 'no-results';
        noResults.textContent = 'No items found in this folder.';
        container.appendChild(noResults);
        return;
    }
    
    // Sort items: folders first, then variables
    items.sort((a, b) => {
        if (a.type !== b.type) {
            return a.type === 'folder' ? -1 : 1;
        }
        return a.browse_name.localeCompare(b.browse_name);
    });
    
    items.forEach(item => {
        const div = document.createElement('div');
        
        if (item.type === 'folder') {
            // Folder item
            div.className = 'tree-item folder';
            div.style.cssText = `
                padding: 8px; border: 1px solid #ccc; margin: 4px 0;
                background-color: #f8f9fa; cursor: pointer;
                display: flex; justify-content: space-between; align-items: center;
            `;
            
            div.innerHTML = `
                <div>
                    <span class="folder-icon">📁</span>
                    <strong>${item.display_name}</strong>
                    <small style="color: #666;"> (${item.browse_name})</small>
                </div>
                <button class="btn btn-sm browse-folder-btn">Browse →</button>
            `;
            
            // Add click handler for browse button
            div.querySelector('.browse-folder-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                browseSimple(item.node_id);
            });
            
        } else if (item.type === 'variable') {
            // Variable item  
            div.className = 'tree-item variable';
            div.style.cssText = `
                padding: 8px; border: 1px solid #ddd; margin: 4px 0;
                background-color: #f9f9f9;
                display: flex; justify-content: space-between; align-items: center;
            `;
            
            div.innerHTML = `
                <div class="variable-info">
                    <span class="variable-icon">📊</span>
                    <strong>${item.browse_name}</strong>
                    <span class="variable-value"> = ${item.current_value || 'N/A'}</span>
                    <span class="variable-type"> (${item.data_type || 'unknown'})</span><br>
                    <small style="color: #666;">Node ID: ${item.node_id}</small>
                </div>
                <button class="btn btn-sm add-btn">Add to Monitoring</button>
            `;
            
            // Add click handler for add button
            div.querySelector('.add-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                openAddModal(item);
            });
            
        } else {
            // Other item types
            div.className = 'tree-item other';
            div.style.cssText = `
                padding: 8px; border: 1px solid #eee; margin: 4px 0;
                background-color: #fafafa; opacity: 0.7;
            `;
            
            div.innerHTML = `
                <span>⚪</span>
                <span>${item.display_name}</span>
                <small style="color: #999;"> (${item.type})</small>
            `;
        }
        
        container.appendChild(div);
    });
}

function renderSimpleTree(variables) {
    // Fallback for old API calls
    const items = variables.map(v => ({ ...v, type: 'variable' }));
    renderBrowseTree(items);
}

// Add Manual Variable
async function addManualVariable(e) {
    e.preventDefault();
    
    const data = {
        node_id: document.getElementById('manual-node-id').value.trim(),
        variable_name: document.getElementById('manual-variable-name').value.trim(),
        description: document.getElementById('manual-description').value.trim(),
        data_type: document.getElementById('manual-data-type').value,
        unit: document.getElementById('manual-unit').value.trim(),
        writable: document.getElementById('manual-writable').checked,
        store_to_db: document.getElementById('manual-store-db').checked
    };
    
    if (!data.node_id || !data.variable_name) {
        alert('Node ID and Variable Name are required');
        return;
    }
    
    try {
        const result = await API.post('/opcua/variables/add-manual', data);
        
        if (result.success) {
            alert('Variable added successfully!');
            document.getElementById('manual-variable-modal').style.display = 'none';
            document.getElementById('manual-variable-form').reset();
            await loadSelectedVariables();
            showMessage('browse-status', 'Manual variable added successfully', 'success');
        } else {
            alert('Error: ' + (result.error || 'Failed to add variable'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Helper function to show messages
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `status-message ${type}`;
    }
}

// Export functions
window.removeVariable = removeVariable;

// Initialize on page load
document.addEventListener('DOMContentLoaded', initVariablesPage);
