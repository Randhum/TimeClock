"""
Popup service for centralized popup management.
"""
import logging
import threading
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import Clock

from ..presentation.popups.greeter_popup import GreeterPopup

logger = logging.getLogger(__name__)


class PopupService:
    """Centralized popup management with proper cleanup and thread safety"""
    
    def __init__(self):
        """Initialize popup service"""
        self._open_popups = []  # Track all open popups
        self._current_main_popup = None  # Track the main popup (non-nested)
        self._dismissing_popups = set()  # Track popups currently being dismissed
        self._lock = threading.Lock()  # Lock for thread-safe operations
    
    def _register_popup(self, popup, is_main=False):
        """Register a popup for tracking (thread-safe)"""
        with self._lock:
            # Don't register if popup is already being dismissed
            if popup in self._dismissing_popups:
                logger.warning(f"Attempted to register popup that is being dismissed: {popup}")
                return
            
            # Don't register if popup is already registered and open
            if popup in self._open_popups:
                if hasattr(popup, 'is_open') and popup.is_open:
                    logger.debug(f"Popup already registered and open: {popup}")
                    return
            
            if popup not in self._open_popups:
                self._open_popups.append(popup)
                # Bind to dismiss event to clean up
                popup.bind(on_dismiss=lambda instance: self._unregister_popup(instance))
            
            if is_main:
                # Close previous main popup if exists
                if self._current_main_popup and self._current_main_popup != popup:
                    self._force_dismiss(self._current_main_popup)
                self._current_main_popup = popup
    
    def _unregister_popup(self, popup):
        """Unregister a popup when it's dismissed (thread-safe)"""
        with self._lock:
            if popup in self._open_popups:
                self._open_popups.remove(popup)
            if popup in self._dismissing_popups:
                self._dismissing_popups.discard(popup)
            if self._current_main_popup == popup:
                self._current_main_popup = None
    
    def _force_dismiss(self, popup):
        """Force dismiss a popup, ensuring it's fully closed (thread-safe)"""
        if not popup:
            return
        
        with self._lock:
            # Check if already being dismissed
            if popup in self._dismissing_popups:
                logger.debug(f"Popup already being dismissed: {popup}")
                return
            
            # Mark as being dismissed
            self._dismissing_popups.add(popup)
        
        # Dismiss outside lock to avoid blocking
        try:
            if hasattr(popup, 'is_open') and popup.is_open:
                popup.dismiss()
            # Schedule a cleanup check
            Clock.schedule_once(lambda dt: self._cleanup_popup(popup), 0.1)
        except Exception as e:
            logger.warning(f"Error dismissing popup: {e}")
            # Still cleanup even if dismiss failed
            with self._lock:
                self._dismissing_popups.discard(popup)
    
    def _cleanup_popup(self, popup):
        """Final cleanup check for popup"""
        if popup and popup.is_open:
            try:
                popup.dismiss()
            except:
                pass
        self._unregister_popup(popup)
    
    def close_all_popups(self, except_popup=None):
        """Close all open popups except the specified one (thread-safe)"""
        with self._lock:
            # Create a copy of the list to avoid modification during iteration
            popups_to_close = [p for p in list(self._open_popups) if p != except_popup]
        
        # Dismiss outside lock
        for popup in popups_to_close:
            self._force_dismiss(popup)
    
    def close_main_popup(self):
        """Close the current main popup (thread-safe)"""
        with self._lock:
            main_popup = self._current_main_popup
        
        if main_popup:
            self._force_dismiss(main_popup)
    
    def show_info(self, title: str, message: str, duration: float = 3.0):
        """
        Show informational popup.
        
        Args:
            title: Popup title
            message: Popup message
            duration: Auto-dismiss duration in seconds
        """
        # Close any existing info/error/success popups
        self._close_simple_popups()
        
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=True
        )
        self._register_popup(popup, is_main=False)
        
        # Only open if not already open
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
        Clock.schedule_once(lambda dt: self._safe_dismiss(popup), duration)
    
    def _close_simple_popups(self):
        """Close simple notification popups (thread-safe)"""
        with self._lock:
            # Create a copy to avoid modification during iteration
            popups_to_close = [
                p for p in list(self._open_popups)
                if hasattr(p, 'title') and p.title in ['Info', 'Error', 'Erfolg', 'Success']
            ]
        
        # Dismiss outside lock
        for popup in popups_to_close:
            self._force_dismiss(popup)
    
    def _safe_dismiss(self, popup):
        """Safely dismiss a popup"""
        if popup and popup.is_open:
            popup.dismiss()
    
    def show_error(self, title: str, message: str, duration: float = 5.0):
        """
        Show error popup.
        
        Args:
            title: Popup title
            message: Error message
            duration: Auto-dismiss duration in seconds
        """
        # Close any existing info/error/success popups
        self._close_simple_popups()
        
        popup = Popup(
            title=title,
            content=Label(text=message, color=(1, 0, 0, 1)),  # Red text
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=True
        )
        self._register_popup(popup, is_main=False)
        
        # Only open if not already open
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
        Clock.schedule_once(lambda dt: self._safe_dismiss(popup), duration)
    
    def show_success(self, title: str, message: str, duration: float = 3.0):
        """
        Show success popup.
        
        Args:
            title: Popup title
            message: Success message
            duration: Auto-dismiss duration in seconds
        """
        # Close any existing info/error/success popups
        self._close_simple_popups()
        
        popup = Popup(
            title=title,
            content=Label(text=message, color=(0, 1, 0, 1)),  # Green text
            size_hint=(None, None),
            size=(400, 200),
            auto_dismiss=True
        )
        self._register_popup(popup, is_main=False)
        
        # Only open if not already open
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
        Clock.schedule_once(lambda dt: self._safe_dismiss(popup), duration)
    
    def show_greeter(self, employee, action: str):
        """
        Show greeter popup.
        
        Args:
            employee: Employee object
            action: 'in' or 'out'
        """
        # Import here to avoid circular imports
        from ..presentation.popups.greeter_popup import GreeterPopup
        
        # Close any existing greeter popups (thread-safe)
        with self._lock:
            greeter_popups = [p for p in list(self._open_popups) if isinstance(p, GreeterPopup)]
        
        for popup in greeter_popups:
            self._force_dismiss(popup)
        
        popup = GreeterPopup(employee, action)
        self._register_popup(popup, is_main=False)
        
        # Only open if not already open
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
    
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
        close_btn.bind(on_release=lambda *_: self._safe_dismiss(popup))
        self._register_popup(popup, is_main=True)
        
        # Only open if not already open
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()

