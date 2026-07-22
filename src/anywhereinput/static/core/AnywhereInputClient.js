/**
 * AnywhereInputClient - Main orchestrator.
 * Coordinates all subsystems: connection, input, screen, UI, engine monitoring.
 */

import { ViewportManager } from '../utils/Viewport.js';
import { StorageManager } from '../utils/Storage.js';
import { RequestConnectManager } from '../utils/RequestConnect.js';
import { ConnectionManager } from './ConnectionManager.js';
import { EngineMonitor } from './EngineMonitor.js';
import { ScreenManager } from './ScreenManager.js';
import { TouchpadHandler } from '../input/TouchpadHandler.js';
import { ScreenClickHandler } from '../input/ScreenClickHandler.js';
import { KeyboardHandler } from '../input/KeyboardHandler.js';
import { ControlButtons } from '../input/ControlButtons.js';
import { UIManager } from '../ui/UIManager.js';
import { ScreenStatusOverlay } from '../ui/ScreenStatusOverlay.js';

export class AnywhereInputClient {
    constructor() {
        // State
        this.screenEnabled = true;
        this.sensitivity = 1.5;
        this.tapToClick = true;
        this.longPressRightClick = true;
        this.showFps = false;
        this.touchpadMode = "mouse";
        this.watchMode = false;
        this._watchTouchRevealed = false;
        this.engineState = 'healthy';
        this.serverOs = null; // detected from server auth_ok response

        // Subsystems (initialized in init())
        this.viewport = null;
        this.storage = null;
        this.requestConnect = null;
        this.connection = null;
        this.engineMonitor = null;
        this.screenManager = null;
        this.touchpad = null;
        this.screenClick = null;
        this.keyboard = null;
        this.controls = null;
        this.ui = null;
        this.screenStatusOverlay = null;
        this.els = {};  // DOM element cache - populated by UIManager.bindElements()

        this.init();
    }

    init() {
        // UI elements must be bound first (other modules depend on this.els)
        this.ui = new UIManager(this);
        this.ui.bindElements();

        // Initialize subsystems
        this.viewport = new ViewportManager(this);
        this.storage = new StorageManager(this);
        this.requestConnect = new RequestConnectManager(this);
        this.connection = new ConnectionManager(this);
        this.engineMonitor = new EngineMonitor(this);
        this.screenManager = new ScreenManager(this);
        this.touchpad = new TouchpadHandler(this);
        this.screenClick = new ScreenClickHandler(this);
        this.keyboard = new KeyboardHandler(this);
        this.controls = new ControlButtons(this);
        this.screenStatusOverlay = new ScreenStatusOverlay();

        // Bind all event listeners
        this.viewport.bind();
        this.ui.bindEvents();
        this.keyboard.bind();
        this.controls.bind();
        this.touchpad.bind();
        this.screenClick.bind();
        this.requestConnect.bind();

        // Load persisted settings and URL params
        this.storage.load();
        this.viewport.autoFillFromURL();
    }

    // ── Delegated methods (proxies to subsystems) ──

    get connected() { return this.connection ? this.connection.connected : false; }
    get ws() { return this.connection ? this.connection.ws : null; }

    connect() { this.connection.connect(); }
    disconnect() {
        this.touchpad.cleanup();
        this.requestConnect.cleanup();
        this.engineMonitor.stopPolling();
        this.connection.disconnect();
    }
    send(data) { this.connection.send(data); }

    onConnected() {
        this.connection.onConnected();
        this.touchpad.startMoveFlushTimer();
        this.engineMonitor.setEngineState('healthy');
        this.engineMonitor.startPolling();
        this.screenManager.fetchScreenInfo();
        this.screenManager.fetchMonitors();
    }

    handleMessage(data) {
        // Engine errors first
        if (this.engineMonitor.handleMessage(data)) return;

        switch(data.type) {
            case 'auth_ok':
                // Detect server OS and build shortcuts accordingly
                if (data.server_os) {
                    this.serverOs = data.server_os;
                    this._buildShortcutsForOs(data.server_os);
                }
                this.onConnected();
                break;
            case 'error':
                this.ui.showStatus(data.message, 'error');
                // If auth-related error, clear stale token so user sees login screen next visit
                if (data.message && (
                    data.message.toLowerCase().includes('invalid token') ||
                    data.message.toLowerCase().includes('token') && data.message.toLowerCase().includes('auth')
                )) {
                    localStorage.removeItem('ai_request_approved');
                    localStorage.removeItem('ai_pending_request');
                }
                this.connection.ws.close();
                break;
            case 'screen':
                this.screenManager.onScreenFrame(data.data);
                break;
            case 'screen_status':
                this.engineMonitor.applyScreenStreamState(data.status, data.message);
                if (data.persist && this.screenStatusOverlay) {
                    const normalized = (data.status || 'offline').toLowerCase();
                    const colors = {
                        degraded: '#f59e0b',
                        rebuilding: '#3b82f6',
                        failed: '#ef4444',
                        offline: '#6b7280'
                    };
                    const color = colors[normalized] || colors.offline;
                    this.screenStatusOverlay.el.style.opacity = '1';
                    this.screenStatusOverlay.el.style.transition = 'none';
                    setTimeout(() => {
                        if (this.engineState !== 'healthy') {
                            this.screenStatusOverlay.el.style.transition = 'opacity 2s';
                        }
                    }, 4000);
                }
                break;
            case 'pong':
                break;
        }
    }

    // ── Proxied UI methods ──
    showStatus(message, type) { this.ui.showStatus(message, type); }
    setMode(mode) { this.ui.setMode(mode); }
    setMonitor(index) { this.screenManager.setMonitor(index); }
    openKeyboard() { this.keyboard.openKeyboard(); }
    closeKeyboard() { this.keyboard.closeKeyboard(); }
    sendKey(key) { this.send({ type: 'key', key: key }); }
    sendHotkey(keys) {
        if (!this.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        // Accept both comma-separated string ("ctrl,a") and array (['ctrl','a'])
        if (typeof keys === 'string') {
            keys = keys.split(',').map(k => k.trim());
        }
        this.send({ type: 'hotkey', keys });
    }
    setEngineState(state, message) { this.engineMonitor.setEngineState(state, message); }
    restartStream() { this.engineMonitor.restartStream(); }
    vibrate() { this.ui.vibrate(); }

    // ── Platform-aware shortcuts ──

    /** Get human-readable key label for the current platform config */
    _label(key) {
        const labels = {
            ctrl: 'Ctrl', win: 'Win', super: 'Super', cmd: '\u2318',
            alt: 'Alt', option: 'Opt', shift: 'Shift', enter: 'Enter',
            tab: 'Tab', esc: 'Esc', backspace: 'Backspace', space: 'Space',
        };
        return labels[key] || key;
    }

    /** Build the platform-specific extra shortcuts below the base ones. */
    _buildShortcutsForOs(serverOs) {
        const plat = serverOs === 'darwin' ? 'macos' : (serverOs === 'linux' ? 'linux' : 'windows');

        const platformConfigs = {
            windows: {
                shortcuts: [
                    { label: 'Win+D', keys: ['win','d'] },
                    { label: 'Win+E', keys: ['win','e'] },
                    { label: 'Win+R', keys: ['win','r'] },
                ],
                system: [
                    { label: 'Win+L', keys: ['win','l'] },
                    { label: 'Win+Tab', keys: ['win','tab'] },
                ],
            },
            linux: {
                shortcuts: [
                    { label: 'Super+D', keys: ['super','d'] },
                    { label: 'Super+E', keys: ['super','e'] },
                    { label: 'Super+R', keys: ['super','r'] },
                ],
                system: [
                    { label: 'Super+L', keys: ['super','l'] },
                    { label: 'Super+Tab', keys: ['super','tab'] },
                ],
            },
            macos: {
                shortcuts: [
                    { label: '⌘+C', keys: ['command','c'] },
                    { label: '⌘+V', keys: ['command','v'] },
                    { label: '⌘+Z', keys: ['command','z'] },
                    { label: '⌘+Tab', keys: ['command','tab'] },
                    { label: '⌘+Q', keys: ['command','q'] },
                ],
                system: [
                    { label: '⌥+⌘+⎋', keys: ['alt','command','escape'] },
                    { label: '⌘+Space', keys: ['command','space'] },
                ],
            },
        };

        const config = platformConfigs[plat];
        if (!config) return;

        // Populate Shortcuts tab platform extras
        const shortcutsContainer = document.getElementById('shortcuts-platform-extras');
        if (shortcutsContainer) {
            let html = '<div class="hotkey-grid">';
            config.shortcuts.forEach((sc, i) => {
                if (i > 0 && i % 3 === 0) html += '</div><div class="hotkey-grid">';
                html += `<button class="hotkey-btn" data-keys="${sc.keys.join(',')}">${sc.label}</button>`;
            });
            html += '</div>';
            shortcutsContainer.innerHTML = html;
        }

        // Populate System tab platform extras
        const systemContainer = document.getElementById('system-platform-extras');
        if (systemContainer && config.system.length > 0) {
            let html = '<div class="hotkey-grid">';
            config.system.forEach((sc, i) => {
                if (i > 0 && i % 3 === 0) html += '</div><div class="hotkey-grid">';
                html += `<button class="hotkey-btn" data-keys="${sc.keys.join(',')}">${sc.label}</button>`;
            });
            html += '</div>';
            systemContainer.innerHTML = html;
        }
    }

    // ── Touch support for screen stream (tap-to-click, drag-to-move, long-press right-click, two-finger scroll) ──

    _screenTouchState = {
        touches: [],
        startTime: 0,
        startX: 0,
        startY: 0,
        lastX: 0,
        lastY: 0,
        moved: false,
        longPressTimer: null,
        isDragging: false,
        isLongPress: false
    };

    _onScreenTouchStart(e) {
        if (!this.connected) return;
        
        const touch = e.changedTouches[0];
        this._screenTouchState.touches = Array.from(e.touches);
        this._screenTouchState.startTime = Date.now();
        this._screenTouchState.startX = touch.clientX;
        this._screenTouchState.startY = touch.clientY;
        this._screenTouchState.lastX = touch.clientX;
        this._screenTouchState.lastY = touch.clientY;
        this._screenTouchState.moved = false;
        this._screenTouchState.isDragging = false;
        this._screenTouchState.isLongPress = false;
        this._screenTouchState.lastTapX = 0;
        this._screenTouchState.lastTapY = 0;
        this._screenTouchState.lastTapTime = 0;
        this._screenTouchState.lastTapClicked = false;

        // Two-finger scroll detection
        if (e.touches.length === 2) {
            this._screenTouchState.scrollMode = true;
            return;
        }

        // Long press for right click
        if (this.longPressRightClick) {
            this._screenTouchState.longPressTimer = setTimeout(() => {
                this._screenTouchState.isLongPress = true;
                this.send({ type: 'click', button: 'right', clicks: 1 });
                this.vibrate();
            }, 600);
        }

        // Capture touch for move tracking
        touch.target.setPointerCapture ? touch.target.setPointerCapture(touch.identifier) : null;
    }

    _onScreenTouchMove(e) {
        if (!this.connected || !this._screenTouchState.touches.length) return;
        
        const touch = e.changedTouches[0];
        const state = this._screenTouchState;

        // Two-finger scroll
        if (state.scrollMode && e.touches.length === 2) {
            const dy = state.startY - touch.clientY;
            if (Math.abs(dy) > 5) {
                this.send({ type: 'scroll', amount: dy > 0 ? 15 : -15 });
                state.startY = touch.clientY;
            }
            return;
        }

        const dx = touch.clientX - state.lastX;
        const dy = touch.clientY - state.lastY;
        const totalMoved = Math.abs(touch.clientX - state.startX) + Math.abs(touch.clientY - state.startY);

        if (totalMoved > 5) {
            state.moved = true;
            state.isDragging = true;
            clearTimeout(state.longPressTimer);
        }

        if (state.isDragging && !state.scrollMode) {
            // Send relative mouse movement
            const sendDx = Math.round(dx * this.sensitivity);
            const sendDy = Math.round(dy * this.sensitivity);
            if (sendDx !== 0 || sendDy !== 0) {
                this.send({
                    type: 'move',
                    mode: 'relative',
                    dx: sendDx,
                    dy: sendDy
                });
            }
        }

        state.lastX = touch.clientX;
        state.lastY = touch.clientY;
    }

    _onScreenTouchEnd(e) {
        const state = this._screenTouchState;
        
        if (state.scrollMode) {
            state.scrollMode = false;
        }

        clearTimeout(state.longPressTimer);

        if (!state.moved && !state.isLongPress) {
            // Check if this is a repeat tap at the same location (within tolerance)
            const stream = this.els.screenStream;
            if (stream && state.startX !== undefined && state.startY !== undefined) {
                const rect = stream.getBoundingClientRect();
                const x = (state.startX - rect.left) / rect.width;
                const y = (state.startY - rect.top) / rect.height;
                
                // Check if this tap is close to the last tap position
                const distance = Math.hypot(
                    (state.lastTapX || 0) - x,
                    (state.lastTapY || 0) - y
                );
                
                const TAP_TOLERANCE = 0.02; // ~2% of screen dimension
                const TAP_WINDOW = 500; // ms
                
                const isSameLocation = distance < TAP_TOLERANCE;
                const isWithinTimeWindow = (Date.now() - (state.lastTapTime || 0)) < TAP_WINDOW;
                
                if (isSameLocation && isWithinTimeWindow && state.lastTapClicked !== true) {
                    // Second tap on same location - CLICK
                    this.send({ type: 'click', mode: 'absolute', x, y, button: 'left', clicks: 1 });
                    state.lastTapClicked = true;
                    if (navigator.vibrate) navigator.vibrate(10);
                } else {
                    // First tap or different location - MOVE mouse there
                    if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
                        this.send({ type: 'move', mode: 'absolute', x, y });
                    }
                    state.lastTapX = x;
                    state.lastTapY = y;
                    state.lastTapTime = Date.now();
                    state.lastTapClicked = false;
                    if (navigator.vibrate) navigator.vibrate(5);
                }
            }
        }

        // Reset state
        state.touches = [];
        state.moved = false;
        state.isDragging = false;
        state.isLongPress = false;
        state.scrollMode = false;
    }
}
