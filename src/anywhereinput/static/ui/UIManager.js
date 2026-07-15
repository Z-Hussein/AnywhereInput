/**
 * UI state management: settings panel, status messages, mode selector,
 * monitor dropdown, disconnect, and general DOM element binding.
 */

export class UIManager {
    constructor(client) {
        this.client = client;
    }

    bindElements() {
        this.client.els = {
            loginScreen: document.getElementById('login-screen'),
            controlScreen: document.getElementById('control-screen'),
            connectForm: document.getElementById('connect-form'),
            serverUrl: document.getElementById('server-url'),
            accessToken: document.getElementById('access-token'),
            statusDot: document.getElementById('status-dot'),
            statusText: document.getElementById('status-text'),
            screenContainer: document.getElementById('screen-container'),
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
            engineStateBadge: document.getElementById('engine-state-badge'),
            actionsPanel: document.querySelector('.actions-panel'),
            streamRestartBtn: document.getElementById('btn-settings-restart-stream'),
            requestForm: document.getElementById('request-form'),
            watchModeBtn: document.getElementById('btn-watch-mode'),
        };
        for (const key in this.client.els) {
            if (!this.client.els[key]) console.warn(`Element not found: ${key}`);
        }
    }

    bindEvents() {
        // Login form
        this.client.els.connectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.client.connect();
        });

        // Top actions
        document.getElementById('btn-disconnect').addEventListener('click', () => this.client.disconnect());
        document.getElementById('btn-settings').addEventListener('click', () =>
            this.client.els.settingsPanel.classList.add('open'));
        document.getElementById('close-settings').addEventListener('click', () =>
            this.client.els.settingsPanel.classList.remove('open'));

        // Mode selector
        this.client.els.modeSelector.addEventListener('change', (e) => this.client.setMode(e.target.value));

        // Settings
        document.getElementById('setting-screen').addEventListener('change', (e) => {
            this.client.screenEnabled = e.target.checked;
            this.client.send({ type: 'screen_toggle', enabled: this.client.screenEnabled });
        });
        this.client.els.monitorSelect.addEventListener('change', (e) => {
            this.client.setMonitor(parseInt(e.target.value));
        });
        document.getElementById('setting-sensitivity').addEventListener('input', (e) => {
            this.client.sensitivity = parseFloat(e.target.value);
            document.getElementById('sensitivity-value').textContent = this.client.sensitivity.toFixed(1) + 'x';
        });
        document.getElementById('setting-fps').addEventListener('change', (e) => {
            this.client.showFps = e.target.checked;
            this.client.els.fpsCounter.classList.toggle('visible', this.client.showFps);
        });
        document.getElementById('setting-tap-click').addEventListener('change', (e) => {
            this.client.tapToClick = e.target.checked;
        });
        document.getElementById('setting-long-press').addEventListener('change', (e) => {
            this.client.longPressRightClick = e.target.checked;
        });
        // Restart stream button (settings panel)
        const restartBtn = document.getElementById('btn-settings-restart-stream');
        if (restartBtn) {
            restartBtn.addEventListener('click', () => this.client.restartStream());
        }
    }

    setMode(mode) {
        const hints = {
            mouse: 'Drag to move pointer',
            keyboard: "Type on your device's keyboard",
            paint: 'Drag to paint and draw\nRelease to stop'
        };
        this.client.els.touchpadHint.innerHTML = hints[mode] || hints.mouse;

        const modeLabels = { mouse: 'Mouse', keyboard: 'Keyboard', paint: 'Paint' };
        document.getElementById('stream-mode').textContent = modeLabels[mode] || 'Mouse';

        if (mode === 'keyboard') {
            this.client.openKeyboard();
        }
    }

    showStatus(message, type) {
        const el = this.client.els.connectionStatus;
        el.textContent = message;
        el.className = 'connection-status ' + type;
        if (type === 'success' || type === 'error') {
            setTimeout(() => { el.style.display = 'none'; }, 3000);
        }
    }

    vibrate() {
        if (navigator.vibrate) navigator.vibrate(50);
    }
}
