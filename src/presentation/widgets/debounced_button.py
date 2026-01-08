"""
Debounced button widget to prevent user double-clicks.

Note: Hardware-level duplicate events are handled by OS/Kivy.
This widget only prevents intentional user double-clicks (rapid successive clicks).
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """
    Button that prevents user double-clicks.
    
    Only prevents intentional rapid clicks (UX concern).
    OS/Kivy handles hardware-level duplicate events.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_release_time = None  # None = no previous release
        self._debounce_interval = 0.3  # 300ms for user double-clicks
    
    def on_touch_down(self, touch):
        """Handle touch down - always allow to proceed"""
        # Always allow touch_down - no filtering needed
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        """Handle touch up - debounce rapid successive user clicks"""
        """Handle touch up - debounce rapid successive user clicks"""
        if not self.collide_point(*touch.pos):
            return super().on_touch_up(touch)
        
        current_time = time.monotonic()
        
        # First click always works
        if self._last_release_time is None:
            self._last_release_time = current_time
            return super().on_touch_up(touch)
        
        # Block rapid double-clicks
        if current_time - self._last_release_time < self._debounce_interval:
            return True  # Block double-click
        
        # Update last release time
        self._last_release_time = current_time
        return super().on_touch_up(touch)

