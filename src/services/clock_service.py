"""
Clock service for handling clock in/out business logic.
"""
import logging
from typing import Optional
from dataclasses import dataclass

from ..database import TimeEntry, create_time_entry
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
    
    def __init__(self, rfid_provider=None):
        """
        Initialize clock service.
        
        Args:
            rfid_provider: RFID provider for LED feedback
        """
        self.rfid = rfid_provider
    
    def clock_in_out(self, employee) -> ClockResult:
        """
        Perform clock action for employee.
        
        Args:
            employee: Employee to clock in/out
            
        Returns:
            ClockResult with action details
        """
        try:
            # Find last entry
            last_entry = TimeEntry.get_last_for_employee(employee)
            
            # Determine action
            action = self._determine_action(last_entry)
            
            # Create time entry
            entry = create_time_entry(employee, action)
            
            logger.info(f"Clocked {action.upper()} - {employee.name}")
            
            # Signal success via RFID if available
            if self.rfid:
                self.rfid.indicate_success()
            
            return ClockResult(
                success=True,
                action=action,
                employee=employee,
                entry=entry
            )
            
        except Exception as e:
            logger.error(f"Error performing clock action: {e}")
            
            # Signal error via RFID if available
            if self.rfid:
                self.rfid.indicate_error()
            
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

