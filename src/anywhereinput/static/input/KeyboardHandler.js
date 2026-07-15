/**
 * Keyboard modal, hotkeys, live typing, text sending, tab switching.
 */

export class KeyboardHandler {
    constructor(client) {
        this.client = client;
        this.lastKeyboardValue = "";
        this._suppressInput = false;
    }

    bind() {
        // Keyboard modal open/close - both the regular top-bar button and the fullscreen button
        document.getElementById('btn-keyboard')?.addEventListener('click', () => this.openKeyboard());
        document.getElementById('btn-watch-mode-keyboard')?.addEventListener('click', () => this.openKeyboard());
        document.getElementById('close-keyboard').addEventListener('click', () => this.closeKeyboard());

        // Tab switching inside keyboard modal
        document.querySelectorAll('.kb-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Action buttons inside keyboard modal
        document.getElementById('send-text').addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            this.sendText();
        });
        document.getElementById('send-enter').addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            this._clearInput();
            this.client.sendKey('enter');
        });
        document.getElementById('send-esc').addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            this.client.sendKey('esc');
        });
        document.getElementById('send-tab').addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            this.client.sendKey('tab');
        });
        document.getElementById('send-backspace').addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            this.client.sendKey('backspace');
        });

        // Arrow keys from Arrows tab
        document.getElementById('tab-arrows')?.addEventListener('pointerdown', (e) => {
            const btn = e.target.closest('.arrow-btn');
            if (!btn) return;
            e.stopPropagation();
            const key = btn.dataset.key;
            if (key) this.client.sendKey(key);
        });

        // Hotkey buttons - event delegation so dynamically injected buttons also work
        document.getElementById('keyboard-modal').addEventListener('pointerdown', (e) => {
            const btn = e.target.closest('.hotkey-btn');
            if (!btn) return;
            e.stopPropagation();
            if (btn.dataset.fired === '1') return;
            btn.dataset.fired = '1';
            setTimeout(() => { btn.dataset.fired = ''; }, 200);
            this._clearInput();
            const keys = btn.dataset.keys;
            console.log(`[Hotkey] Sending: ${keys}`);
            this.client.sendHotkey(keys);
            btn.style.opacity = '0.7';
            setTimeout(() => { btn.style.opacity = '1'; }, 100);
        });

        // Live typing on input
        this.client.els.keyboardInput.addEventListener("input", () => this.handleLiveTyping());

        // Handle Enter key on the input (covers mobile virtual keyboard Enter)
        this.client.els.keyboardInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                this.client.sendKey('enter');
                this._clearInput();
            }
        });
    }

    openKeyboard() {
        this.client.els.keyboardModal.classList.add('active');
        this.switchTab('text');
        setTimeout(() => this.client.els.keyboardInput.focus(), 100);
    }

    closeKeyboard() {
        this.client.els.keyboardModal.classList.remove('active');
        this._clearInput();
    }

    switchTab(tabName) {
        document.querySelectorAll('.kb-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.kb-tab[data-tab="${tabName}"]`)?.classList.add('active');
        document.querySelectorAll('.kb-tab-content').forEach(c => c.classList.remove('active'));
        const content = document.getElementById('tab-' + tabName);
        if (content) content.classList.add('active');
    }

    /** Clear input without triggering handleLiveTyping backspace flood. */
    _clearInput() {
        this._suppressInput = true;
        this.client.els.keyboardInput.value = '';
        this.lastKeyboardValue = '';
        this._suppressInput = false;
    }

    sendText() {
        this._clearInput();
    }

    handleLiveTyping() {
        if (this._suppressInput) return;

        const newVal = this.client.els.keyboardInput.value || "";
        const oldVal = this.lastKeyboardValue || "";

        if (newVal === oldVal) return;

        // Find common prefix
        let p = 0;
        const minLen = Math.min(oldVal.length, newVal.length);
        while (p < minLen && oldVal[p] === newVal[p]) p++;

        // Send backspaces for deleted chars
        const deletes = oldVal.length - p;
        for (let i = 0; i < deletes; i++) {
            this.client.sendKey('backspace');
        }

        // Send only the newly added characters
        const added = newVal.slice(p);
        if (added.length > 0) {
            this.client.send({ type: 'type', text: added });
        }

        this.lastKeyboardValue = newVal;
    }
}
