// MQTT Message Monitor JavaScript

let messageBuffer = [];
let topicStats = {};
let totalMessages = 0;
let messagesThisSecond = 0;
let isPaused = false;
let messageRateInterval = null;
const MAX_BUFFER_SIZE = 100;

// Load messages from sessionStorage
function loadMessagesFromStorage() {
    try {
        const stored = sessionStorage.getItem('mqtt_messages');
        if (stored) {
            const data = JSON.parse(stored);
            messageBuffer = data.messages.map(msg => ({
                ...msg,
                timestamp: new Date(msg.timestamp)
            }));
            topicStats = data.topicStats || {};
            totalMessages = data.totalMessages || 0;
            console.log(`Loaded ${messageBuffer.length} messages from storage`);
        }
    } catch (error) {
        console.error('Error loading messages from storage:', error);
        messageBuffer = [];
        topicStats = {};
        totalMessages = 0;
    }
}

// Save messages to sessionStorage
function saveMessagesToStorage() {
    try {
        const data = {
            messages: messageBuffer.map(msg => ({
                topic: msg.topic,
                payload: msg.payload,
                timestamp: msg.timestamp.toISOString()
            })),
            topicStats: topicStats,
            totalMessages: totalMessages
        };
        sessionStorage.setItem('mqtt_messages', JSON.stringify(data));
    } catch (error) {
        console.error('Error saving messages to storage:', error);
    }
}

// Initialize MQTT Monitor
function initMQTTMonitor() {
    console.log('Initializing MQTT Monitor...');
    
    // Load messages from storage first
    loadMessagesFromStorage();
    
    // Render loaded messages
    if (messageBuffer.length > 0) {
        renderMessages();
        updateTopicTable();
        updateStats();
    }
    
    // Load subscriptions count
    loadSubscriptions();
    
    // Set up Socket.IO listener
    if (window.socket) {
        console.log('Socket.IO available, registering mqtt_message listener');
        
        // Remove any existing listener first to avoid duplicates
        window.socket.off('mqtt_message');
        
        // Register listener
        window.socket.on('mqtt_message', handleMQTTMessage);
        
        // Check connection status
        if (window.socket.connected) {
            console.log('Socket.IO already connected');
        } else {
            console.log('Socket.IO connecting...');
            window.socket.on('connect', () => {
                console.log('Socket.IO connected - ready to receive messages');
            });
        }
    } else {
        console.error('Socket.IO not available - waiting for initialization...');
        // Retry after a short delay
        setTimeout(() => {
            if (window.socket) {
                console.log('Socket.IO now available, registering listener');
                window.socket.off('mqtt_message');
                window.socket.on('mqtt_message', handleMQTTMessage);
            } else {
                console.error('Socket.IO still not available after retry');
            }
        }, 500);
    }
    
    // Set up controls
    document.getElementById('pause-btn').addEventListener('click', togglePause);
    document.getElementById('clear-btn').addEventListener('click', clearMessages);
    document.getElementById('auto-scroll').addEventListener('change', updateAutoScroll);
    document.getElementById('show-timestamps').addEventListener('change', renderMessages);
    document.getElementById('topic-filter').addEventListener('input', renderMessages);
    
    // Start message rate counter
    messageRateInterval = setInterval(updateMessageRate, 1000);
    
    // Update stats and connection status periodically
    setInterval(updateStats, 2000);
    setInterval(() => {
        if (messageBuffer.length === 0) {
            renderMessages(); // Update connection status display
        }
    }, 1000);
}

// Handle incoming MQTT message
function handleMQTTMessage(data) {
    if (isPaused) return;
    
    const { topic, payload, timestamp } = data;
    
    // Add to buffer
    messageBuffer.unshift({
        topic,
        payload,
        timestamp: new Date(timestamp)
    });
    
    // Limit buffer size
    if (messageBuffer.length > MAX_BUFFER_SIZE) {
        messageBuffer.pop();
    }
    
    // Update topic statistics
    if (!topicStats[topic]) {
        topicStats[topic] = {
            count: 0,
            lastMessage: null,
            lastPayload: null
        };
    }
    topicStats[topic].count++;
    topicStats[topic].lastMessage = new Date(timestamp);
    topicStats[topic].lastPayload = payload;
    
    // Update counters
    totalMessages++;
    messagesThisSecond++;
    
    // Save to storage
    saveMessagesToStorage();
    
    // Update display
    renderMessages();
    updateTopicTable();
    updateStats();
}

// Render messages in the display
function renderMessages() {
    const container = document.getElementById('message-container');
    const showTimestamps = document.getElementById('show-timestamps').checked;
    const topicFilter = document.getElementById('topic-filter').value.trim();
    
    if (messageBuffer.length === 0) {
        const socketStatus = window.socket && window.socket.connected ? 
            '✓ Connected - Ready to receive messages' : 
            '⚠ Connecting...';
        
        container.innerHTML = `
            <div class="no-messages">
                <p>📡 ${isPaused ? 'Paused - Click Resume to continue' : 'Waiting for MQTT messages...'}</p>
                <p class="help-text">Socket.IO: ${socketStatus}</p>
                <p class="help-text">Subscribe to topics in <a href="/configuration">Configuration</a></p>
            </div>
        `;
        return;
    }
    
    // Filter messages
    let filteredMessages = messageBuffer;
    if (topicFilter) {
        const filterRegex = topicFilter.replace(/\+/g, '[^/]+').replace(/#/g, '.*');
        filteredMessages = messageBuffer.filter(msg => 
            new RegExp(`^${filterRegex}$`).test(msg.topic)
        );
    }
    
    // Render messages
    const html = filteredMessages.map(msg => {
        const timestampStr = showTimestamps ? 
            `<span class="message-timestamp">[${formatTime(msg.timestamp)}]</span>` : '';
        
        const payloadDisplay = formatPayload(msg.payload);
        
        return `
            <div class="message-item">
                ${timestampStr}
                <span class="message-topic">${escapeHtml(msg.topic)}</span>
                ${payloadDisplay}
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
    
    // Auto-scroll to bottom
    if (document.getElementById('auto-scroll').checked) {
        container.scrollTop = container.scrollHeight;
    }
}

// Format payload for display
function formatPayload(payload) {
    try {
        const parsed = JSON.parse(payload);
        return `<span class="message-json">${escapeHtml(JSON.stringify(parsed, null, 2))}</span>`;
    } catch {
        return `<span class="message-payload">${escapeHtml(payload)}</span>`;
    }
}

// Format time
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
    });
}

// Update topic breakdown table
function updateTopicTable() {
    const tbody = document.getElementById('topic-tbody');
    
    if (Object.keys(topicStats).length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No messages received yet</td></tr>';
        return;
    }
    
    const rows = Object.entries(topicStats)
        .sort((a, b) => b[1].count - a[1].count)
        .map(([topic, stats]) => {
            const lastTime = stats.lastMessage ? 
                new Date(stats.lastMessage).toLocaleTimeString() : 'N/A';
            const payloadPreview = stats.lastPayload ? 
                stats.lastPayload.substring(0, 50) + (stats.lastPayload.length > 50 ? '...' : '') : '';
            
            return `
                <tr>
                    <td><code>${escapeHtml(topic)}</code></td>
                    <td><span class="topic-count">${stats.count}</span></td>
                    <td>${lastTime}</td>
                    <td class="payload-preview">${escapeHtml(payloadPreview)}</td>
                </tr>
            `;
        })
        .join('');
    
    tbody.innerHTML = rows;
}

// Update statistics
function updateStats() {
    document.getElementById('total-messages').textContent = totalMessages.toLocaleString();
    document.getElementById('unique-topics').textContent = Object.keys(topicStats).length;
}

// Update message rate
function updateMessageRate() {
    document.getElementById('messages-per-sec').textContent = messagesThisSecond;
    messagesThisSecond = 0;
}

// Load active subscriptions
async function loadSubscriptions() {
    try {
        const result = await API.get('/mqtt/subscriptions');
        if (result.success) {
            document.getElementById('active-subscriptions').textContent = result.count || 0;
        }
    } catch (error) {
        console.error('Error loading subscriptions:', error);
    }
}

// Toggle pause
function togglePause() {
    isPaused = !isPaused;
    const btn = document.getElementById('pause-btn');
    if (isPaused) {
        btn.textContent = '▶️ Resume';
        btn.classList.remove('btn-warning');
        btn.classList.add('btn-success');
    } else {
        btn.textContent = '⏸️ Pause';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-warning');
    }
    renderMessages();
}

// Clear messages
function clearMessages() {
    if (confirm('Clear all messages from display?')) {
        messageBuffer = [];
        topicStats = {};
        totalMessages = 0;
        
        // Clear from storage
        sessionStorage.removeItem('mqtt_messages');
        
        renderMessages();
        updateTopicTable();
        updateStats();
    }
}

// Update auto-scroll
function updateAutoScroll() {
    renderMessages();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initMQTTMonitor);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (messageRateInterval) {
        clearInterval(messageRateInterval);
    }
});
