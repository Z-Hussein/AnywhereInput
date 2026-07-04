"""
Windows-specific recovery for display session issues.
Handles RDP disconnections, session locks, and UAC prompts.
"""

import ctypes
import logging
import os
import subprocess
from ctypes import wintypes

logger = logging.getLogger(__name__)

# Windows constants
WTS_CURRENT_SERVER_HANDLE = None
WTS_CURRENT_SESSION = -1
WTS_SESSIONSTATE_LOCK = 0x0
WTS_SESSIONSTATE_UNLOCK = 0x1

class WindowsDisplayRecovery:
    """Windows-specific display session recovery."""
    
    def __init__(self):
        self._wtsapi32 = None
        self._user32 = None
        self._kernel32 = None
        self._load_windows_apis()
    
    def _load_windows_apis(self):
        """Load required Windows APIs."""
        try:
            self._wtsapi32 = ctypes.WinDLL('wtsapi32')
            self._user32 = ctypes.WinDLL('user32')
            self._kernel32 = ctypes.WinDLL('kernel32')
        except Exception as e:
            logger.warning(f"Could not load Windows APIs: {e}")
    
    def is_session_locked(self) -> bool:
        """Check if current Windows session is locked."""
        if not self._wtsapi32:
            return False
            
        try:
            from ctypes import byref, c_int
            
            session_id = wintypes.DWORD()
            cb_session_id = wintypes.DWORD(ctypes.sizeof(session_id))
            
            # Get current session ID
            if not self._wtsapi32.WTSQuerySessionInformationW(
                WTS_CURRENT_SERVER_HANDLE,
                WTS_CURRENT_SESSION,
                16,  # WTSConnectState
                ctypes.byref(session_id),
                ctypes.byref(cb_session_id)
            ):
                return False
            
            # WTSActive = 0, WTSConnected = 1, WTSConnectQuery = 2, 
            # WTSShadow = 3, WTSDisconnected = 4, WTSIdle = 5, 
            # WTSListen = 6, WTSReset = 7, WTSDown = 8, WTSInit = 9
            state = session_id.value
            self._wtsapi32.WTSFreeMemory(session_id)
            
            return state in (4, 5)  # Disconnected or Idle (locked)
            
        except Exception as e:
            logger.error(f"Session lock check failed: {e}")
            return False
    
    def is_uac_active(self) -> bool:
        """Detect if UAC secure desktop is active."""
        try:
            # Check for consent UI window
            hwnd = self._user32.FindWindowW("ConsentPromptDialog", None)
            if hwnd:
                return True
            
            # Check for credential dialog
            hwnd = self._user32.FindWindowW("Credential Dialog Xaml Host", None)
            if hwnd:
                return True
                
            return False
        except Exception:
            return False
    
    def get_session_user(self) -> str:
        """Get current session username."""
        try:
            buffer = ctypes.c_wchar_p()
            size = wintypes.DWORD()
            
            if self._wtsapi32.WTSQuerySessionInformationW(
                WTS_CURRENT_SERVER_HANDLE,
                WTS_CURRENT_SESSION,
                5,  # WTSUserName
                ctypes.byref(buffer),
                ctypes.byref(size)
            ):
                user = buffer.value
                self._wtsapi32.WTSFreeMemory(buffer)
                return user
        except Exception:
            pass
        return ""
    
    def attempt_session_recovery(self) -> bool:
        """
        Attempt to recover display session.
        This may involve sending a simulated input to wake the session.
        """
        try:
            # Simulate mouse move 0,0 to wake session
            self._user32.mouse_event(0x0001, 0, 0, 0, 0)  # MOUSEEVENTF_MOVE
            return True
        except Exception as e:
            logger.error(f"Session recovery failed: {e}")
            return False


def get_display_recovery():
    """Factory for platform-specific recovery."""
    if os.name == 'nt':
        return WindowsDisplayRecovery()
    # Linux/Mac could use xprintidle, xdotool, etc.
    return None
