/**
 * localStorage settings persistence for AnywhereInput client.
 */

export class StorageManager {
    constructor(client) {
        this.client = client;
    }

    load() {
        const saved = localStorage.getItem('ai_settings');
        if (saved) {
            const s = JSON.parse(saved);
            this.client.sensitivity = s.sensitivity || 1.5;
            this.client.tapToClick = s.tapToClick !== false;
            this.client.longPressRightClick = s.longPressRightClick !== false;
            this.client.showFps = s.showFps || false;
            this.client.screenEnabled = s.screenEnabled !== false;
            this.client.touchpadMode = s.touchpadMode || 'mouse';

            document.getElementById('setting-sensitivity').value = this.client.sensitivity;
            document.getElementById('sensitivity-value').textContent = this.client.sensitivity.toFixed(1) + 'x';
            document.getElementById('setting-tap-click').checked = this.client.tapToClick;
            document.getElementById('setting-long-press').checked = this.client.longPressRightClick;
            document.getElementById('setting-fps').checked = this.client.showFps;
            document.getElementById('setting-screen').checked = this.client.screenEnabled;

            if (this.client.touchpadMode === 'paint') {
                this.client.els.modeBadge.textContent = 'Paint Mode';
                this.client.els.touchpadHint.innerHTML = 'Drag to paint and draw\nRelease to stop';
            }
        }

        window.addEventListener('beforeunload', () => {
            localStorage.setItem('ai_settings', JSON.stringify({
                sensitivity: this.client.sensitivity,
                tapToClick: this.client.tapToClick,
                longPressRightClick: this.client.longPressRightClick,
                showFps: this.client.showFps,
                screenEnabled: this.client.screenEnabled,
                touchpadMode: this.client.touchpadMode
            }));
        });
    }
}
