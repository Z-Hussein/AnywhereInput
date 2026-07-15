/**
 * WebSocket connection lifecycle: connect, auth, disconnect, send, message routing.
 */

export class ConnectionManager {
    constructor(client) {
        this.client = client;
        this.ws = null;
        this.connected = false;
        this.pingInterval = null;
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

        this.client.showStatus('Connecting...', 'info');
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

            this.ws.onmessage = (event) => {
                if (event.data) this.client.handleMessage(JSON.parse(event.data));
            };
            this.ws.onclose = () => {
                const state = this.ws.readyState;
                const states = { 0: 'CONNECTING', 1: 'OPEN', 2: 'CLOSING', 3: 'CLOSED' };
                this.client.showStatus(`WebSocket closed (readyState=${states[state]})`, 'error');
            };
            this.ws.onerror = () => {
                const state = this.ws.readyState;
                const states = { 0: 'CONNECTING', 1: 'OPEN', 2: 'CLOSING', 3: 'CLOSED' };
                this.client.showStatus(`WebSocket error (readyState=${states[state]})`, 'error');
            };
        } catch (err) {
            this.client.showStatus('Invalid URL', 'error');
        }
    }

    disconnect() {
        this.connected = false;
        if (this.ws) { this.ws.close(); this.ws = null; }
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
