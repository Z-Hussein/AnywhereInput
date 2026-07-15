/**
 * Visual overlay for engine and screen stream status states.
 */

export class ScreenStatusOverlay {
    constructor() {
        this.el = document.getElementById('screen-status-overlay');
        if (!this.el) {
            this.el = document.createElement('div');
            this.el.id = 'screen-status-overlay';
            document.body.appendChild(this.el);
        }
    }

    show(status, message = '') {
        const colors = {
            healthy: '#10b981',
            degraded: '#f59e0b',
            rebuilding: '#3b82f6',
            failed: '#ef4444',
            offline: '#6b7280',
        };
        const normalized = (status || 'offline').toLowerCase();
        const color = colors[normalized] || colors.offline;

        if (normalized === 'healthy') {
            this.hide();
            return;
        }

        this.el.textContent = message || normalized;
        this.el.style.background = color + '20';
        this.el.style.color = color;
        this.el.style.border = `1px solid ${color}40`;
        this.el.style.opacity = '1';
    }

    hide() {
        this.el.style.opacity = '0';
    }
}
