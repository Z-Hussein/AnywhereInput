/**
 * Engine health polling, state tracking, and screen status management.
 */

export class EngineMonitor {
    constructor(client) {
        this.client = client;
        this.enginePollTimer = null;
        this.enginePollFailures = 0;
    }

    setEngineState(state, message = '') {
        const normalized = ['healthy', 'degraded', 'recovering', 'offline'].includes(state)
            ? state
            : 'healthy';
        this.client.engineState = normalized;

        // Restore restart button label when recovery is done
        const btn = this.client.els.streamRestartBtn;
        if (btn && normalized === 'healthy') {
            btn.disabled = false;
            btn.textContent = '⟳ Restart Stream';
        }

        if (this.client.els.engineStateBadge) {
            this.client.els.engineStateBadge.classList.remove('healthy', 'degraded', 'recovering', 'offline');
            this.client.els.engineStateBadge.classList.add(normalized);
            this.client.els.engineStateBadge.textContent = message || `ENGINE: ${normalized.toUpperCase()}`;
        }

        // Only disable inputs when truly offline
        const disableInputs = normalized === 'offline';
        if (this.client.els.touchpad) {
            this.client.els.touchpad.classList.toggle('engine-disabled', disableInputs);
            this.client.els.touchpad.style.pointerEvents = disableInputs ? 'none' : 'auto';
        }
        if (this.client.els.actionsPanel) {
            this.client.els.actionsPanel.classList.toggle('engine-disabled', disableInputs);
            this.client.els.actionsPanel.style.pointerEvents = disableInputs ? 'none' : 'auto';
        }
    }

    applyScreenStreamState(status, message = '') {
        const normalized = (status || 'offline').toLowerCase();
        if (this.client.screenStatusOverlay) {
            this.client.screenStatusOverlay.show(normalized, message || '');
        }

        if (this.client.els.screenContainer) {
            this.client.els.screenContainer.style.opacity = normalized === 'healthy' ? '1' : '0.4';
        }

        if (normalized === 'rebuilding') {
            this.setEngineState('recovering', 'ENGINE: RECOVERING');
        } else if (normalized === 'failed' || normalized === 'offline') {
            this.setEngineState('offline', 'ENGINE: OFFLINE');
        } else if (normalized === 'degraded') {
            this.setEngineState('degraded', 'ENGINE: DEGRADED');
        } else if (normalized === 'healthy') {
            this.setEngineState('healthy', 'ENGINE: HEALTHY');
        }
    }

    startPolling() {
        if (this.enginePollTimer) {
            clearInterval(this.enginePollTimer);
            this.enginePollTimer = null;
        }
        this.enginePollFailures = 0;

        const poll = async () => {
            const baseUrl = this.client.els.serverUrl.value.trim().replace(/\/$/, '');
            if (!baseUrl || !this.client.connected) return;
            try {
                const resp = await fetch(baseUrl + '/api/engine', { cache: 'no-store' });
                if (!resp.ok) {
                    this.enginePollFailures++;
                    if (this.enginePollFailures > 2) {
                        clearInterval(this.enginePollTimer);
                        this.enginePollTimer = null;
                    }
                    return;
                }
                this.enginePollFailures = 0;
                const payload = await resp.json();
                const state = (payload.state || payload.engine_state || 'healthy').toString().toLowerCase();
                this.setEngineState(state);
                const screenState = (payload.screen_engine?.state || 'healthy').toString().toLowerCase();
                const screenMessage = (payload.screen_engine?.message || '').toString();
                this.applyScreenStreamState(screenState, screenMessage);
            } catch (e) {
                this.enginePollFailures++;
                if (this.enginePollFailures > 5 && this.enginePollTimer) {
                    clearInterval(this.enginePollTimer);
                    this.enginePollTimer = null;
                }
            }
        };

        poll();
        this.enginePollTimer = setInterval(poll, 5000);
    }

    stopPolling() {
        if (this.enginePollTimer) {
            clearInterval(this.enginePollTimer);
            this.enginePollTimer = null;
        }
    }

    restartStream() {
        // Disable button during restart
        const btn = this.client.els.streamRestartBtn;
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⟳ Restarting...';
        }
        
        // Show status feedback
        if (this.setEngineState) {
            this.setEngineState('recovering', 'ENGINE: RESTARTING');
        }
        if (this.applyScreenStreamState) {
            this.applyScreenStreamState('rebuilding', 'Restarting stream...');
        }
        
        // Send command to server
        this.client.send({ type: 'screen_restart' });
    }

    handleMessage(data) {
        if (data && data.error) {
            if (data.error === 'capture_engine_offline') {
                this.setEngineState('offline', 'ENGINE: OFFLINE');
                return true;
            }
            if (data.error === 'capture_error') {
                const recovering = Boolean(data.recovering);
                this.setEngineState(
                    recovering ? 'recovering' : 'degraded',
                    recovering ? 'ENGINE: RECOVERING' : 'ENGINE: DEGRADED'
                );
                return true;
            }
        }
        return false;
    }
}
