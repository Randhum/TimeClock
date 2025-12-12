"""
Popup service for centralized popup management.
"""
import logging
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import Clock

from ..presentation.popups.greeter_popup import GreeterPopup

logger = logging.getLogger(__name__)


class PopupService:
    """Centralized popup management"""
    
    def __init__(self):
        """Initialize popup service"""
        pass
    
    def show_info(self, title: str, message: str, duration: float = 3.0):
        """
        Show informational popup.
        
        Args:
            title: Popup title
            message: Popup message
            duration: Auto-dismiss duration in seconds
        """
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), duration)
    
    def show_error(self, title: str, message: str, duration: float = 5.0):
        """
        Show error popup.
        
        Args:
            title: Popup title
            message: Error message
            duration: Auto-dismiss duration in seconds
        """
        popup = Popup(
            title=title,
            content=Label(text=message, color=(1, 0, 0, 1)),  # Red text
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), duration)
    
    def show_success(self, title: str, message: str, duration: float = 3.0):
        """
        Show success popup.
        
        Args:
            title: Popup title
            message: Success message
            duration: Auto-dismiss duration in seconds
        """
        popup = Popup(
            title=title,
            content=Label(text=message, color=(0, 1, 0, 1)),  # Green text
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), duration)
    
    def show_greeter(self, employee, action: str):
        """
        Show greeter popup.
        
        Args:
            employee: Employee object
            action: 'in' or 'out'
        """
        # Import here to avoid circular imports
        from ..presentation.popups.greeter_popup import GreeterPopup
        GreeterPopup(employee, action).open()

