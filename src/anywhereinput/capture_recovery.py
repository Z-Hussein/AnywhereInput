"""
Graceful Capture Engine Recovery on Crash
Handles pyautogui/pydirectinput crashes, display disconnections,
and input automation failures with exponential backoff.
"""

import asyncio
import logging
import threading
import time
import traceback
from enum import Enum, auto
from functools import wraps
from typing import Callable, Optional, Any

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pydirectinput
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    PYDIRECTINPUT_AVAILABLE = False

logger = logging.getLogger(__name__)


class EngineState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    RECOVERING = auto()
    FAILED = auto()
    OFFLINE = auto()


class CaptureEngineError(Exception):
    """Base exception for capture engine failures."""
    pass


class DisplayDisconnectedError(CaptureEngineError):
    """Raised when the display session is lost (RDP disconnect, lock screen, etc.)."""
    pass


class InputBlockedError(CaptureEngineError):
    """Raised when OS blocks synthetic input (UAC, secure desktop, etc.)."""
    pass


class CaptureEngineRecovery:
    """
    Singleton recovery manager for the input capture engine.
    Implements circuit-breaker pattern with automatic recovery.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.state = EngineState.HEALTHY
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None
        self.recovery_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Configurable thresholds
        self.max_failures_before_offline = 5
        self.base_backoff_seconds = 1.0
        self.max_backoff_seconds = 30.0
        self.health_check_interval = 5.0
        
        # Engine references
        self._pyautogui = None
        self._pydirectinput = None
        
        self._initialized = True
    
    def initialize(self, use_directinput: bool = False):
        """Initialize engine references."""
        if PYAUTOGUI_AVAILABLE:
            self._pyautogui = pyautogui
            # Safety settings
            self._pyautogui.FAILSAFE = True
            self._pyautogui.PAUSE = 0.01
        
        if PYDIRECTINPUT_AVAILABLE and use_directinput:
            self._pydirectinput = pydirectinput
            self._pydirectinput.FAILSAFE = False
            self._pydirectinput.PAUSE = 0.01
        
        logger.info(f"CaptureEngine initialized. State: {self.state.name}")
    
    @property
    def current_backoff(self) -> float:
        """Calculate current backoff with exponential decay."""
        if self.consecutive_failures == 0:
            return 0.0
        backoff = self.base_backoff_seconds * (2 ** (self.consecutive_failures - 1))
        return min(backoff, self.max_backoff_seconds)
    
    def _is_display_available(self) -> bool:
        """Check if we have a valid display context."""
        try:
            if self._pyautogui:
                # This will fail if no display/RDP disconnected
                _ = self._pyautogui.size()
                return True
        except Exception as e:
            logger.debug(f"Display check failed: {e}")
            return False
        return False
    
    def _is_input_allowed(self) -> bool:
        """Check if synthetic input is currently allowed."""
        try:
            if self._pyautogui:
                # Move to current position (no-op test)
                x, y = self._pyautogui.position()
                self._pyautogui.moveTo(x, y, duration=0)
                return True
        except Exception as e:
            logger.debug(f"Input check failed: {e}")
            return False
        return False
    
    async def health_check(self) -> EngineState:
        """
        Perform async health check of the capture engine.
        Returns current state without modifying it.
        """
        if self.state == EngineState.OFFLINE or self._shutdown:
            return EngineState.OFFLINE
        
        # Run blocking checks in thread pool
        loop = asyncio.get_event_loop()
        display_ok = await loop.run_in_executor(None, self._is_display_available)
        
        if not display_ok:
            return EngineState.FAILED
        
        input_ok = await loop.run_in_executor(None, self._is_input_allowed)
        if not input_ok:
            return EngineState.DEGRADED
            
        return EngineState.HEALTHY
    
    async def attempt_recovery(self) -> bool:
        """
        Attempt to recover the capture engine.
        Returns True if recovery succeeded.
        """
        if self.state == EngineState.RECOVERING:
            logger.warning("Recovery already in progress")
            return False
        
        self.state = EngineState.RECOVERING
        self.last_failure_time = time.time()
        
        logger.info(f"Starting recovery attempt {self.consecutive_failures + 1}, "
                   f"backoff: {self.current_backoff}s")
        
        # Wait for backoff period
        await asyncio.sleep(self.current_backoff)
        
        try:
            # Strategy 1: Re-initialize pyautogui
            if PYAUTOGUI_AVAILABLE:
                # Re-import to clear any cached bad state
                import importlib
                import pyautogui
                self._pyautogui = importlib.reload(pyautogui)
                self._pyautogui.FAILSAFE = True
            
            # Strategy 2: Check display again
            if not self._is_display_available():
                raise DisplayDisconnectedError("Display still unavailable after reload")
            
            # Strategy 3: Test input
            if not self._is_input_allowed():
                raise InputBlockedError("Input still blocked after reload")
            
            # Success!
            self.consecutive_failures = 0
            self.state = EngineState.HEALTHY
            logger.info("Capture engine recovery successful")
            return True
            
        except Exception as e:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            
            if self.consecutive_failures >= self.max_failures_before_offline:
                self.state = EngineState.OFFLINE
                logger.error(f"Engine marked OFFLINE after {self.consecutive_failures} failures")
            else:
                self.state = EngineState.FAILED
                logger.error(f"Recovery attempt failed: {e}")
            
            return False
    
    async def start_monitoring(self):
        """Start background health monitoring."""
        while not self._shutdown:
            try:
                if self.state in (EngineState.HEALTHY, EngineState.DEGRADED):
                    health = await self.health_check()
                    if health == EngineState.FAILED:
                        logger.error("Health check detected failure")
                        self.state = EngineState.FAILED
                        self.consecutive_failures += 1
                        asyncio.create_task(self.attempt_recovery())
                    elif health == EngineState.DEGRADED and self.state == EngineState.HEALTHY:
                        logger.warning("Engine degraded - input blocked but display OK")
                        self.state = EngineState.DEGRADED
                        
                elif self.state == EngineState.FAILED:
                    # Auto-trigger recovery if not already running
                    if not self.recovery_task or self.recovery_task.done():
                        self.recovery_task = asyncio.create_task(self.attempt_recovery())
                        
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
            
            await asyncio.sleep(self.health_check_interval)
    
    def shutdown(self):
        """Graceful shutdown."""
        self._shutdown = True
        if self.recovery_task and not self.recovery_task.done():
            self.recovery_task.cancel()
        self.state = EngineState.OFFLINE
        logger.info("CaptureEngineRecovery shutdown complete")


def with_recovery(fallback: Optional[Callable] = None):
    """
    Decorator for capture operations with automatic recovery.
    
    Usage:
        @with_recovery(fallback=noop)
        async def move_mouse(x, y):
            pyautogui.moveTo(x, y)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            recovery = CaptureEngineRecovery()
            
            # If offline, reject immediately
            if recovery.state == EngineState.OFFLINE:
                logger.warning(f"Engine offline, rejecting call to {func.__name__}")
                if fallback:
                    return fallback(*args, **kwargs)
                raise CaptureEngineError("Capture engine is offline")
            
            # If recovering, wait a bit
            if recovery.state == EngineState.RECOVERING:
                await asyncio.sleep(0.5)
            
            try:
                result = await func(*args, **kwargs)
                # Reset failures on success
                if recovery.consecutive_failures > 0:
                    recovery.consecutive_failures = 0
                    recovery.state = EngineState.HEALTHY
                return result
                
            except Exception as e:
                recovery.consecutive_failures += 1
                recovery.last_failure_time = time.time()
                
                # Classify error
                error_str = str(e).lower()
                if any(x in error_str for x in ['display', 'screen', 'rdp', 'disconnect']):
                    recovery.state = EngineState.FAILED
                    logger.error(f"Display error in {func.__name__}: {e}")
                elif any(x in error_str for x in ['access denied', 'blocked', 'uac', 'privilege']):
                    recovery.state = EngineState.DEGRADED
                    logger.warning(f"Input blocked in {func.__name__}: {e}")
                else:
                    recovery.state = EngineState.FAILED
                    logger.error(f"Capture error in {func.__name__}: {e}")
                
                # Trigger async recovery
                asyncio.create_task(recovery.attempt_recovery())
                
                if fallback:
                    return fallback(*args, **kwargs)
                raise CaptureEngineError(f"Capture failed: {e}") from e
                
        return wrapper
    return decorator


# Convenience fallback functions
def noop(*args, **kwargs):
    """No-op fallback."""
    return None

def queued_command(*args, **kwargs):
    """Queue command for later execution when engine recovers."""
    # Implementation depends on your command queue system
    logger.info(f"Command queued for recovery: {args}, {kwargs}")
    return {"status": "queued", "message": "Engine recovering, command queued"}
