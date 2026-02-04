// State
let settings = {};
let wsReconnectAttempts = 0;
let lastMessageTime = Date.now();

// DOM Elements
const connectBtn = document.getElementById('connectBtn');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const squareOffAllBtn = document.getElementById('squareOffAllBtn');
const statusDot = document.getElementById('statusDot');
const connectionStatus = document.getElementById('connectionStatus');
const activeLaddersTable = document.getElementById('activeLaddersBody');
const globalPnlEl = document.getElementById('globalPnl');

// Helper
const getVal = (id) => document.getElementById(id).value;
const setVal = (id, val) => document.getElementById(id).value = val;

// API Interaction
async function connectDhan() {
    const payload = {
        client_id: getVal('clientId'),
        access_token: getVal('accessToken'),
    };

    // Gather all settings
    updateSettingsFromUI(payload);

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            addLog('✅ Connected to Dhan API');
            updateStatus(true);
        } else {
            addLog('❌ Connection Failed: ' + data.message);
            updateStatus(false);
        }
    } catch (e) {
        console.error(e);
        addLog('❌ API Error: ' + e.message);
    }
}

async function startStrategy() {
    try {
        const res = await fetch('/api/start', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            addLog('▶️ ' + data.message);
        } else {
            addLog('❌ ' + (data.message || data.status));
        }
    } catch (e) {
        addLog('❌ Start failed: ' + e.message);
    }
}

async function stopStrategy() {
    try {
        const res = await fetch('/api/stop', { method: 'POST' });
        const data = await res.json();
        addLog('⏹️ ' + data.status);
    } catch (e) {
        addLog('❌ Stop failed: ' + e.message);
    }
}

async function saveSettings() {
    try {
        const payload = {};
        updateSettingsFromUI(payload);

        console.log('[DEBUG] Saving settings:', payload);

        // Save to localStorage
        localStorage.setItem('ladder_settings', JSON.stringify(payload));
        console.log('✓ Saved to localStorage');

        // Send to backend
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        console.log('Backend response:', data);

        if (data.status === 'success') {
            addLog('💾 ' + data.message);
            // If Dhan connected, update status
            if (data.message.includes('Dhan connected')) {
                updateStatus(true);
            }
        } else if (data.status === 'error') {
            addLog('❌ ' + data.message);
        }
    } catch (e) {
        console.error('Save error:', e);
        addLog('❌ Save failed: ' + e.message);
    }
}

async function squareOffAll() {
    if (!confirm('⚠️ WARNING: This will close ALL positions immediately. Continue?')) {
        return;
    }

    try {
        const res = await fetch('/api/square-off-all', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            addLog('⚠️ Emergency Square-off: ' + data.message);
        } else {
            addLog('❌ Square-off failed: ' + data.message);
        }
    } catch (e) {
        addLog('❌ Square-off error: ' + e.message);
    }
}

async function closePosition(symbol) {
    if (!confirm(`Close position for ${symbol}?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/close-position/${symbol}`, { method: 'POST' });
        const data = await res.json();
        addLog(`📊 ${data.message}`);
    } catch (e) {
        addLog(`❌ Close failed: ${e.message}`);
    }
}

function updateSettingsFromUI(obj) {
    // Collect credentials (if present)
    const clientId = getVal('clientId');
    const accessToken = getVal('accessToken');

    // Only include if not placeholder text
    if (clientId && clientId !== 'Dhan Client ID' && clientId.trim() !== '') {
        obj.client_id = clientId;
    }
    if (accessToken && accessToken !== 'Access Token' && accessToken.trim() !== '') {
        obj.access_token = accessToken;
    }

    // Collect all strategy settings
    obj.no_of_add_ons = parseInt(getVal('noAddOns'));
    obj.add_on_percentage = parseFloat(getVal('addOnPct'));
    obj.initial_stop_loss_pct = parseFloat(getVal('initSLPct'));
    obj.trailing_stop_loss_pct = parseFloat(getVal('tslPct'));
    obj.target_percentage = parseFloat(getVal('targetPct'));
    obj.trade_capital = parseFloat(getVal('capital'));
    obj.profit_target_per_stock = parseFloat(getVal('stockProfitTarget'));
    obj.loss_limit_per_stock = parseFloat(getVal('stockLossLimit'));
    obj.top_n_gainers = parseInt(getVal('topGainers') || 5);
    obj.top_n_losers = parseInt(getVal('topLosers') || 5);
    obj.min_turnover_crores = parseFloat(getVal('minTurnover') || 1.0);
    return obj;
}

function loadSettingsFromLocalStorage() {
    try {
        const saved = localStorage.getItem('ladder_settings');
        console.log('[DEBUG] localStorage raw:', saved);

        if (saved) {
            const settings = JSON.parse(saved);
            console.log('[DEBUG] Parsed settings:', settings);

            // Populate form fields - check !== undefined to handle 0 values
            if (settings.no_of_add_ons !== undefined) {
                setVal('noAddOns', settings.no_of_add_ons);
                console.log('[DEBUG] Set noAddOns:', settings.no_of_add_ons);
            }
            if (settings.add_on_percentage !== undefined) setVal('addOnPct', settings.add_on_percentage);
            if (settings.initial_stop_loss_pct !== undefined) setVal('initSLPct', settings.initial_stop_loss_pct);
            if (settings.trailing_stop_loss_pct !== undefined) setVal('tslPct', settings.trailing_stop_loss_pct);
            if (settings.target_percentage !== undefined) setVal('targetPct', settings.target_percentage);
            if (settings.trade_capital !== undefined) setVal('capital', settings.trade_capital);
            if (settings.profit_target_per_stock !== undefined) setVal('stockProfitTarget', settings.profit_target_per_stock);
            if (settings.loss_limit_per_stock !== undefined) setVal('stockLossLimit', settings.loss_limit_per_stock);
            if (settings.top_n_gainers !== undefined) setVal('topGainers', settings.top_n_gainers);
            if (settings.top_n_losers !== undefined) setVal('topLosers', settings.top_n_losers);
            if (settings.min_turnover_crores !== undefined) setVal('minTurnover', settings.min_turnover_crores);

            console.log('[DEBUG] Settings loaded successfully');
            addLog('📋 Settings loaded from local storage');
        } else {
            console.log('[DEBUG] No saved settings in localStorage');
        }
    } catch (e) {
        console.error('[ERROR] Failed to load settings:', e);
        addLog('⚠️ Failed to load saved settings');
    }
}

function updateStatus(connected) {
    if (connected) {
        statusDot.classList.add('connected');
        connectionStatus.textContent = "Dhan Connected";
    } else {
        statusDot.classList.remove('connected');
        connectionStatus.textContent = "Disconnected";
    }
}

function addLog(message) {
    const logsContainer = document.getElementById('logsContainer');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('p');
    logEntry.textContent = `[${timestamp}] ${message}`;
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function formatCurrency(value) {
    return '₹' + value.toFixed(2);
}

function formatPercent(value) {
    return value.toFixed(2) + '%';
}

function getPercentColor(value) {
    if (value > 0) return '#10b981';
    if (value < 0) return '#ef4444';
    return '#94a3b8';
}

function formatTurnover(value) {
    return (value / 10000000).toFixed(2) + ' Cr';
}

// WebSocket with reconnection
let ws;
let wsReconnectTimer;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = function () {
        wsReconnectAttempts = 0;
        addLog('🔌 WebSocket Connected');
        if (wsReconnectTimer) {
            clearTimeout(wsReconnectTimer);
        }
    };

    ws.onmessage = function (event) {
        lastMessageTime = Date.now();
        const data = JSON.parse(event.data);

        // Update Global Stats
        globalPnlEl.textContent = formatCurrency(data.global_pnl);
        globalPnlEl.className = data.global_pnl >= 0 ? 'stat-value pnl-green' : 'stat-value pnl-red';

        updateStatus(data.dhan_connected);

        // Update stock counts
        const activeCount = data.active_stocks.filter(s => s.mode !== 'NONE').length;
        document.getElementById('activeLadders').textContent = activeCount;
        document.getElementById('totalStocks').textContent = data.active_stocks.length;

        // Update performance metrics
        if (data.performance && data.performance.tick_stats) {
            const tickStats = data.performance.tick_stats;
            const orderStats = data.performance.order_stats;
            const systemStats = data.performance.system_stats;

            document.getElementById('tickLatency').textContent = tickStats.avg_latency_ms.toFixed(2) + 'ms';
            document.getElementById('orderLatency').textContent = orderStats.avg_latency_ms.toFixed(2) + 'ms';
            document.getElementById('tickRate').textContent = tickStats.tick_rate.toFixed(0) + '/s';
            document.getElementById('cpuUsage').textContent = systemStats.cpu_percent.toFixed(1) + '%';
            document.getElementById('memoryUsage').textContent = systemStats.memory_mb.toFixed(1) + 'MB';
            document.getElementById('latency').textContent = tickStats.avg_latency_ms.toFixed(1);
        }

        // Render Table with document fragment for performance
        const fragment = document.createDocumentFragment();

        data.active_stocks.forEach(stock => {
            // SHOW ALL STOCKS - including IDLE ones so user can see live data
            // Comment this out to see all stocks:
            // if (stock.mode === 'NONE' && stock.status === 'IDLE') {
            //     return; // Skip idle stocks
            // }

            const row = document.createElement('tr');

            // Add glow effect for active positions
            if (stock.mode !== 'NONE') {
                row.classList.add('active-position');
            }

            const changeColor = getPercentColor(stock.change_pct);
            const pnlColor = stock.pnl >= 0 ? '#10b981' : '#ef4444';

            row.innerHTML = `
                <td><strong>${stock.symbol}</strong></td>
                <td><span class="badge ${stock.mode === 'LONG' ? 'badge-long' : stock.mode === 'SHORT' ? 'badge-short' : 'badge-none'}">${stock.mode}</span></td>
                <td>${formatCurrency(stock.ltp)}</td>
                <td style="color: ${changeColor}; font-weight: 600;">${formatPercent(stock.change_pct)}</td>
                <td style="color: ${pnlColor}; font-weight: 600;">${formatCurrency(stock.pnl)}</td>
                <td>${stock.quantity}</td>
                <td>${stock.ladder_level}</td>
                <td>${formatCurrency(stock.avg_entry_price)}</td>
                <td>${formatCurrency(stock.stop_loss)}</td>
                <td>${formatCurrency(stock.target)}</td>
                <td>${formatTurnover(stock.turnover)}</td>
                <td><span class="status-badge status-${stock.status.toLowerCase()}">${stock.status}</span></td>
                <td>
                    ${stock.mode !== 'NONE' ?
                    `<button class="btn-small btn-danger" onclick="closePosition('${stock.symbol}')">Close</button>` :
                    '-'}
                </td>
            `;
            fragment.appendChild(row);
        });

        activeLaddersTable.innerHTML = '';
        activeLaddersTable.appendChild(fragment);
    };

    ws.onerror = function (error) {
        console.error('WebSocket error:', error);
        addLog('❌ WebSocket error');
    };

    ws.onclose = function () {
        addLog('🔌 WebSocket closed - Reconnecting...');
        attemptReconnect();
    };
}

function attemptReconnect() {
    wsReconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000); // Max 30s

    wsReconnectTimer = setTimeout(() => {
        addLog(`🔄 Reconnecting (attempt ${wsReconnectAttempts})...`);
        connectWebSocket();
    }, delay);
}

// Heartbeat to detect connection issues
setInterval(() => {
    const timeSinceLastMessage = Date.now() - lastMessageTime;
    if (timeSinceLastMessage > 5000 && ws && ws.readyState === WebSocket.OPEN) {
        // No message for 5 seconds, connection might be stale
        ws.close();
    }
}, 5000);

// Listeners
connectBtn.onclick = connectDhan;
saveSettingsBtn.onclick = saveSettings;
startBtn.onclick = startStrategy;
stopBtn.onclick = stopStrategy;
squareOffAllBtn.onclick = squareOffAll;

// Initialize: Load settings and connect WebSocket
console.log('[DEBUG] Initializing app...');
loadSettingsFromLocalStorage();
connectWebSocket();

// Periodic health check
setInterval(async () => {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        // Could update UI based on health status
    } catch (e) {
        console.error('Health check failed:', e);
    }
}, 30000); // Every 30 seconds
