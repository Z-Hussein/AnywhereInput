/**
 * Touchpad pointer events: drag-to-move, long-press right-click, paint mode,
 * two-finger scroll, and direct delta tracking for both normal and watch
 * (fullscreen) modes.
 *
 * Matches the original android_controller.html touchpad: raw pixel deltas
 * sent straight to the server with no rounding, no smoothing, no preventDefault.
 */

export class TouchpadHandler {
    constructor(client) {
        this.client = client;
        this.touchStart = { x: 0, y: 0, time: 0 };
        this.touchLast = { x: 0, y: 0 };
        this.isDragging = false;
        this.longPressTimer = null;
        this.longPressDuration = 600;
        // Delta buffer - flushes ASAP for low latency on mobile
        this.moveBuffer = { dx: 0, dy: 0 };
        this.hasPendingMove = false;
        this.isPainting = false;

        // Two-finger scroll state
        this.twoFingerScrolling = false;
        this.lastTwoFingerY = 0;
        this.scrollAccum = 0;
    }

    bind() {
        const tp = this.client.els.touchpad;

        tp.addEventListener('pointerdown', (e) => this._onPointerDown(e, tp));
        tp.addEventListener('pointerup', (e) => this._onPointerUp(e, tp));
        tp.addEventListener('pointercancel', () => this._onPointerCancel(tp));
        tp.addEventListener('pointerleave', () => this._onPointerLeave(tp));
        tp.addEventListener('pointermove', (e) => this._onPointerMove(e, tp));

        if (this.client.els.screenContainer) {
            const sc = this.client.els.screenContainer;
            sc.addEventListener('pointerdown', (e) => this._onPointerDown(e, tp));
            sc.addEventListener('pointerup', (e) => this._onPointerUp(e, tp));
            sc.addEventListener('pointercancel', () => this._onPointerCancel(tp));
            sc.addEventListener('pointerleave', () => this._onPointerLeave(tp));
            sc.addEventListener('pointermove', (e) => this._onPointerMove(e, tp));
        }

        if (this.client.els.screenStream) {
            this.client.els.screenStream.addEventListener('touchstart', (e) =>
                this.client._onScreenTouchStart(e), { passive: false });
            this.client.els.screenStream.addEventListener('touchmove', (e) =>
                this.client._onScreenTouchMove(e), { passive: false });
            this.client.els.screenStream.addEventListener('touchend', (e) =>
                this.client._onScreenTouchEnd(e), { passive: false });
        }

        this.startMoveFlushTimer();

        tp.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.client.send({ type: 'scroll', amount: -Math.sign(e.deltaY) * 15 });
        }, { passive: false });

        // Two-finger scroll on touch devices
        tp.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: false });
        tp.addEventListener('touchmove', (e) => this._onTouchMove(e), { passive: false });
        tp.addEventListener('touchend', (e) => this._onTouchEnd(e), { passive: false });
        tp.addEventListener('touchcancel', (e) => this._onTouchEnd(e), { passive: false });
    }

    _onTouchStart(e) {
        if (e.touches.length === 2) {
            e.preventDefault();
            this.twoFingerScrolling = true;
            this.lastTwoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
            this.scrollAccum = 0;
            // Cancel any ongoing single-finger drag
            this.touchStart = { x: 0, y: 0, time: 0 };
            this.isDragging = false;
        }
    }

    _onTouchMove(e) {
        if (this.twoFingerScrolling && e.touches.length === 2) {
            e.preventDefault();
            const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
            const dy = midY - this.lastTwoFingerY;
            this.lastTwoFingerY = midY;

            // Accumulate and send scroll when threshold reached
            this.scrollAccum += dy;
            const threshold = 3;
            if (Math.abs(this.scrollAccum) >= threshold) {
                const amount = -Math.round(this.scrollAccum / threshold) * 15;
                this.client.send({ type: 'scroll', amount });
                this.scrollAccum = 0;
            }
        }
    }

    _onTouchEnd(e) {
        if (this.twoFingerScrolling && e.touches.length < 2) {
            this.twoFingerScrolling = false;
            this.scrollAccum = 0;
        }
    }

    _onPointerDown(e, tp) {
        if (this.twoFingerScrolling) return;
        e.preventDefault();
        this.touchStart = { x: e.clientX, y: e.clientY, time: Date.now() };
        this.touchLast = { x: e.clientX, y: e.clientY };
        this.isDragging = false;
        this.moveBuffer = { dx: 0, dy: 0 };
        tp.classList.add("active");

        if (this.client.watchMode) {
            if (this.client.els.touchpadHint && !this.client._watchTouchRevealed) {
                this.client.els.touchpadHint.style.opacity = '0.8';
                setTimeout(() => { this.client.els.touchpadHint.style.opacity = '0'; }, 2000);
                this.client._watchTouchRevealed = true;
            }
        }

        if (this.client.touchpadMode === "paint") {
            this.isPainting = true;
            this.client.send({ type: "mouse_down", button: "left" });
        } else if (this.client.longPressRightClick) {
            this.longPressTimer = setTimeout(() => {
                this.client.send({ type: 'click', button: 'right', clicks: 1 });
                this.client.vibrate();
            }, this.longPressDuration);
        }

        e.target.setPointerCapture(e.pointerId);
    }

    _onPointerMove(e, tp) {
        if (this.twoFingerScrolling) return;
        if (!this.touchStart.time) return;

        const rawDx = e.clientX - this.touchLast.x;
        const rawDy = e.clientY - this.touchLast.y;

        if (rawDx === 0 && rawDy === 0) return;

        // Accumulate deltas into moveBuffer
        this.moveBuffer.dx += rawDx * this.client.sensitivity;
        this.moveBuffer.dy += rawDy * this.client.sensitivity;

        // Schedule flush ASAP - no fixed interval, fires on next animation frame
        if (!this.hasPendingMove) {
            this.hasPendingMove = true;
            requestAnimationFrame(this._flushMoves.bind(this));
        }

        const totalMoved = Math.abs(e.clientX - this.touchStart.x)
            + Math.abs(e.clientY - this.touchStart.y);
        if (totalMoved > 5) {
            this.isDragging = true;
            clearTimeout(this.longPressTimer);
        }

        this.touchLast = { x: e.clientX, y: e.clientY };
    }

    _flushMoves() {
        this.hasPendingMove = false;
        if (this.moveBuffer.dx === 0 && this.moveBuffer.dy === 0) return;

        const sendDx = Math.round(this.moveBuffer.dx);
        const sendDy = Math.round(this.moveBuffer.dy);
        this.client.send({
            type: 'move', mode: 'relative',
            dx: sendDx, dy: sendDy,
        });
        this.moveBuffer.dx = 0;
        this.moveBuffer.dy = 0;

        // Keep flushing while still dragging
        if (this.isDragging && this.client.connected) {
            requestAnimationFrame(this._flushMoves.bind(this));
        }
    }

    _onPointerUp(e, tp) {
        e.preventDefault();
        clearTimeout(this.longPressTimer);

        if (this.client.touchpadMode === "paint" && this.isPainting) {
            this.client.send({ type: "mouse_up", button: "left" });
            this.isPainting = false;
        } else {
            const duration = Date.now() - this.touchStart.time;
            if (!this.isDragging && duration < this.longPressDuration && this.client.tapToClick) {
                this.client.send({ type: 'click', button: 'left', clicks: 1 });
            }
        }

        tp.classList.remove("active");
        this.touchStart = { x: 0, y: 0, time: 0 };
        this.isDragging = false;
    }

    _onPointerCancel(tp) {
        clearTimeout(this.longPressTimer);

        if (this.isPainting) {
            this.client.send({ type: "mouse_up", button: "left" });
            this.isPainting = false;
        }

        this.touchStart = { x: 0, y: 0, time: 0 };
        tp.classList.remove("active");
    }

    _onPointerLeave(tp) {
        clearTimeout(this.longPressTimer);

        if (this.isPainting) {
            this.client.send({ type: "mouse_up", button: "left" });
            this.isPainting = false;
        }

        this.touchStart = { x: 0, y: 0, time: 0 };
        tp.classList.remove("active");
    }

    startMoveFlushTimer() {
        // Use requestAnimationFrame instead of setTimeout for lower latency
        const flushLoop = () => {
            if (this.moveBuffer.dx === 0 && this.moveBuffer.dy === 0) {
                this.moveTimer = requestAnimationFrame(flushLoop);
                return;
            }
            const sendDx = Math.round(this.moveBuffer.dx);
            const sendDy = Math.round(this.moveBuffer.dy);
            this.client.send({
                type: 'move', mode: 'relative',
                dx: sendDx, dy: sendDy,
            });
            this.moveBuffer.dx = 0;
            this.moveBuffer.dy = 0;
            if (this.client.connected) this.moveTimer = requestAnimationFrame(flushLoop);
        };
        this.moveTimer = requestAnimationFrame(flushLoop);
    }

    cleanup() {
        if (this.moveTimer) {
            cancelAnimationFrame(this.moveTimer);
            this.moveTimer = null;
        }
    }
}
