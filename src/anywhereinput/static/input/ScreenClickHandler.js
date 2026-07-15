/**
 * Screen overlay click-to-move and watch mode toggle.
 * Supports touch for tap-to-click in watch mode.
 */

export class ScreenClickHandler {
    constructor(client) {
        this.client = client;
        this._touchStartX = 0;
        this._touchStartY = 0;
        this._touchStartTime = 0;
        this._touchMoved = false;
        this._tapThreshold = 10; // pixels
        this._tapTimeThreshold = 300; // ms
    }

    bind() {
        const stream = this.client.els.screenStream;

        // Click handler (mouse)
        stream.addEventListener('click', (e) => this.handleScreenClick(e));

        // Touch handlers for tap-to-click on stream
        stream.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
        stream.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: true });
        stream.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
        stream.addEventListener('touchcancel', (e) => this.resetTouchState());

        if (this.client.els.watchModeBtn) {
            // Single toggle button - toggles watch mode on/off
            this.client.els.watchModeBtn.addEventListener('click', () => this.toggleWatchMode());
        }
    }

    handleScreenClick(e) {
        if (!this.client.connected) return;
        const rect = this.client.els.screenStream.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        // Send as single compound message so move + click land atomically
        this.client.send({ type: 'click', mode: 'absolute', x, y, button: 'left', clicks: 1 });
    }

    handleTouchStart(e) {
        if (!this.client.connected) return;
        const touch = e.touches[0];
        const rect = this.client.els.screenStream.getBoundingClientRect();
        this._touchStartX = (touch.clientX - rect.left) / rect.width;
        this._touchStartY = (touch.clientY - rect.top) / rect.height;
        this._touchStartTime = Date.now();
        this._touchMoved = false;
    }

    handleTouchMove(e) {
        if (!this.client.connected) return;
        const touch = e.touches[0];
        const rect = this.client.els.screenStream.getBoundingClientRect();
        const currentX = (touch.clientX - rect.left) / rect.width;
        const currentY = (touch.clientY - rect.top) / rect.height;
        const dx = Math.abs(currentX - this._touchStartX);
        const dy = Math.abs(currentY - this._touchStartY);
        if (dx > this._tapThreshold / rect.width || dy > this._tapThreshold / rect.height) {
            this._touchMoved = true;
        }
    }

    handleTouchEnd(e) {
        if (!this.client.connected) return;
        const touchTime = Date.now() - this._touchStartTime;

        // Tap detected: short duration and minimal movement
        if (!this._touchMoved && touchTime < this._tapTimeThreshold) {
            this.client.send({
                type: 'click',
                mode: 'absolute',
                x: this._touchStartX,
                y: this._touchStartY,
                button: 'left',
                clicks: 1
            });
            // Haptic feedback if available
            if (navigator.vibrate) navigator.vibrate(10);
        }
        this.resetTouchState();
    }

    resetTouchState() {
        this._touchStartX = 0;
        this._touchStartY = 0;
        this._touchStartTime = 0;
        this._touchMoved = false;
    }

    toggleWatchMode() {
        const inWatch = !!this.client.watchMode;

        if (!inWatch) {
            // Enter watch mode
            this.client.watchMode = true;

            const cs = document.getElementById('control-screen');
            cs.classList.add('watch-mode');

            // Update button to show "exit" state
            const btn = this.client.els.watchModeBtn;
            if (btn) {
                btn.textContent = '⬅️';
                btn.title = 'Exit Fullscreen';
            }

            setTimeout(() => {
                if (this.client.els.touchpadHint) this.client.els.touchpadHint.style.opacity = '0';
            }, 3000);

            // Go real fullscreen
            const target = cs;
            if (!document.fullscreenElement) {
                (target.requestFullscreen || target.webkitRequestFullscreen || target.msRequestFullscreen).call(target)
                    .catch(() => {});
            }
        } else {
            // Exit watch mode
            this.client.watchMode = false;

            const cs = document.getElementById('control-screen');
            cs.classList.remove('watch-mode');

            // Update button to show "enter" state
            const btn = this.client.els.watchModeBtn;
            if (btn) {
                btn.textContent = '👁️';
                btn.title = 'Enter Fullscreen';
            }

            if (this.client.els.touchpadHint) this.client.els.touchpadHint.style.opacity = '1';

            // Exit real fullscreen
            if (document.fullscreenElement) {
                (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document)
                    .catch(() => {});
            }
        }

        localStorage.setItem('ai_watch_mode', this.client.watchMode ? 'true' : 'false');
    }
}
