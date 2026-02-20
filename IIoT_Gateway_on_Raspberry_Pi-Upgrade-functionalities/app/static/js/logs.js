// Logs Page JavaScript

let autoScroll = true;

// Initialize Logs Page
function initLogsPage() {
    document.getElementById('refresh-logs-btn').addEventListener('click', loadLogs);
    document.getElementById('clear-logs-btn').addEventListener('click', clearLogs);
    document.getElementById('auto-scroll').addEventListener('change', (e) => {
        autoScroll = e.target.checked;
    });
    
    // Load initial logs
    loadLogs();
    
    // Auto-refresh every 10 seconds
    setInterval(loadLogs, 10000);
}

// Load Logs (simulated - in production, would read from log file via API)
async function loadLogs() {
    const container = document.getElementById('log-container');
    
    try {
        // In production, this would call an API endpoint that reads the log file
        // For now, we'll show a placeholder
        const logs = [
            `[${new Date().toISOString()}] INFO - System startup`,
            `[${new Date().toISOString()}] INFO - MQTT client connected`,
            `[${new Date().toISOString()}] INFO - OPC UA server started`,
            `[${new Date().toISOString()}] INFO - OPC UA client connected to S7-1500`,
            `[${new Date().toISOString()}] INFO - Monitoring 5 variables`,
        ];
        
        container.innerHTML = logs.map(log => `<div>${log}</div>`).join('');
        
        if (autoScroll) {
            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        container.innerHTML = '<div style="color: #e74c3c;">Error loading logs: ' + error.message + '</div>';
    }
}

// Clear Logs Display
function clearLogs() {
    document.getElementById('log-container').innerHTML = '';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initLogsPage);
