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
    
    def show_report(self, title: str, report_text: str, size_hint=(0.95, 0.95)):
        """
        Show report popup with scrollable content.
        
        Args:
            title: Popup title
            report_text: Report text content
            size_hint: Size hint tuple for popup (default: (0.95, 0.95))
        """
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.scrollview import ScrollView
        from ..presentation.widgets import DebouncedButton
        
        # Create scrollable content
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            bar_width=10
        )
        
        label = Label(
            text=report_text,
            font_size='16sp',
            halign='left',
            valign='top',
            size_hint_y=None,
            text_size=(460, None),
            markup=True
        )
        # Bind height to texture size for proper scrolling
        label.bind(texture_size=lambda inst, size: setattr(inst, 'height', size[1]))
        
        scroll.add_widget(label)
        content.add_widget(scroll)
        
        # Add close button
        close_btn = DebouncedButton(
            text="Schließen",
            size_hint_y=None,
            height='50dp',
            background_color=(0.3, 0.6, 0.9, 1)
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=size_hint,
            auto_dismiss=True
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

