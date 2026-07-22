"""MouseWorker - Pyautogui input engine thread."""

import platform
import queue
import threading
import time

from anywhereinput._constants import (
    DEFAULT_MOVE_INTERVAL,
    MAX_MOVE_PER_BATCH,
    MAX_MOVES_PER_SEC,
)
from anywhereinput.logging_config import get_logger

log = get_logger(__name__)

try:
    import pyautogui  # type: ignore[import-untyped]

    # Optimize pyautogui for minimum latency
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except ImportError:
    pyautogui = None

# Sentinel value used to wake a blocked queue.get() during shutdown.
_SENTINEL = object()

# Shared lock to serialize pyautogui access across threads.
# Moves bypass this lock when direct X11 is available.
# Clicks, keys, and cursor-position reads still need it.
_pyautogui_lock = threading.Lock()


class MouseWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue: queue.Queue = queue.Queue(maxsize=100)  # Reduced from 200
        self.running = True
        self._pyautogui_lock = _pyautogui_lock
        if pyautogui is not None:
            self.screen_w, self.screen_h = pyautogui.size()
        else:
            self.screen_w, self.screen_h = 1920, 1080
            log.warning(
                "[MouseWorker] PyAutoGUI not installed — mouse control disabled. "
                "Install with: pip install pyautogui"
            )
        self.mouse_down_state: dict[str, bool] = {}
        self.base_recovery_backoff_seconds = 0.05
        self.max_recovery_backoff_seconds = 1.0
        self.max_failures_before_long_backoff = 5
        self.max_failures_before_offline = 12
        self.consecutive_failures = 0
        self.recovering_until = 0.0
        self.last_error = ""
        self._slow_queue: queue.Queue = queue.Queue(maxsize=50)
        self._init_ok = False
        # Local cursor position tracking - avoids pyautogui.position() calls on every batch.
        # Initialized from pyautogui on first successful move, then accumulated with deltas.
        self._cursor_x = 0
        self._cursor_y = 0

        # Rate limiting for move events to prevent flooding X server
        self._last_move_time = 0.0
        self._min_move_interval = DEFAULT_MOVE_INTERVAL
        self._max_move_per_batch = MAX_MOVE_PER_BATCH
        self._move_count_last_sec = 0
        self._move_count_window_start = time.monotonic()
        self._max_moves_per_sec = MAX_MOVES_PER_SEC

        # Safety: auto-release stuck mouse buttons
        self._last_button_check = 0.0
        self._button_check_interval = 5.0  # Check every 5 seconds

    def get_engine_state(self) -> str:
        now = time.monotonic()
        if self.consecutive_failures >= self.max_failures_before_offline:
            return "offline"
        if now < self.recovering_until:
            return "recovering"
        if self.consecutive_failures > 0:
            return "degraded"
        return "healthy"

    def get_engine_status(self) -> dict:
        now = time.monotonic()
        return {
            "state": self.get_engine_state(),
            "consecutive_failures": self.consecutive_failures,
            "recovering_for_seconds": max(0.0, self.recovering_until - now),
            "last_error": self.last_error,
        }

    def _current_backoff(self) -> float:
        backoff = self.base_recovery_backoff_seconds * (
            2 ** max(0, self.consecutive_failures - 1)
        )
        if self.consecutive_failures >= self.max_failures_before_long_backoff:
            backoff = max(backoff, 0.5)
        return min(backoff, self.max_recovery_backoff_seconds)

    @staticmethod
    def _classify_input_error(err: Exception) -> str:
        e = str(err).lower()
        if any(
            k in e
            for k in ("access denied", "permission", "blocked", "uac", "privilege")
        ):
            return "degraded"
        if any(k in e for k in ("display", "screen", "monitor", "rdp", "disconnect")):
            return "failed"
        return "transient"

    def _drain_slow_ops(self) -> None:
        """Process all pending type/hotkey operations from _slow_queue."""
        while True:
            try:
                op_type, data = self._slow_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if op_type == "type":
                    with _pyautogui_lock:
                        try:
                            pyautogui.write(data)
                        except Exception as e:
                            log.debug(
                                "[MouseWorker] pyautogui.write failed, falling back to per-char: %s",
                                e,
                            )
                            for ch in data:
                                try:
                                    pyautogui.press(ch)
                                except Exception as e2:
                                    log.debug(
                                        "[MouseWorker] pyautogui.press failed for char %r: %s",
                                        ch,
                                        e2,
                                    )
                elif op_type == "hotkey":
                    if isinstance(data, str):
                        keys = [k.strip().lower() for k in data.split(",") if k.strip()]
                    else:
                        keys = list(data) if data else []
                    if keys:
                        with _pyautogui_lock:
                            pyautogui.hotkey(*keys)
            except Exception as e:
                log.warning("[MouseWorker] Slow op failed: %s", e)

    def enqueue(self, item: dict) -> None:
        """Thread-safe enqueue. Drops oldest items when full."""
        try:
            self.queue.put_nowait(dict(item))
        except queue.Full:
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(dict(item))
            except Exception as e:
                log.debug("[MouseWorker] queue overflow in enqueue: %s", e)

    def stop(self) -> None:
        self.running = False
        try:
            self.queue.put_nowait(_SENTINEL)
        except queue.Full:
            pass
        if pyautogui is None:
            return
        with _pyautogui_lock:
            for btn, held in self.mouse_down_state.items():
                if held:
                    try:
                        pyautogui.mouseUp(button=btn)
                    except Exception:
                        pass

    @staticmethod
    def _init_x11() -> tuple | None:
        """Create a thread-local X11 Display for lock-free moves."""
        try:
            from Xlib.display import Display as _X11Display  # type: ignore[import-untyped]
            from Xlib.ext.xtest import fake_input as _x11_fake  # type: ignore[import-untyped]
            from Xlib import X as _X11X  # type: ignore[import-untyped]

            return _X11Display(), _x11_fake, _X11X
        except Exception:
            return None

    def run(self) -> None:
        if pyautogui is None:
            log.warning("[MouseWorker] PyAutoGUI not available — mouse input disabled")
            return

        try:
            test_pos = pyautogui.position()
            self._init_ok = True
            log.info("[MouseWorker] Initialized OK (pyautogui position=%s)", test_pos)
        except Exception as e:
            self._init_ok = False
            log.warning("[MouseWorker] pyautogui failed to initialize: %s", e)

        x11 = self._init_x11()
        if x11:
            log.info("[MouseWorker] Direct X11 enabled for moves (no sync round-trip)")
        else:
            log.info("[MouseWorker] Using pyautogui for all operations")

        while self.running:
            try:
                now = time.monotonic()
                if now < self.recovering_until:
                    time.sleep(min(self.recovering_until - now, 0.1))
                    continue

                if not self._init_ok:
                    time.sleep(1.0)
                    try:
                        test_pos = pyautogui.position()
                        self._init_ok = True
                        log.info("[MouseWorker] pyautogui became available")
                    except Exception as e:
                        log.debug(
                            "[MouseWorker] pyautogui position check failed: %s", e
                        )
                    continue

                # Safety: periodically check and release stuck mouse buttons
                if now - self._last_button_check >= self._button_check_interval:
                    self._last_button_check = now
                    with _pyautogui_lock:
                        for btn, held in list(self.mouse_down_state.items()):
                            if held:
                                log.warning(
                                    "[MouseWorker] Safety: releasing stuck button %s",
                                    btn,
                                )
                                try:
                                    pyautogui.mouseUp(button=btn)
                                except Exception as e:
                                    log.warning(
                                        "[MouseWorker] pyautogui.mouseUp on stop failed: %s",
                                        e,
                                    )
                                self.mouse_down_state[btn] = False

                # ── Block until data arrives ─────────────────────────────
                try:
                    first = self.queue.get(timeout=0.005)
                except queue.Empty:
                    self._drain_slow_ops()
                    continue
                if first is _SENTINEL:
                    continue

                # Drain remaining items
                items = [first]
                while len(items) < 32:
                    try:
                        n = self.queue.get_nowait()
                        if n is _SENTINEL:
                            continue
                        items.append(n)
                    except queue.Empty:
                        break

                # ── Accumulate move deltas, batch everything else ─────────
                move_dx = 0
                move_dy = 0
                has_move = False
                queued_clicks: list[dict] = []
                queued_keys: list[str] = []
                queued_text_chunks: list[str] = []
                queued_hotkeys: list[list[str]] = []
                handled_any = False

                for item in items:
                    t = item.get("type")
                    if t == "move_relative":
                        move_dx += int(item.get("dx", 0))
                        move_dy += int(item.get("dy", 0))
                        has_move = True
                        handled_any = True
                    elif t == "move_absolute":
                        queued_clicks.append(
                            {
                                "func": "moveTo",
                                "x": int(float(item.get("dx", 0.5)) * self.screen_w),
                                "y": int(float(item.get("dy", 0.5)) * self.screen_h),
                            }
                        )
                        handled_any = True
                    elif t == "click":
                        queued_clicks.append(
                            {
                                "func": "click",
                                "button": item.get("button", "left"),
                                "clicks": item.get("clicks", 1),
                            }
                        )
                        handled_any = True
                    elif t == "mouse_down":
                        btn = item.get("button", "left")
                        if not self.mouse_down_state.get(btn, False):
                            queued_clicks.append({"func": "mouseDown", "button": btn})
                            self.mouse_down_state[btn] = True
                        handled_any = True
                    elif t == "mouse_up":
                        btn = item.get("button", "left")
                        if self.mouse_down_state.get(btn, False):
                            queued_clicks.append({"func": "mouseUp", "button": btn})
                            self.mouse_down_state[btn] = False
                        handled_any = True
                    elif t == "scroll":
                        queued_clicks.append(
                            {
                                "func": "scroll",
                                "amount": item.get("amount", 0),
                            }
                        )
                        handled_any = True
                    elif t == "key":
                        queued_keys.append(item.get("key", ""))
                        handled_any = True
                    elif t == "type":
                        text = item.get("text", "")
                        if text:
                            queued_text_chunks.append(text)
                            handled_any = True
                    elif t == "hotkey":
                        keys = item.get("keys", "")
                        if keys:
                            if isinstance(keys, str):
                                keys = [
                                    k.strip().lower()
                                    for k in keys.split(",")
                                    if k.strip()
                                ]
                            if platform.system() == "Darwin":
                                keys = ["cmd" if k == "win" else k for k in keys]
                            keys = ["del" if k == "delete" else k for k in keys]
                            if keys:
                                queued_hotkeys.append(keys)
                                handled_any = True

                # ── Execute moves ────────────────────────────────────────
                # Rate limit move events to prevent flooding X server
                now = time.monotonic()
                if has_move and (move_dx != 0 or move_dy != 0):
                    # Rate limit moves per second
                    if now - self._move_count_window_start >= 1.0:
                        self._move_count_window_start = now
                        self._move_count_last_sec = 0

                    if self._move_count_last_sec >= self._max_moves_per_sec:
                        # Drop this move batch - too many moves this second
                        pass
                    elif now - self._last_move_time >= self._min_move_interval:
                        # Clamp move delta to max per batch
                        move_dx = max(
                            -self._max_move_per_batch,
                            min(self._max_move_per_batch, move_dx),
                        )
                        move_dy = max(
                            -self._max_move_per_batch,
                            min(self._max_move_per_batch, move_dy),
                        )

                        if x11 is not None:
                            x11_display, fake_input, Xmod = x11
                            # Use locally tracked cursor position - avoids pyautogui.position()
                            # contention with screen_capture and eliminates an X round-trip per batch.
                            new_x = max(0, min(self.screen_w, self._cursor_x + move_dx))
                            new_y = max(0, min(self.screen_h, self._cursor_y + move_dy))
                            fake_input(x11_display, Xmod.MotionNotify, x=new_x, y=new_y)
                            x11_display.flush()
                            # Update local cursor after reporting (MotionNotify generates an event
                            # but doesn't actually reposition the real cursor).
                            self._cursor_x = new_x
                            self._cursor_y = new_y
                        else:
                            with _pyautogui_lock:
                                pyautogui.moveRel(move_dx, move_dy)

                        self._last_move_time = now
                        self._move_count_last_sec += 1

                # ── Execute clicks / keys under pyautogui lock ───────────
                _exec_count = 0
                _max_exec = 30
                if queued_clicks or queued_keys:
                    with _pyautogui_lock:
                        for c in queued_clicks:
                            if _exec_count >= _max_exec:
                                break
                            try:
                                if c["func"] == "moveTo":
                                    pyautogui.moveTo(c["x"], c["y"], duration=0)
                                elif c["func"] == "click":
                                    pyautogui.click(
                                        button=c["button"], clicks=c["clicks"]
                                    )
                                elif c["func"] == "mouseDown":
                                    pyautogui.mouseDown(button=c["button"])
                                elif c["func"] == "mouseUp":
                                    pyautogui.mouseUp(button=c["button"])
                                elif c["func"] == "scroll":
                                    pyautogui.scroll(c["amount"])
                                _exec_count += 1
                            except Exception as e:
                                log.warning("[MouseWorker] click/move failed: %s", e)

                        for k in queued_keys:
                            if _exec_count >= _max_exec:
                                break
                            try:
                                pyautogui.press(k)
                                _exec_count += 1
                            except Exception as e:
                                log.warning("[MouseWorker] key press failed: %s", e)

                # Defer slow operations
                if queued_text_chunks:
                    self._slow_queue.put(("type", "".join(queued_text_chunks)))
                for hk in queued_hotkeys:
                    self._slow_queue.put(("hotkey", hk))

                if handled_any and self.consecutive_failures:
                    self.consecutive_failures = 0
                    self.recovering_until = 0.0

                # Process deferred slow ops
                self._drain_slow_ops()

            except Exception as e:
                self.consecutive_failures += 1
                state = self._classify_input_error(e)
                backoff = self._current_backoff()
                self.recovering_until = time.monotonic() + backoff
                self.last_error = str(e)
                log.warning(
                    "[MouseWorker] %s input error: %s | failures=%d backoff=%.2fs",
                    state,
                    e,
                    self.consecutive_failures,
                    backoff,
                )
                time.sleep(backoff)
