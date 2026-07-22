/**
 * Connection request flow: request approval, polling, token display.
 */

export class RequestConnectManager {
    constructor(client) {
        this.client = client;
        this._requestPending = false;
        this._requestPollTimer = null;
    }

    bind() {
        const form = document.getElementById('request-form');
        if (!form) return;

        // Check URL for ?connect=true - shows existing-token connect form instead of request form
        const params = new URLSearchParams(window.location.search);
        if (params.get('connect') === 'true') {
            this.client.els.requestForm.style.display = 'none';
            document.getElementById('approval-msg').style.display = 'none';
            form.style.display = 'block';
            this._showExistingTokenUI();
            return;
        }

        // If URL has a fresh token, discard any stale localStorage token
        const urlToken = params.get('token');
        if (urlToken) {
            const approvedData = localStorage.getItem('ai_request_approved');
            if (approvedData) {
                try {
                    const data = JSON.parse(approvedData);
                    if (data.token !== urlToken) {
                        // Token in URL differs from stored one — server restarted, old token is stale
                        localStorage.removeItem('ai_request_approved');
                        localStorage.removeItem('ai_pending_request');
                    }
                } catch(e) {
                    localStorage.removeItem('ai_request_approved');
                    localStorage.removeItem('ai_pending_request');
                }
            }
            // Don't auto-show old approval — the URL has the fresh token
            // Fall through to normal request form flow
        } else {
            // Check if we were already approved (persisted in localStorage)
            const approvedData = localStorage.getItem('ai_request_approved');
            if (approvedData) {
                try {
                    const data = JSON.parse(approvedData);

                    // Only auto-show approval if the server URL from this visit matches
                    // what was stored. If a new QR/tunnel link was opened, the old token is stale.
                    const currentUrl = new URL(window.location.href).origin;
                    const savedOrigin = data.server_url ?
                        new URL(data.server_url.replace(/\/$/, '')).origin :
                        null;

                    if (currentUrl === savedOrigin) {
                        // Same server — show the approved token for quick re-connect
                        this.client.els.requestForm.style.display = 'none';
                        this._showApprovalMessage(data.token, data.request_id);
                        return;
                    } else {
                        // Different server — old approval is stale, discard it
                        localStorage.removeItem('ai_request_approved');
                        localStorage.removeItem('ai_pending_request');
                    }
                } catch(e) {
                    localStorage.removeItem('ai_request_approved');
                }
            }
        }

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.requestConnect();
        });

        // Wire the "Already have a token?" / "Request a new connection?" toggle
        const existingTokenToggle = document.getElementById('existing-token-toggle');
        if (existingTokenToggle) {
            existingTokenToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const requestForm = document.getElementById('request-form');
                const connectForm = document.getElementById('connect-form');
                // Toggle between request form and connect form
                if (connectForm && connectForm.style.display === 'block') {
                    this._showRequestFormUI();
                } else {
                    this._showExistingTokenUI();
                }
            });
        }
    }

    _showRequestFormUI() {
        const approvalMsg = document.getElementById('approval-msg');
        const requestForm = document.getElementById('request-form');
        const connectForm = document.getElementById('connect-form');
        const toggleLink = document.getElementById('existing-token-toggle');

        if (approvalMsg) approvalMsg.style.display = 'none';
        if (connectForm) connectForm.style.display = 'none';
        if (toggleLink) toggleLink.textContent = 'Already have a token?';
        if (requestForm) requestForm.style.display = 'block';
    }

    _showExistingTokenUI() {
        const approvalMsg = document.getElementById('approval-msg');
        const requestForm = document.getElementById('request-form');
        const connectForm = document.getElementById('connect-form');
        const toggleLink = document.getElementById('existing-token-toggle');

        if (approvalMsg) approvalMsg.style.display = 'none';
        if (requestForm) requestForm.style.display = 'none';
        if (toggleLink) toggleLink.textContent = 'Request a new connection?';
        if (connectForm) connectForm.style.display = 'block';
    }

    _showApprovalMessage(token, requestId) {
        const approvalMsg = document.getElementById('approval-msg');
        const requestForm = document.getElementById('request-form');
        const toggleLink = document.getElementById('existing-token-toggle');
        const approvedTokenInput = document.getElementById('approved-token');

        if (requestForm) requestForm.style.display = 'none';
        if (approvalMsg) approvalMsg.style.display = 'block';
        if (toggleLink) toggleLink.style.display = 'block';
        if (approvedTokenInput) approvedTokenInput.value = token;

        // Copy button
        const copyBtn = document.getElementById('copy-token-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(token).then(() => {
                        copyBtn.textContent = '✅';
                        setTimeout(() => { copyBtn.textContent = '📋'; }, 1500);
                    });
                } else {
                    approvedTokenInput.select();
                    document.execCommand('copy');
                }
            });
        }

        // Connect button
        const connectBtn = document.getElementById('connect-with-token');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                if (this.client.els.serverUrl.value) {
                    this.client.els.accessToken.value = token;
                    this.client.connect();
                } else {
                    this.client.showStatus('Enter server URL above first', 'error');
                }
            });
        }

        // Dismiss button
        const dismissBtn = document.getElementById('dismiss-approval');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => {
                approvalMsg.style.display = 'none';
            });
        }
    }

    async requestConnect() {
        if (this._requestPending) {
            this.client.showStatus('Request already pending...', 'info');
            return;
        }
        const nameInput = document.getElementById('client-name');
        const name = nameInput.value.trim();
        if (!name) {
            this.client.showStatus('Please enter your name', 'error');
            return;
        }

        this._requestPending = true;
        this.client.showStatus('Sending request...', 'info');
        nameInput.disabled = true;

        const baseUrl = this.client.els.serverUrl.value.trim().replace(/\/$/, '');
        if (!baseUrl) {
            this.client.showStatus('Server URL is required', 'error');
            return;
        }

        try {
            const resp = await fetch(baseUrl + '/api/request-connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name }),
            });

            if (!resp.ok) {
                const err = await resp.text();
                this.client.showStatus(`Request failed: ${err}`, 'error');
                return;
            }

            const data = await resp.json();
            const requestId = data.request_id;

            localStorage.setItem('ai_pending_request', JSON.stringify({
                request_id: requestId,
                server_url: baseUrl,
                name: name,
            }));

            const statusEl = document.getElementById('connection-status');
            statusEl.innerHTML = `<div class="status-waiting">⏳ Request sent! Waiting for admin approval...<br><small>Your ID: <code>${requestId}</code></small></div>`;

            const poll = async () => {
                try {
                    const r = await fetch(`${baseUrl}/api/requests/status?request_id=${encodeURIComponent(requestId)}`);
                    if (!r.ok) return;
                    const s = await r.json();

                    if (s.status === 'approved') {
                        localStorage.setItem('ai_request_approved', JSON.stringify({
                            token: s.token,
                            request_id: requestId,
                            server_url: baseUrl,
                            approved_at: Date.now(),
                        }));
                        localStorage.removeItem('ai_pending_request');

                        this._requestPending = false;
                        this.client.showStatus('Connection approved! Connecting...', 'success');

                        setTimeout(() => {
                            nameInput.disabled = false;
                            statusEl.style.display = 'none';
                            this._showApprovalMessage(s.token, requestId);
                        }, 500);
                    } else if (s.status === 'declined') {
                        this.client.showStatus(s.message || 'Request declined.', 'error');
                        nameInput.disabled = false;
                        localStorage.removeItem('ai_pending_request');
                    }
                } catch (e) {
                    // Poll failure - keep trying silently
                }
            };

            poll();
            this._requestPollTimer = setInterval(poll, 2000);
        } catch (err) {
            this.client.showStatus(`Failed to send request: ${err.message}`, 'error');
            nameInput.disabled = false;
            this._requestPending = false;
        }
    }

    cleanup() {
        if (this._requestPollTimer) {
            clearInterval(this._requestPollTimer);
            this._requestPollTimer = null;
        }
    }
}
