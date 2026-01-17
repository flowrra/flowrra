/**
 * Flowrra UI JavaScript
 *
 * Provides interactivity for the Flowrra web interface:
 * - Auto-refresh for live updates
 * - API interaction helpers
 * - Dynamic UI updates
 */

const CONFIG = {
    AUTO_REFRESH_INTERVAL: 30000, // 30 seconds
    API_BASE_URL: '', // Relative to current URL
};

const state = {
    autoRefreshEnabled: false,
    refreshTimer: null,
};

/**
 * Initialize the application
 */
function init() {
    console.log('Flowrra UI initialized');

    // Add event listeners
    setupEventListeners();

    // Start auto-refresh if on dashboard
    if (window.location.pathname.endsWith('/') || window.location.pathname.endsWith('/dashboard')) {
        enableAutoRefresh();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Auto-refresh toggle (if button exists)
    const refreshToggle = document.getElementById('auto-refresh-toggle');
    if (refreshToggle) {
        refreshToggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                enableAutoRefresh();
            } else {
                disableAutoRefresh();
            }
        });
    }

    // Manual refresh button
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            refreshPage();
        });
    }
}

/**
 * Enable auto-refresh
 */
function enableAutoRefresh() {
    if (state.autoRefreshEnabled) return;

    state.autoRefreshEnabled = true;
    state.refreshTimer = setInterval(() => {
        refreshPage();
    }, CONFIG.AUTO_REFRESH_INTERVAL);

    console.log('Auto-refresh enabled');
}

/**
 * Disable auto-refresh
 */
function disableAutoRefresh() {
    if (!state.autoRefreshEnabled) return;

    state.autoRefreshEnabled = false;
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
        state.refreshTimer = null;
    }

    console.log('Auto-refresh disabled');
}

/**
 * Refresh the current page
 */
function refreshPage() {
    console.log('Refreshing page...');
    window.location.reload();
}

/**
 * Fetch data from API endpoint
 * @param {string} endpoint - API endpoint path
 * @returns {Promise<Object>} - JSON response
 */
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + endpoint);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API fetch error:', error);
        throw error;
    }
}

/**
 * Post data to API endpoint
 * @param {string} endpoint - API endpoint path
 * @param {Object} data - Data to send
 * @returns {Promise<Object>} - JSON response
 */
async function postAPI(endpoint, data) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API post error:', error);
        throw error;
    }
}

/**
 * Update data to API endpoint
 * @param {string} endpoint - API endpoint path
 * @param {Object} data - Data to send
 * @returns {Promise<Object>} - JSON response
 */
async function putAPI(endpoint, data) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + endpoint, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data || {}),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API put error:', error);
        throw error;
    }
}

/**
 * Delete from API endpoint
 * @param {string} endpoint - API endpoint path
 * @returns {Promise<Object>} - JSON response
 */
async function deleteAPI(endpoint) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + endpoint, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API delete error:', error);
        throw error;
    }
}

/**
 * Format datetime for display
 * @param {string} isoString - ISO datetime string
 * @returns {string} - Formatted datetime
 */
function formatDatetime(isoString) {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString();
}

/**
 * Format duration in seconds to human readable
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted duration
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
        const minutes = seconds / 60;
        return `${minutes.toFixed(1)}m`;
    } else {
        const hours = seconds / 3600;
        return `${hours.toFixed(1)}h`;
    }
}

/**
 * Get status color class
 * @param {string} status - Task status
 * @returns {string} - CSS class name
 */
function getStatusColor(status) {
    const colors = {
        'pending': 'yellow',
        'running': 'blue',
        'success': 'green',
        'failed': 'red',
    };
    return colors[status.toLowerCase()] || 'gray';
}

/**
 * Show notification
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, info)
 */
function showNotification(message, type = 'info') {
    // Simple console notification for now
    // Can be enhanced with a UI notification component
    console.log(`[${type.toUpperCase()}] ${message}`);

    // You could implement a toast notification here
    alert(message);
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success');
    } catch (error) {
        console.error('Failed to copy:', error);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export functions for use in inline scripts
window.FlowrraUI = {
    fetchAPI,
    postAPI,
    putAPI,
    deleteAPI,
    formatDatetime,
    formatDuration,
    getStatusColor,
    showNotification,
    copyToClipboard,
    enableAutoRefresh,
    disableAutoRefresh,
};
