"""
Application state management service.
Manages application-wide state like last clocked employee, pending identifications, etc.
"""
import time
import logging
from typing import Optional, Dict, Tuple
from kivy.clock import Clock

logger = logging.getLogger(__name__)


class PendingIdentification:
    """Represents a pending badge identification"""
    def __init__(self, action_type: str, popup=None):
        self.action_type = action_type
        self.popup = popup


class StateService:
    """Manages application state"""
    
    def __init__(self):
        self._last_clocked_employee: Optional[object] = None
        self._pending_identification: Optional[PendingIdentification] = None
        self._recent_scan_times: Dict[str, float] = {}
        self._employee_timeout_event = None
        self.SCAN_DEBOUNCE_SECONDS = 1.2
        self.EMPLOYEE_TIMEOUT_SECONDS = 120
    
    @property
    def last_clocked_employee(self):
        """Get the last clocked employee"""
        return self._last_clocked_employee
    
    def set_last_clocked_employee(self, employee, timeout: Optional[int] = None):
        """Set last clocked employee with optional timeout"""
        self._last_clocked_employee = employee
        timeout = timeout or self.EMPLOYEE_TIMEOUT_SECONDS
        self._reset_clocked_employee_timer(timeout)
    
    def clear_last_clocked_employee(self):
        """Clear last clocked employee"""
        self._last_clocked_employee = None
        if self._employee_timeout_event:
            self._employee_timeout_event.cancel()
            self._employee_timeout_event = None
    
    def _reset_clocked_employee_timer(self, timeout: int):
        """Reset timer that clears last_clocked_employee after inactivity"""
        if self._employee_timeout_event:
            self._employee_timeout_event.cancel()
        self._employee_timeout_event = Clock.schedule_once(
            lambda dt: self.clear_last_clocked_employee(),
            timeout
        )
    
    def is_recent_scan(self, tag_id: str, threshold: Optional[float] = None) -> bool:
        """Check if scan is within debounce threshold"""
        threshold = threshold or self.SCAN_DEBOUNCE_SECONDS
        now = time.monotonic()
        last_scan = self._recent_scan_times.get(tag_id, 0)
        
        if now - last_scan < threshold:
            return True
        
        self._recent_scan_times[tag_id] = now
        return False
    
    def record_scan(self, tag_id: str):
        """Record a scan timestamp"""
        self._recent_scan_times[tag_id] = time.monotonic()
    
    @property
    def pending_identification(self) -> Optional[PendingIdentification]:
        """Get pending identification"""
        return self._pending_identification
    
    def set_pending_identification(self, action_type: str, popup=None):
        """Set pending identification"""
        self._pending_identification = PendingIdentification(action_type, popup)
    
    def clear_pending_identification(self):
        """Clear pending identification"""
        if self._pending_identification and self._pending_identification.popup:
            try:
                self._pending_identification.popup.dismiss()
            except:
                pass
        self._pending_identification = None

