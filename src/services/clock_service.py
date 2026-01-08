"""
Clock service for handling clock in/out business logic.
"""
import logging
from typing import Optional
from dataclasses import dataclass

from ..data.database import TimeEntry, create_time_entry, create_time_entry_atomic
from ..utils.errors import DatabaseError, InvalidActionError

logger = logging.getLogger(__name__)


@dataclass
class ClockResult:
    """Result of a clock action"""
    success: bool
    action: str
    employee: object
    entry: Optional[object] = None
    error: Optional[str] = None


class ClockService:
    """Handles clock in/out business logic"""
    
    def __init__(self, rfid_provider=None, popup_service=None, state_service=None):
        """
        Initialize clock service.
        
        Args:
            rfid_provider: RFID provider for LED feedback
            popup_service: PopupService for showing notifications
            state_service: StateService for managing application state
        """
        self.rfid = rfid_provider
        self.popup_service = popup_service
        self.state_service = state_service
    
    def clock_in_out(self, employee) -> ClockResult:
        """
        Perform clock action for employee.
        Uses atomic operation to prevent race conditions between action determination and entry creation.
        
        Args:
            employee: Employee to clock in/out
            
        Returns:
            ClockResult with action details
        """
        try:
            # Atomically determine action and create entry to prevent race conditions
            # This ensures no other clock operation can interfere between determination and creation
            entry, action = create_time_entry_atomic(employee)
            
            logger.info(f"Clocked {action.upper()} - {employee.name}")
            
            # Signal success via RFID if available
            if self.rfid:
                self.rfid.indicate_success()
            
            # Update state using state service
            if self.state_service:
                self.state_service.set_last_clocked_employee(employee)
            
            result = ClockResult(
                success=True,
                action=action,
                employee=employee,
                entry=entry
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing clock action: {e}")
            
            # Signal error via RFID if available
            if self.rfid:
                self.rfid.indicate_error()
            
            # Show error popup using popup service
            if self.popup_service:
                self.popup_service.show_error("Error", f"Failed to record time: {str(e)}")
            
            return ClockResult(
                success=False,
                action='',
                employee=employee,
                error=str(e)
            )
    
    def _determine_action(self, last_entry: Optional[TimeEntry]) -> str:
        """
        Determine next action based on last entry.
        
        Args:
            last_entry: Last time entry for employee, or None
            
        Returns:
            'in' or 'out'
        """
        if not last_entry or last_entry.action == 'out':
            return 'in'
        return 'out'

