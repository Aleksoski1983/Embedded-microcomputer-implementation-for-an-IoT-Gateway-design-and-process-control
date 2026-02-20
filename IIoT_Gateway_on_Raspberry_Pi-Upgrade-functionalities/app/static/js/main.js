// Main JavaScript - Common Functions

// API Helper
const API = {
    async get(endpoint) {
        const response = await fetch(`/api${endpoint}`);
        if (!response.ok) {
            // Try to parse JSON error, fallback to text
            let errorMessage;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || 'Request failed';
            } catch (e) {
                errorMessage = await response.text() || `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        return response.json();
    },
    
    async post(endpoint, data) {
        const response = await fetch(`/api${endpoint}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            // Try to parse JSON error, fallback to text
            let errorMessage;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || 'Request failed';
            } catch (e) {
                errorMessage = await response.text() || `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        return response.json();
    },
    
    async delete(endpoint) {
        const response = await fetch(`/api${endpoint}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            // Try to parse JSON error, fallback to text
            let errorMessage;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || 'Request failed';
            } catch (e) {
                errorMessage = await response.text() || `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        return response.json();
    }
};

// Status Updater
function updateStatus(elementId, isConnected, statusText = null) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const dot = element.querySelector('.status-dot');
    const text = element.querySelector('.status-text');
    
    if (dot) {
        dot.classList.remove('online', 'offline');
        dot.classList.add(isConnected ? 'online' : 'offline');
    }
    
    if (text && statusText) {
        text.textContent = statusText;
    }
}

// Show message
function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = message;
    element.className = `status-message ${type}`;
    
    setTimeout(() => {
        element.textContent = '';
        element.className = 'status-message';
    }, 5000);
}

// Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Initialize Socket.IO
function initSocketIO() {
    // Check if already initialized
    if (window.socket && window.socket.connected) {
        console.log('Socket.IO already connected');
        return window.socket;
    }
    
    console.log('Initializing Socket.IO...');
    const socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity
    });
    
    socket.on('connect', () => {
        console.log('Socket.IO connected, ID:', socket.id);
    });
    
    socket.on('disconnect', (reason) => {
        console.log('Socket.IO disconnected:', reason);
    });
    
    socket.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error);
    });
    
    socket.on('reconnect', (attemptNumber) => {
        console.log('Socket.IO reconnected after', attemptNumber, 'attempts');
    });
    
    return socket;
}

// Auto-initialize Socket.IO on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Socket.IO...');
    window.socket = initSocketIO();
});

// Export functions
window.API = API;
window.updateStatus = updateStatus;
window.showMessage = showMessage;
window.formatTimestamp = formatTimestamp;
window.initSocketIO = initSocketIO;
