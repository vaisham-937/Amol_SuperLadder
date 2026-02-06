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
function backendHint() {
    if (window.location.protocol === 'file:' || !window.location.host) {
        return "Backend not running. Open http://localhost:8000 (don't open index.html directly).";
    }
    return 'Backend not reachable. Start server: python -m uvicorn main:app --reload --port 8000';
}

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
        if ((e.message || '').toLowerCase().includes('failed to fetch')) {
            addLog('⚠️ ' + backendHint());
        }
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
        if ((e.message || '').toLowerCase().includes('failed to fetch')) {
            addLog('⚠️ ' + backendHint());
        }
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
        if ((e.message || '').toLowerCase().includes('failed to fetch')) {
            addLog('⚠️ ' + backendHint());
        }
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
    obj.max_ladder_stocks = Math.max(1, parseInt(getVal('maxLadderStocks') || 20));
    obj.profit_target_per_stock = parseFloat(getVal('stockProfitTarget'));
    obj.loss_limit_per_stock = parseFloat(getVal('stockLossLimit'));
    obj.top_n_gainers = parseInt(getVal('topGainers') || 5);
    obj.top_n_losers = parseInt(getVal('topLosers') || 5);
    obj.min_turnover_crores = parseFloat(getVal('minTurnover') || 1.0);

    // Enforce: top_n_gainers + top_n_losers <= max_ladder_stocks
    const maxLadders = Number.isFinite(obj.max_ladder_stocks) ? obj.max_ladder_stocks : 1;
        const g = Math.max(0, obj.top_n_gainers || 0);
        const l = Math.max(0, obj.top_n_losers || 0);
        if (g + l > maxLadders) {
            const adjustedLosers = Math.max(0, maxLadders - g);
            obj.top_n_losers = adjustedLosers;
            setVal('topLosers', adjustedLosers);
            addLog(`⚠️ Adjusted Top N Losers to ${adjustedLosers} (Max Ladder Stocks=${maxLadders})`);
        }
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
            if (settings.max_ladder_stocks !== undefined) setVal('maxLadderStocks', settings.max_ladder_stocks);
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

    // Keep DOM light for smooth scrolling
    while (logsContainer.childElementCount > 200) {
        logsContainer.removeChild(logsContainer.firstChild);
    }
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
let lastTopMoversFetch = 0;
let marketOpenState = null;

async function fetchTopMovers() {
    const now = Date.now();
    if (now - lastTopMoversFetch < 30000) {
        return;
    }
    lastTopMoversFetch = now;

    try {
        const res = await fetch('/api/top-movers');
        const data = await res.json();
        if (data.status !== 'success') {
            return;
        }

        const gainers = (data.gainers || [])
            .map(s => `${s.symbol} ${formatPercent(s.change_pct)}`)
            .slice(0, 5)
            .join(', ');
        const losers = (data.losers || [])
            .map(s => `${s.symbol} ${formatPercent(s.change_pct)}`)
            .slice(0, 5)
            .join(', ');

        const gainersEl = document.getElementById('topGainersApi');
        const losersEl = document.getElementById('topLosersApi');
        if (gainersEl) gainersEl.textContent = gainers || '-';
        if (losersEl) losersEl.textContent = losers || '-';
    } catch (e) {
        console.error('Top movers fetch failed:', e);
    }
}

function connectWebSocket() {
    if (window.location.protocol === 'file:' || !window.location.host) {
        addLog('⚠️ ' + backendHint());
        return;
    }
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

        const positions = data.positions || data.active_stocks || [];
        const activeCount = Number.isFinite(data.active_positions) ? data.active_positions : positions.length;
        const totalStocks = Number.isFinite(data.total_stocks) ? data.total_stocks : positions.length;
        document.getElementById('activeLadders').textContent = activeCount;
        document.getElementById('totalStocks').textContent = totalStocks;

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

        // When market is closed, fetch top movers via REST
        marketOpenState = data.market_open;
        if (data.market_open === false) {
            fetchTopMovers();
        }

        // Render Table with document fragment for performance
        const fragment = document.createDocumentFragment();

        positions.forEach(stock => {
            // Default: skip idle rows for smooth UI (backend usually doesn't send them)
            if (stock.mode === 'NONE' && stock.status === 'IDLE') {
                return;
            }

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

// Apply saved settings to backend on refresh (so Start uses same config)
try {
    const saved = localStorage.getItem('ladder_settings');
    if (saved) {
        let body = saved;
        // Don't send credentials on refresh; backend preserves them if already connected.
        try {
            const parsed = JSON.parse(saved);
            delete parsed.client_id;
            delete parsed.access_token;
            body = JSON.stringify(parsed);
        } catch (e) { }

        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body
        }).catch(() => { });
    }
} catch (e) { }

connectWebSocket();

// Periodic health check
setInterval(async () => {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (typeof data.market_open === 'boolean') {
            marketOpenState = data.market_open;
        }
    } catch (e) {
        console.error('Health check failed:', e);
    }
}, 30000); // Every 30 seconds

// Periodic top movers refresh (closed market or no ticks)
setInterval(() => {
    if (marketOpenState === false) {
        fetchTopMovers();
    }
}, 60000);
