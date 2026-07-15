/**
 * Viewport sizing and URL parameter handling for AnywhereInput client.
 */

export class ViewportManager {
    constructor(client) {
        this.client = client;
    }

    bind() {
        const update = () => {
            const vv = window.visualViewport;
            const h = vv ? vv.height : window.innerHeight;
            const w = vv ? vv.width : window.innerWidth;
            document.documentElement.style.setProperty('--app-height', `${Math.round(h)}px`);
            document.documentElement.style.setProperty('--app-width', `${Math.round(w)}px`);
        };

        update();
        window.addEventListener('resize', update, { passive: true });
        window.addEventListener('orientationchange', update, { passive: true });
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', update, { passive: true });
            window.visualViewport.addEventListener('scroll', update, { passive: true });
        }
    }

    autoFillFromURL() {
        const params = new URLSearchParams(window.location.search);
        const queryToken = params.get("token");
        const queryHost = params.get("host");
        const connectParam = params.get("connect");

        if (queryHost) {
            this.client.els.serverUrl.value = queryHost;
        } else if (window.location.protocol.startsWith("http")) {
            this.client.els.serverUrl.value = window.location.origin;
        } else if (window.location.hostname) {
            this.client.els.serverUrl.value = window.location.hostname;
        }

        if (queryToken) {
            this.client.els.accessToken.value = queryToken;
        }

        // If ?connect=true, show the connect form instead of request form
        if (connectParam === 'true') {
            setTimeout(() => {
                const approvalMsg = document.getElementById('approval-msg');
                const toggleLink = document.getElementById('existing-token-toggle');
                if (approvalMsg) approvalMsg.style.display = 'none';
                if (toggleLink) toggleLink.style.display = 'none';
                this.client.els.requestForm.style.display = 'block';
            }, 100);
        }

        // Auto-connect if both URL and token are available
        if (this.client.els.serverUrl.value && this.client.els.accessToken.value) {
            setTimeout(() => {
                this.client.connect();
            }, 500);
        }
    }
}
