/**
 * Screen frame rendering, FPS counting, aspect ratio, monitor management.
 */

export class ScreenManager {
    constructor(client) {
        this.client = client;
        this.screenWidth = 1920;
        this.screenHeight = 1080;
        this.monitors = [];
        this.lastFrameTime = 0;
        this.frameCount = 0;
        this.fps = 0;
        this._lastFrameRenderTime = 0;
    }

    onScreenFrame(base64Data) {
        // Update immediately - no frame skipping for lowest perceived latency
        const now = performance.now();
        if (this._lastFrameRenderTime && now - this._lastFrameRenderTime < 8) {
            return;
        }
        this._lastFrameRenderTime = now;

        // Direct assignment - fastest possible frame swap
        if (this.client.screenStatusOverlay) this.client.screenStatusOverlay.hide();
        if (this.client.els.screenContainer) this.client.els.screenContainer.style.opacity = '1';
        this.client.els.screenStream.src = 'data:image/jpeg;base64,' + base64Data;
        
        this.frameCount++;

        if (performance.now() - this.lastFrameTime >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFrameTime = now;
            if (this.client.showFps && this.client.els.fpsCounter) {
                this.client.els.fpsCounter.textContent = this.fps + ' FPS';
            }
        }
    }

    async fetchScreenInfo() {
        const url = this.client.els.serverUrl.value.trim().replace(/\/$/, '');
        try {
            const r = await fetch(url + '/api/screen');
            const d = await r.json();
            this.screenWidth = d.width;
            this.screenHeight = d.height;
            if (this.screenWidth > 0 && this.screenHeight > 0) {
                this.client.els.screenStream.style.aspectRatio = `${this.screenWidth} / ${this.screenHeight}`;
            }
        } catch (e) {
            console.log('Could not fetch screen info');
        }
    }

    async fetchMonitors() {
        const url = this.client.els.serverUrl.value.trim().replace(/\/$/, '');
        try {
            const r = await fetch(url + '/api/monitors');
            const d = await r.json();
            this.monitors = d.monitors || [];
            if (this.monitors.length > 0) {
                this.client.els.monitorSetting.style.display = 'flex';
                this.client.els.monitorSelect.innerHTML = '';

                const autoOpt = document.createElement('option');
                autoOpt.value = '0';
                autoOpt.textContent = '🎯 Auto (follow cursor)';
                this.client.els.monitorSelect.appendChild(autoOpt);

                const sortedMonitors = [...this.monitors].sort((a, b) => a.index - b.index);
                sortedMonitors.forEach(mon => {
                    const opt = document.createElement('option');
                    opt.value = String(mon.index);
                    opt.textContent = `${mon.primary ? '🖥️' : '📺'} Monitor ${mon.index} (${mon.width}x${mon.height})`;
                    this.client.els.monitorSelect.appendChild(opt);
                });

                const newVal = d.auto_track ? '0' : String(d.current);
                this.client.els.monitorSelect.value = newVal;
            } else {
                this.client.els.monitorSetting.style.display = 'none';
            }
        } catch (e) {
            console.log('Could not fetch monitors');
        }
    }

    async setMonitor(index) {
        const url = this.client.els.serverUrl.value.trim().replace(/\/$/, '');
        try {
            const r = await fetch(url + '/api/monitor/' + index, { method: 'POST' });
            const d = await r.json();
            if (d.success) {
                this.monitors = d.monitors || this.monitors;
                this.client.els.monitorSelect.value = String(d.monitor);
                if (d.auto_track) {
                    this.client.els.monitorSelect.value = '0';
                }
                this.client.showStatus('Monitor: ' + (d.auto_track ? 'Auto' : d.monitor), 'success');
            } else {
                this.client.showStatus('Failed to switch monitor', 'error');
            }
        } catch (e) {
            console.log('Failed to set monitor');
            this.client.showStatus('Monitor switch failed', 'error');
        }
    }
}
