/**
 * WebSocket connection lifecycle: connect, auth, disconnect, reconnect, send, message routing.
 */

export class ConnectionManager {
    constructor(client) {
        this.client = client;
        this.ws = null;
        this.connected = false;
        this.pingInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectTimer = null;
        this.baseReconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this._intentionalClose = false;
    }

    connect() {
        const url = this.client.els.serverUrl.value.trim();
        const token = this.client.els.accessToken.value.trim();
        if (!url || !token) {
            this.client.showStatus('Please enter both URL and token', 'error');
            return;
        }

        let wsUrl = url;
        if (wsUrl.startsWith('http://')) wsUrl = wsUrl.replace('http://', 'ws://');
        else if (wsUrl.startsWith('https://')) wsUrl = wsUrl.replace('https://', 'wss://');
        else wsUrl = 'ws://' + wsUrl;
        // Don't add :8008 for https/wss URLs (tunnel domains use port 443)
        if (!wsUrl.startsWith('wss://') && !wsUrl.includes(':')) wsUrl += ':8008';
        wsUrl = wsUrl.replace(/\/$/, '') + '/ws';

        this._intentionalClose = false;
        this._wsUrl = wsUrl;
        this._token = token;
        this.client.showStatus('Connecting...', 'info');
        this._openSocket(wsUrl, token);
    }

    _openSocket(wsUrl, token) {
        try {
            this.ws = new WebSocket(wsUrl);
            let authSent = false;
            const sendAuth = () => {
                if (!authSent && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'auth', token: token }));
                    authSent = true;
                }
            };
            sendAuth();  // Try immediately
            setTimeout(sendAuth, 500);  // Retry after 500ms for tunnel edge cases

            this.ws.binaryType = 'arraybuffer';  // Accept binary JPEG frames
            this.ws.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer) {
                    // Binary frame — raw JPEG image
                    this.client.screenManager.onScreenFrame(new Uint8Array(event.data));
                } else if (event.data) {
                    // Text frame — JSON messages, base64 frames, etc.
                    const parsed = JSON.parse(event.data);
                    if (parsed.type === 'screen' && typeof parsed.data === 'string') {
                        this.client.screenManager.onScreenFrame(parsed.data);
                    } else {
                        this.client.handleMessage(parsed);
                    }
                }
            };
            this.ws.onclose = (event) => {
                this._handleClose(event);
            };
            this.ws.onerror = () => {
                const state = this.ws ? this.ws.readyState : 3;
                const states = { 0: 'CONNECTING', 1: 'OPEN', 2: 'CLOSING', 3: 'CLOSED' };
                this.client.showStatus(`WebSocket error (readyState=${states[state]})`, 'error');
            };
        } catch (err) {
            this.client.showStatus('Invalid URL', 'error');
        }
    }

    _handleClose(event) {
        const { code, reason, wasClean } = event;
        const reasonText = reason || 'unknown';

        // Don't reconnect for intentional closes
        if (this._intentionalClose) {
            this._showDisconnected();
            return;
        }

        // Don't reconnect for auth/kick/policy close codes
        const noReconnectCodes = [4001, 4003, 4004, 1008];
        if (noReconnectCodes.includes(code)) {
            const messages = {
                4001: 'Authentication failed — check your token',
                4003: 'Connection rejected by server',
                4004: 'Disconnected by administrator',
                1008: 'Connection policy violation',
            };
            this.client.showStatus(messages[code] || `Disconnected (${code}): ${reasonText}`, 'error');
            this._showLoginScreen();
            return;
        }

        // Server restarting (1012) — always reconnect with longer delay
        if (code === 1012) {
            this.client.showStatus('Server is restarting — reconnecting in 3s...', 'info');
            this.reconnectTimer = setTimeout(() => {
                if (!this._intentionalClose && this._wsUrl && this._token) {
                    this._openSocket(this._wsUrl, this._token);
                }
            }, 3000);
            return;
        }

        // Clean close (normal closure) — don't reconnect
        if (wasClean && code === 1000) {
            this._showDisconnected();
            return;
        }

        // Abnormal close — attempt reconnection with exponential backoff
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(
                this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
                this.maxReconnectDelay
            );
            const jitter = delay * 0.1 * Math.random();
            const totalDelay = Math.round(delay + jitter);

            this.client.showStatus(
                `Connection lost (${code}: ${reasonText}). Reconnecting in ${Math.round(totalDelay / 1000)}s... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
                'info'
            );

            this.reconnectTimer = setTimeout(() => {
                if (!this._intentionalClose && this._wsUrl && this._token) {
                    this._openSocket(this._wsUrl, this._token);
                }
            }, totalDelay);
        } else {
            this.client.showStatus(
                `Connection lost (${code}: ${reasonText}). Max reconnection attempts reached.`,
                'error'
            );
            this._showLoginScreen();
        }
    }

    _showLoginScreen() {
        this.client.els.loginScreen.classList.add('active');
        this.client.els.controlScreen.classList.remove('active');
        this.connected = false;
        this.reconnectAttempts = 0;
    }

    _showDisconnected() {
        const state = this.ws ? this.ws.readyState : 3;
        const states = { 0: 'CONNECTING', 1: 'OPEN', 2: 'CLOSING', 3: 'CLOSED' };
        this.client.showStatus(`WebSocket closed (readyState=${states[state]})`, 'error');
        if (!this.connected) {
            this._showLoginScreen();
        }
        this.connected = false;
        this.reconnectAttempts = 0;
    }

    disconnect() {
        this._intentionalClose = true;
        this.connected = false;
        if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
        if (this.ws) { this.ws.close(1000, 'Client disconnect'); this.ws = null; }
        if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }

        this.client.els.controlScreen.classList.remove('active');
        this.client.els.loginScreen.classList.add('active');
        this.client.els.statusDot.classList.remove('connected');
        this.client.els.statusText.textContent = 'Disconnected';
        this.client.els.screenStream.classList.remove('active');
        this.client.els.screenStream.src = '';
        this.client.els.streamOverlay.style.display = 'block';
        this.client.els.monitorSetting.style.display = 'none';
        if (this.client.screenStatusOverlay) this.client.screenStatusOverlay.hide();
        if (this.client.els.screenContainer) this.client.els.screenContainer.style.opacity = '1';
        this.client.setEngineState('healthy');
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    onConnected() {
        this.connected = true;
        this.reconnectAttempts = 0;
        this.client.els.loginScreen.classList.remove('active');
        this.client.els.controlScreen.classList.add('active');
        this.client.els.statusDot.classList.add('connected');
        this.client.els.statusText.textContent = 'Connected';
        this.client.els.screenStream.classList.add('active');
        this.client.els.streamOverlay.style.display = 'none';
        this.pingInterval = setInterval(() => { this.send({ type: 'ping' }); }, 30000);
        this.client.showStatus('Connected successfully!', 'success');
    }
}
