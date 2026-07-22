/**
 * Control panel buttons: left/right/double click, scroll, center mouse.
 */

export class ControlButtons {
    constructor(client) {
        this.client = client;
    }

    bind() {
        document.querySelectorAll('.ctrl-btn').forEach(btn => {
            btn.addEventListener('pointerdown', (e) => {
                e.stopPropagation();
                if (btn.dataset.fired === '1') return;
                btn.dataset.fired = '1';
                setTimeout(() => { btn.dataset.fired = ''; }, 200);
                this.handleAction(btn.dataset.action);
            });
        });
    }

    handleAction(action) {
        if (!this.client.connected || !this.client.ws || this.client.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        switch(action) {
            case 'left-click':
                this.client.send({ type: 'click', button: 'left', clicks: 1 });
                break;
            case 'right-click':
                this.client.send({ type: 'click', button: 'right', clicks: 1 });
                break;
            case 'double-click':
                this.client.send({ type: 'click', button: 'left', clicks: 2 });
                break;
            case 'scroll-up':
                this.client.send({ type: 'scroll', amount: 15 });
                break;
            case 'scroll-down':
                this.client.send({ type: 'scroll', amount: -15 });
                break;
            case 'center':
                this.client.send({ type: 'move', mode: 'absolute', dx: 0.5, dy: 0.5 });
                break;
        }
    }
}
