const CONFIG = {
    API_BASE: '/api',
    WS_ENDPOINT: (() => {
        const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
        return `${protocol}://${location.host}/flowrra/ws`;
    })(),
    POLL_INTERVAL: 15000,
};

const state = {
    socket: null,
    pollTimer: null,
    connected: false,
    tasks: new Map(), // taskId -> task data
};

/* --------------------------------------------------------
   Initialization
-------------------------------------------------------- */

function init() {
    console.log('Flowrra UI booting…');

    connectWebSocket();
    loadInitialTasks();
    setupUI();
}

/* --------------------------------------------------------
   WebSocket
-------------------------------------------------------- */

function connectWebSocket() {
    state.socket = new WebSocket(CONFIG.WS_ENDPOINT);

    state.socket.onopen = () => {
        console.log('WS connected');
        state.connected = true;
        stopPolling();
    };

    state.socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleTaskEvent(msg);
    };

    state.socket.onclose = () => {
        console.warn('WS disconnected → enabling polling');
        state.connected = false;
        startPolling();
        reconnectLater();
    };

    state.socket.onerror = () => {
        state.socket.close();
    };
}

function reconnectLater() {
    setTimeout(connectWebSocket, 3000);
}

/* --------------------------------------------------------
   Fallback polling
-------------------------------------------------------- */

function startPolling() {
    if (state.pollTimer) return;

    state.pollTimer = setInterval(async () => {
        try {
            const tasks = await apiGet('/tasks');
            syncTasks(tasks);
        } catch (e) {
            console.error('Polling failed', e);
        }
    }, CONFIG.POLL_INTERVAL);
}

function stopPolling() {
    if (!state.pollTimer) return;
    clearInterval(state.pollTimer);
    state.pollTimer = null;
}

/* --------------------------------------------------------
   API
-------------------------------------------------------- */

async function apiGet(path) {
    const res = await fetch(CONFIG.API_BASE + path);
    if (!res.ok) throw new Error(res.status);
    return res.json();
}

/* --------------------------------------------------------
   Initial Load
-------------------------------------------------------- */

async function loadInitialTasks() {
    try {
        const tasks = await apiGet('/tasks');
        syncTasks(tasks);
    } catch (e) {
        console.error('Failed to load tasks', e);
    }
}

/* --------------------------------------------------------
   Task Events
-------------------------------------------------------- */

function handleTaskEvent(event) {
    /*
      Expected:
      {
        type: "task.update" | "task.create" | "task.delete",
        task: {...}
      }
    */

    const { type, task } = event;

    if (type === 'task.delete') {
        removeTask(task.id);
        return;
    }

    updateTask(task);
}

/* --------------------------------------------------------
   State sync
-------------------------------------------------------- */

function syncTasks(taskList) {
    const seen = new Set();

    for (const task of taskList) {
        seen.add(task.id);
        updateTask(task);
    }

    // Remove tasks no longer present
    for (const id of state.tasks.keys()) {
        if (!seen.has(id)) {
            removeTask(id);
        }
    }
}

function updateTask(task) {
    state.tasks.set(task.id, task);
    renderTask(task);
}

function removeTask(id) {
    state.tasks.delete(id);
    const row = document.getElementById(`task-${id}`);
    if (row) row.remove();
}

/* --------------------------------------------------------
   Rendering
-------------------------------------------------------- */

function renderTask(task) {
    let row = document.getElementById(`task-${task.id}`);

    if (!row) {
        row = document.createElement('tr');
        row.id = `task-${task.id}`;
        document.querySelector('#tasks-body').appendChild(row);
    }

    row.innerHTML = `
        <td>${task.id}</td>
        <td>${task.name}</td>
        <td class="status ${task.status}">${task.status}</td>
        <td>${formatTime(task.started_at)}</td>
        <td>${formatDuration(task.runtime)}</td>
    `;
}

/* --------------------------------------------------------
   UI
-------------------------------------------------------- */

function setupUI() {
    const refreshBtn = document.getElementById('refresh-button');
    if (refreshBtn) {
        refreshBtn.onclick = loadInitialTasks;
    }
}

/* --------------------------------------------------------
   Utils
-------------------------------------------------------- */

function formatTime(iso) {
    if (!iso) return '-';
    return new Date(iso).toLocaleTimeString();
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${(seconds / 60).toFixed(1)}m`;
}

/* --------------------------------------------------------
   Boot
-------------------------------------------------------- */

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
