class AnywhereInputClient {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.pingInterval = null;
        this.screenEnabled = true;
        this.sensitivity = 1.5;
        this.tapToClick = true;
        this.longPressRightClick = true;
        this.showFps = false;
        this.lastFrameTime = 0;
        this.frameCount = 0;
        this.fps = 0;

        // Touchpad state
        this.touchStart = { x: 0, y: 0, time: 0 };
        this.touchLast = { x: 0, y: 0 };
        this.isDragging = false;
        this.longPressTimer = null;
        this.longPressDuration = 600;
        this.moveBuffer = { dx: 0, dy: 0 };
        this.moveTimer = null;
        this.moveInterval = 16;

        // Screen dimensions
        this.screenWidth = 1920;
        this.screenHeight = 1080;
        this.monitors = [];

        // Paint mode from reference
        this.touchpadMode = "mouse";
        this.isPainting = false;
        this.lastKeyboardValue = "";

        this.init();
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.loadSettings();
        this.autoFillFromURL();
    }

    bindElements() {
        this.els = {
            loginScreen: document.getElementById('login-screen'),
            controlScreen: document.getElementById('control-screen'),
            connectForm: document.getElementById('connect-form'),
            serverUrl: document.getElementById('server-url'),
            accessToken: document.getElementById('access-token'),
            statusDot: document.getElementById('status-dot'),
            statusText: document.getElementById('status-text'),
            screenStream: document.getElementById('screen-stream'),
            fpsCounter: document.getElementById('fps-counter'),
            streamOverlay: document.getElementById('stream-overlay'),
            touchpad: document.getElementById('touchpad'),
            touchpadHint: document.getElementById('touchpad-hint'),
            keyboardModal: document.getElementById('keyboard-modal'),
            keyboardInput: document.getElementById('keyboard-input'),
            settingsPanel: document.getElementById('settings-panel'),
            connectionStatus: document.getElementById('connection-status'),
            monitorSelect: document.getElementById('setting-monitor'),
            monitorSetting: document.getElementById('monitor-setting'),
            modeBadge: document.getElementById('stream-mode'),
            modeSelector: document.getElementById('mode-selector'),
        };
        // Validate all elements are found
        for (const key in this.els) {
            if (!this.els[key]) console.warn(`Element not found: ${key}`);
        }
    }

    autoFillFromURL() {
        const params = new URLSearchParams(window.location.search);
        const queryToken = params.get("token");
        const queryHost = params.get("host");

        // Auto-fill server URL: priority to query param, then current origin
        if (queryHost) {
            this.els.serverUrl.value = queryHost;
        } else if (window.location.protocol.startsWith("http")) {
            this.els.serverUrl.value = window.location.origin;
        } else if (window.location.hostname) {
            this.els.serverUrl.value = window.location.hostname;
        }

        // Auto-fill token from URL params
        if (queryToken) {
            this.els.accessToken.value = queryToken;
        } else if (window.location.protocol.startsWith("http")) {
            // Try to fetch token from server if not in URL
            this.fetchTokenFromServer();
        }

        // Auto-connect if both URL and token are available
        if (this.els.serverUrl.value && this.els.accessToken.value) {
            setTimeout(() => {
                // Give user a moment to see prefilled fields before auto-connecting
                // Comment out the line below if you don't want auto-connect
                // this.connect();
            }, 500);
        }
    }

    async fetchTokenFromServer() {
        try {
            const url = window.location.origin + "/api/token";
            const r = await fetch(url);
            if (r.ok) {
                const d = await r.json();
                if (d.token) this.els.accessToken.value = d.token;
            }
        } catch (e) { console.log("Could not fetch token"); }
    }

    bindEvents() {
        // Login
        this.els.connectForm.addEventListener('submit', (e) => { e.preventDefault(); this.connect(); });

        // Top actions
        document.getElementById('btn-disconnect').addEventListener('click', () => this.disconnect());
        document.getElementById('btn-settings').addEventListener('click', () => this.els.settingsPanel.classList.add('open'));
        document.getElementById('close-settings').addEventListener('click', () => this.els.settingsPanel.classList.remove('open'));

        // Keyboard modal
        document.getElementById('btn-keyboard').addEventListener('click', () => this.openKeyboard());
        document.getElementById('close-keyboard').addEventListener('click', () => this.closeKeyboard());

        // Tab switching inside keyboard modal
        document.querySelectorAll('.kb-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });
        document.getElementById('send-text').addEventListener('click', () => this.sendText());
        document.getElementById('send-enter').addEventListener('click', () => this.sendKey('enter'));
        document.getElementById('send-esc').addEventListener('click', () => this.sendKey('esc'));
        document.getElementById('send-tab').addEventListener('click', () => this.sendKey('tab'));
        document.getElementById('send-backspace').addEventListener('click', () => this.sendKey('backspace'));

        // Hotkey buttons
        document.querySelectorAll('.hotkey-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                // Clear keyboard input to prevent live typing interference
                this.els.keyboardInput.value = '';
                this.lastKeyboardValue = '';
                // Send the hotkey
                this.sendHotkey(btn.dataset.keys);
                // Visual feedback
                btn.style.opacity = '0.7';
                setTimeout(() => { btn.style.opacity = '1'; }, 100);
            });
        });

        // Control buttons
        document.querySelectorAll('.ctrl-btn').forEach(btn => {
            btn.addEventListener('click', () => this.handleControlButton(btn.dataset.action));
        });

        // Touchpad
        this.bindTouchpad();

        // Screen click
        this.els.screenStream.addEventListener('click', (e) => this.handleScreenClick(e));

        // Mode selector
        this.els.modeSelector.addEventListener('change', (e) => this.setMode(e.target.value));


        // Settings
        document.getElementById('setting-screen').addEventListener('change', (e) => {
            this.screenEnabled = e.target.checked;
            this.send({ type: 'screen_toggle', enabled: this.screenEnabled });
        });
        this.els.monitorSelect.addEventListener('change', (e) => {
            this.setMonitor(parseInt(e.target.value));
        });
        document.getElementById('setting-sensitivity').addEventListener('input', (e) => {
            this.sensitivity = parseFloat(e.target.value);
            document.getElementById('sensitivity-value').textContent = this.sensitivity.toFixed(1) + 'x';
        });
        document.getElementById('setting-fps').addEventListener('change', (e) => {
            this.showFps = e.target.checked;
            this.els.fpsCounter.classList.toggle('visible', this.showFps);
        });
        document.getElementById('setting-tap-click').addEventListener('change', (e) => { this.tapToClick = e.target.checked; });
        document.getElementById('setting-long-press').addEventListener('change', (e) => { this.longPressRightClick = e.target.checked; });

        // Live typing from reference
        this.els.keyboardInput.addEventListener("input", () => this.handleLiveTyping());
    }

    setMode(mode) {
        this.touchpadMode = mode;
        const hints = { mouse: 'Drag to move pointer', keyboard: "Type on your device's keyboard", paint: 'Drag to paint and draw<br>Release to stop' };
        this.els.touchpadHint.innerHTML = hints[mode] || hints.mouse;

        // Update bottom stream bar mode badge
        const modeLabels = { mouse: 'Mouse', keyboard: 'Keyboard', paint: 'Paint' };
        document.getElementById('stream-mode').textContent = modeLabels[mode] || 'Mouse';

        if (mode === 'keyboard') {
            this.openKeyboard();
        }
    }

    bindTouchpad() {
        const tp = this.els.touchpad;

        tp.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            this.touchStart = { x: e.clientX, y: e.clientY, time: Date.now() };
            this.touchLast = { x: e.clientX, y: e.clientY };
            this.isDragging = false;
            this.moveBuffer = { dx: 0, dy: 0 };
            tp.classList.add("active");

            if (this.touchpadMode === "paint") {
                this.isPainting = true;
                this.send({ type: "mouse_down", button: "left" });
            } else if (this.longPressRightClick) {
                this.longPressTimer = setTimeout(() => {
                    this.send({ type: 'click', button: 'right', clicks: 1 });
                    this.vibrate();
                }, this.longPressDuration);
            }

            tp.setPointerCapture(e.pointerId);
        });

        tp.addEventListener('pointermove', (e) => {
            e.preventDefault();
            if (!this.touchStart.time) return;

            const rawDx = e.clientX - this.touchLast.x;
            const rawDy = e.clientY - this.touchLast.y;

            if (this.touchpadMode === "paint") {
                if (rawDx !== 0 || rawDy !== 0) {
                    this.send({ type: 'move', mode: 'relative', dx: Math.round(rawDx * this.sensitivity), dy: Math.round(rawDy * this.sensitivity) });
                }
            } else {
                this.moveBuffer.dx += rawDx * this.sensitivity * 2.5;
                this.moveBuffer.dy += rawDy * this.sensitivity * 2.5;

                const totalMoved = Math.abs(e.clientX - this.touchStart.x) + Math.abs(e.clientY - this.touchStart.y);
                if (totalMoved > 5) {
                    this.isDragging = true;
                    clearTimeout(this.longPressTimer);
                }
            }

            this.touchLast = { x: e.clientX, y: e.clientY };
        });

        tp.addEventListener('pointerup', (e) => {
            e.preventDefault();
            clearTimeout(this.longPressTimer);

            if (this.touchpadMode === "paint" && this.isPainting) {
                this.send({ type: "mouse_up", button: "left" });
                this.isPainting = false;
            } else {
                this.flushMoveBuffer();
                const duration = Date.now() - this.touchStart.time;
                if (!this.isDragging && duration < this.longPressDuration && this.tapToClick) {
                    this.send({ type: 'click', button: 'left', clicks: 1 });
                }
            }

            tp.classList.remove("active");
            this.touchStart = { x: 0, y: 0, time: 0 };
            this.isDragging = false;
        });

        tp.addEventListener('pointercancel', () => {
            clearTimeout(this.longPressTimer);
            if (this.isPainting) {
                this.send({ type: "mouse_up", button: "left" });
                this.isPainting = false;
            }
            this.flushMoveBuffer();
            this.touchStart = { x: 0, y: 0, time: 0 };
            tp.classList.remove("active");
        });

        tp.addEventListener('pointerleave', () => {
            clearTimeout(this.longPressTimer);
            if (this.isPainting) {
                this.send({ type: "mouse_up", button: "left" });
                this.isPainting = false;
            }
            this.flushMoveBuffer();
            this.touchStart = { x: 0, y: 0, time: 0 };
            tp.classList.remove("active");
        });

        this.startMoveFlushTimer();

        // Two-finger scroll
        tp.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.send({ type: 'scroll', amount: -Math.sign(e.deltaY) * 15 });
        }, { passive: false });
    }

    startMoveFlushTimer() {
        const flush = () => {
            this.flushMoveBuffer();
            if (this.connected) this.moveTimer = setTimeout(flush, this.moveInterval);
        };
        this.moveTimer = setTimeout(flush, this.moveInterval);
    }

    flushMoveBuffer() {
        if (this.moveBuffer.dx !== 0 || this.moveBuffer.dy !== 0) {
            this.send({ type: 'move', mode: 'relative', dx: Math.round(this.moveBuffer.dx), dy: Math.round(this.moveBuffer.dy) });
            this.moveBuffer.dx = 0;
            this.moveBuffer.dy = 0;
        }
    }

    handleScreenClick(e) {
        if (!this.connected) return;
        const rect = this.els.screenStream.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        this.send({ type: 'move', mode: 'absolute', dx: x, dy: y });
        this.send({ type: 'click', button: 'left', clicks: 1 });
    }

    handleControlButton(action) {
        switch(action) {
            case 'left-click': this.send({ type: 'click', button: 'left', clicks: 1 }); break;
            case 'right-click': this.send({ type: 'click', button: 'right', clicks: 1 }); break;
            case 'double-click': this.send({ type: 'click', button: 'left', clicks: 2 }); break;
            case 'scroll-up': this.send({ type: 'scroll', amount: 15 }); break;
            case 'scroll-down': this.send({ type: 'scroll', amount: -15 }); break;
            case 'center': this.send({ type: 'move', mode: 'absolute', dx: 0.5, dy: 0.5 }); break;
        }
    }

    handleLiveTyping() {
        const newVal = this.els.keyboardInput.value || "";
        const oldVal = this.lastKeyboardValue || "";
        let p = 0;
        const minLen = Math.min(oldVal.length, newVal.length);
        while (p < minLen && oldVal[p] === newVal[p]) p++;

        const deletes = oldVal.length - p;
        for (let i = 0; i < deletes; i++) {
            this.send({ type: 'key', key: 'backspace' });
        }

        const added = newVal.slice(p);
        if (added.length > 0) {
            this.send({ type: 'type', text: added });
        }

        this.lastKeyboardValue = newVal;
    }

    connect() {
        const url = this.els.serverUrl.value.trim();
        const token = this.els.accessToken.value.trim();
        if (!url || !token) { this.showStatus('Please enter both URL and token', 'error'); return; }

        let wsUrl = url;
        if (wsUrl.startsWith('http://')) wsUrl = wsUrl.replace('http://', 'ws://');
        else if (wsUrl.startsWith('https://')) wsUrl = wsUrl.replace('https://', 'wss://');
        else wsUrl = 'ws://' + wsUrl;
        if (!wsUrl.includes(':')) wsUrl += ':8008';
        wsUrl = wsUrl.replace(/\/$/, '') + '/ws';

        this.showStatus('Connecting...', 'info');
        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = () => { this.ws.send(JSON.stringify({ type: 'auth', token: token })); };
            this.ws.onmessage = (event) => { this.handleMessage(JSON.parse(event.data)); };
            this.ws.onclose = () => { if (this.connected) { this.disconnect(); this.showStatus('Connection lost', 'error'); } };
            this.ws.onerror = () => { this.showStatus('Connection failed', 'error'); };
        } catch (err) { this.showStatus('Invalid URL', 'error'); }
    }

    handleMessage(data) {
        switch(data.type) {
            case 'auth_ok': this.onConnected(); break;
            case 'error': this.showStatus(data.message, 'error'); this.ws.close(); break;
            case 'screen': this.onScreenFrame(data.data); break;
            case 'pong': break;
        }
    }

    onConnected() {
        this.connected = true;
        this.els.loginScreen.classList.remove('active');
        this.els.controlScreen.classList.add('active');
        this.els.statusDot.classList.add('connected');
        this.els.statusText.textContent = 'Connected';
        this.els.screenStream.classList.add('active');
        this.els.streamOverlay.style.display = 'none';
        this.pingInterval = setInterval(() => { this.send({ type: 'ping' }); }, 30000);
        this.startMoveFlushTimer();
        this.fetchScreenInfo();
        this.fetchMonitors();
        this.showStatus('Connected successfully!', 'success');
    }

    disconnect() {
        this.connected = false;
        if (this.moveTimer) { clearTimeout(this.moveTimer); this.moveTimer = null; }
        if (this.ws) { this.ws.close(); this.ws = null; }
        if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
        this.els.controlScreen.classList.remove('active');
        this.els.loginScreen.classList.add('active');
        this.els.statusDot.classList.remove('connected');
        this.els.statusText.textContent = 'Disconnected';
        this.els.screenStream.classList.remove('active');
        this.els.screenStream.src = '';
        this.els.streamOverlay.style.display = 'block';
        this.els.monitorSetting.style.display = 'none';
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(data));
    }

    onScreenFrame(base64Data) {
        this.els.screenStream.src = 'data:image/jpeg;base64,' + base64Data;
        this.frameCount++;
        const now = performance.now();
        if (now - this.lastFrameTime >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFrameTime = now;
            if (this.showFps) this.els.fpsCounter.textContent = this.fps + ' FPS';
        }
    }

    async fetchScreenInfo() {
        const url = this.els.serverUrl.value.trim().replace(/\/$/, '');
        try { const r = await fetch(url + '/api/screen'); const d = await r.json(); this.screenWidth = d.width; this.screenHeight = d.height; } catch (e) { console.log('Could not fetch screen info'); }
    }

    async fetchMonitors() {
        const url = this.els.serverUrl.value.trim().replace(/\/$/, '');
        try {
            const r = await fetch(url + '/api/monitors');
            const d = await r.json();
            this.monitors = d.monitors || [];
            if (this.monitors.length > 1) {
                this.els.monitorSetting.style.display = 'flex';

                // Only populate options once (preserve user selection on reconnect)
                if (!this._monitorsPopulated) {
                    this._monitorsPopulated = true;
                    this.els.monitorSelect.innerHTML = '<option value="0">🎯 Auto (follow cursor)</option>';
                    this.monitors.forEach(mon => {
                        const opt = document.createElement('option');
                        opt.value = mon.index;
                        opt.textContent = `${mon.primary ? '🖥️' : '📺'} Monitor ${mon.index} (${mon.width}x${mon.height})`;
                        this.els.monitorSelect.appendChild(opt);
                    });
                }

                // Update selection to match server state
                const newVal = d.auto_track ? '0' : String(d.current);
                if (this.els.monitorSelect.value !== newVal) {
                    this.els.monitorSelect.value = newVal;
                }
            }
        } catch (e) { console.log('Could not fetch monitors'); }
    }

    async setMonitor(index) {
        const url = this.els.serverUrl.value.trim().replace(/\/$/, '');
        try {
            const r = await fetch(url + '/api/monitor/' + index, { method: 'POST' });
            const d = await r.json();
            if (d.success) {
                this.monitors = d.monitors || this.monitors;
                this.els.monitorSelect.value = String(d.monitor);
                if (d.auto_track) {
                    this.els.monitorSelect.value = '0';
                    const autoOpt = document.createElement('option');
                    autoOpt.value = '0';
                    autoOpt.textContent = '🎯 Auto (follow cursor)';
                    this.els.monitorSelect.insertBefore(autoOpt, this.els.monitorSelect.firstChild);
                }
                this.showStatus('Monitor: ' + (d.auto_track ? 'Auto' : d.monitor), 'success');
            } else {
                this.showStatus('Failed to switch monitor', 'error');
            }
        } catch (e) { console.log('Failed to set monitor'); this.showStatus('Monitor switch failed', 'error'); }
    }

    openKeyboard() {
        this.els.keyboardModal.classList.add('active');
        this.switchTab('text');
        setTimeout(() => this.els.keyboardInput.focus(), 100);
    }

    closeKeyboard() {
        this.els.keyboardModal.classList.remove('active');
        this.els.keyboardInput.value = '';
        this.lastKeyboardValue = '';
    }

    switchTab(tabName) {
        document.querySelectorAll('.kb-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.kb-tab[data-tab="${tabName}"]`)?.classList.add('active');
        document.querySelectorAll('.kb-tab-content').forEach(c => c.classList.remove('active'));
        const content = document.getElementById('tab-' + tabName);
        if (content) content.classList.add('active');
    }

    sendText() {
        const text = this.els.keyboardInput.value;
        if (text) {
            for (const char of text) this.send({ type: 'key', key: char });
        }
        this.els.keyboardInput.value = '';
        this.lastKeyboardValue = '';
    }

    sendKey(key) { this.send({ type: 'key', key: key }); }
    sendHotkey(keys) { this.send({ type: 'hotkey', keys: keys }); }

    showStatus(message, type) {
        const el = this.els.connectionStatus;
        el.textContent = message;
        el.className = 'connection-status ' + type;
        if (type === 'success' || type === 'error') setTimeout(() => { el.style.display = 'none'; }, 3000);
    }

    vibrate() { if (navigator.vibrate) navigator.vibrate(50); }

    loadSettings() {
        const saved = localStorage.getItem('ai_settings');
        if (saved) {
            const s = JSON.parse(saved);
            this.sensitivity = s.sensitivity || 1.5;
            this.tapToClick = s.tapToClick !== false;
            this.longPressRightClick = s.longPressRightClick !== false;
            this.showFps = s.showFps || false;
            this.screenEnabled = s.screenEnabled !== false;
            this.touchpadMode = s.touchpadMode || 'mouse';

            document.getElementById('setting-sensitivity').value = this.sensitivity;
            document.getElementById('sensitivity-value').textContent = this.sensitivity.toFixed(1) + 'x';
            document.getElementById('setting-tap-click').checked = this.tapToClick;
            document.getElementById('setting-long-press').checked = this.longPressRightClick;
            document.getElementById('setting-fps').checked = this.showFps;
            document.getElementById('setting-screen').checked = this.screenEnabled;

            if (this.touchpadMode === 'paint') {
                this.els.modeBadge.textContent = 'Paint Mode';
                this.els.touchpadHint.innerHTML = 'Drag to paint and draw<br>Release to stop';
            }
        }
        window.addEventListener('beforeunload', () => {
            localStorage.setItem('ai_settings', JSON.stringify({
                sensitivity: this.sensitivity, tapToClick: this.tapToClick,
                longPressRightClick: this.longPressRightClick, showFps: this.showFps,
                screenEnabled: this.screenEnabled, touchpadMode: this.touchpadMode
            }));
        });
    }
}

const client = new AnywhereInputClient();
