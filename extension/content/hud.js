// Antigravity Retina HUD Module
// In-Page Command Deck with real-time logs and attack controls

(function () {
    'use strict';

    // ========================================================================
    // HUD CONFIGURATION
    // ========================================================================

    const WS_ENDPOINT = 'ws://127.0.0.1:8000/stream?client_type=hud';
    const API_ENDPOINT = 'http://127.0.0.1:8000';

    let ws = null;
    let isMinimized = false;
    let logCount = 0;

    // ========================================================================
    // HUD HTML TEMPLATE
    // ========================================================================

    const HUD_HTML = `
        <div id="antigravity-hud" class="hud-container">
            <div class="hud-header">
                <div class="hud-title">
                    <span class="hud-icon">🛸</span>
                    <span>ANTIGRAVITY HUD</span>
                    <span class="hud-status" id="hud-connection-status">●</span>
                </div>
                <div class="hud-controls">
                    <button id="hud-minimize" title="Minimize">_</button>
                    <button id="hud-close" title="Close">×</button>
                </div>
            </div>
            <div class="hud-body" id="hud-body">
                <div class="hud-section">
                    <div class="hud-section-header">
                        <span>📡 LIVE FEED</span>
                        <span class="hud-badge" id="hud-log-count">0</span>
                    </div>
                    <div class="hud-log" id="hud-log"></div>
                </div>
                
                <div class="hud-section">
                    <div class="hud-section-header">🤖 AGENT OMEGA</div>
                    <div class="hud-chat" id="hud-chat">
                        <div class="chat-message agent">Awaiting target acquisition...</div>
                    </div>
                </div>
                
                <div class="hud-actions">
                    <button class="hud-btn primary" id="hud-scan-page">
                        <span>⚡</span> Scan Page
                    </button>
                    <button class="hud-btn secondary" id="hud-fuzz-inputs">
                        <span>🔥</span> Fuzz Inputs
                    </button>
                    <button class="hud-btn danger" id="hud-full-attack">
                        <span>💀</span> Full Attack
                    </button>
                </div>
                
                <div class="hud-info">
                    <span id="hud-target">${window.location.hostname}</span>
                </div>
            </div>
        </div>
    `;

    // ========================================================================
    // HUD INJECTION
    // ========================================================================

    function injectHUD() {
        // Don't inject on our own UI or extension pages
        if (window.location.hostname === '127.0.0.1' ||
            window.location.hostname === 'localhost' ||
            window.location.protocol === 'chrome-extension:') {
            return;
        }

        // Check if already injected
        if (document.getElementById('antigravity-hud')) return;

        const container = document.createElement('div');
        container.innerHTML = HUD_HTML;
        document.body.appendChild(container.firstElementChild);

        // Bind events
        bindHUDEvents();

        // Connect WebSocket
        connectWebSocket();

        console.log('[RETINA HUD] Injected successfully');
    }

    // ========================================================================
    // EVENT BINDINGS
    // ========================================================================

    function bindHUDEvents() {
        // Minimize
        document.getElementById('hud-minimize').addEventListener('click', () => {
            const body = document.getElementById('hud-body');
            isMinimized = !isMinimized;
            body.style.display = isMinimized ? 'none' : 'block';
            document.getElementById('hud-minimize').textContent = isMinimized ? '□' : '_';
        });

        // Close
        document.getElementById('hud-close').addEventListener('click', () => {
            const hud = document.getElementById('antigravity-hud');
            if (hud) hud.remove();
        });

        // Scan Page
        document.getElementById('hud-scan-page').addEventListener('click', async () => {
            addLog('INFO', 'Initiating page scan...');
            addChatMessage('agent', 'Scanning current page for vulnerabilities...');

            chrome.runtime.sendMessage({
                type: "FORWARD_REQ",
                payload: {
                    endpoint: `${API_ENDPOINT}/api/attack/fire`,
                    body: {
                        url: window.location.href,
                        mode: 'quick',
                        modules: ['xray']
                    }
                }
            }, (response) => {
                if (response && response.success) {
                    addLog('SUCCESS', 'Scan initiated!');
                    addChatMessage('agent', 'Scan queued. Monitoring for anomalies...');
                } else {
                    addLog('ERROR', 'Backend unreachable');
                }
            });
        });

        // Fuzz Inputs
        document.getElementById('hud-fuzz-inputs').addEventListener('click', () => {
            addLog('INFO', 'Fuzzing input fields...');

            const inputs = document.querySelectorAll('input, textarea');
            let fuzzed = 0;

            inputs.forEach(input => {
                if (input.type !== 'hidden' && input.type !== 'submit') {
                    input.style.border = '2px solid #ff6600';
                    input.value = "' OR 1=1 --";
                    fuzzed++;
                }
            });

            addLog('SUCCESS', `Fuzzed ${fuzzed} input fields`);
            addChatMessage('agent', `Injected test payloads into ${fuzzed} fields. Submit forms to test.`);
        });

        // Full Attack
        document.getElementById('hud-full-attack').addEventListener('click', async () => {
            addLog('CRITICAL', 'FULL ATTACK MODE ENGAGED');
            addChatMessage('agent', '☠️ Deploying all attack vectors...');

            chrome.runtime.sendMessage({
                type: "FORWARD_REQ",
                payload: {
                    endpoint: `${API_ENDPOINT}/api/attack/fire`,
                    body: {
                        url: window.location.href,
                        mode: 'elite',
                        modules: ['chronomancer', 'doppelganger', 'full']
                    }
                }
            }, (response) => {
                if (response && response.success) {
                    addLog('SUCCESS', 'Full attack deployed');
                } else {
                    addLog('ERROR', 'Attack failed');
                }
            });
        });

        // Make HUD draggable
        makeDraggable(document.getElementById('antigravity-hud'));
    }

    // ========================================================================
    // WEBSOCKET CONNECTION
    // ========================================================================

    function connectWebSocket() {
        try {
            ws = new WebSocket(WS_ENDPOINT);

            ws.onopen = () => {
                updateConnectionStatus(true);
                addLog('SYSTEM', 'Connected to Hive Mind');
            };

            ws.onclose = () => {
                updateConnectionStatus(false);
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = () => {
                updateConnectionStatus(false);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleWSMessage(data);
                } catch (e) {
                    console.error('[HUD] Parse error:', e);
                }
            };
        } catch (e) {
            updateConnectionStatus(false);
        }
    }

    function handleWSMessage(data) {
        const type = data.type || 'INFO';
        const payload = data.payload || data;

        switch (type) {
            case 'VULN_CONFIRMED':
                addLog('CRITICAL', `Vulnerability: ${payload.type || 'Unknown'}`);
                addChatMessage('agent', `🔴 BREACH DETECTED: ${payload.type}`);
                break;
            case 'SCAN_PROGRESS':
                addLog('INFO', `Progress: ${payload.progress || 0}%`);
                break;
            case 'AGENT_MESSAGE':
                addChatMessage('agent', payload.message || payload);
                break;
            default:
                addLog('INFO', JSON.stringify(payload).substring(0, 80));
        }
    }

    // ========================================================================
    // UI HELPERS
    // ========================================================================

    function addLog(level, message) {
        const logEl = document.getElementById('hud-log');
        if (!logEl) return;

        const entry = document.createElement('div');
        entry.className = `log-entry log-${level.toLowerCase()}`;
        entry.innerHTML = `<span class="log-time">${new Date().toLocaleTimeString()}</span> <span class="log-level">[${level}]</span> ${message}`;

        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;

        // Update count
        logCount++;
        const countEl = document.getElementById('hud-log-count');
        if (countEl) countEl.textContent = logCount;

        // Limit log entries
        while (logEl.children.length > 50) {
            logEl.removeChild(logEl.firstChild);
        }
    }

    function addChatMessage(sender, message) {
        const chatEl = document.getElementById('hud-chat');
        if (!chatEl) return;

        const msg = document.createElement('div');
        msg.className = `chat-message ${sender}`;
        msg.textContent = message;

        chatEl.appendChild(msg);
        chatEl.scrollTop = chatEl.scrollHeight;
    }

    function updateConnectionStatus(connected) {
        const statusEl = document.getElementById('hud-connection-status');
        if (statusEl) {
            statusEl.style.color = connected ? '#00ff88' : '#ff0040';
            statusEl.title = connected ? 'Connected' : 'Disconnected';
        }
    }

    function makeDraggable(element) {
        const header = element.querySelector('.hud-header');
        let isDragging = false;
        let offsetX, offsetY;

        header.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON') return;
            isDragging = true;
            offsetX = e.clientX - element.offsetLeft;
            offsetY = e.clientY - element.offsetTop;
            element.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            element.style.left = (e.clientX - offsetX) + 'px';
            element.style.top = (e.clientY - offsetY) + 'px';
            element.style.right = 'auto';
            element.style.bottom = 'auto';
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            element.style.cursor = 'default';
        });
    }

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    if (document.readyState === 'complete') {
        injectHUD();
    } else {
        window.addEventListener('load', injectHUD);
    }

})();
