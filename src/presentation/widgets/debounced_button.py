"""
Debounced button widget to prevent user double-clicks.

Note: Hardware-level duplicate events are already handled by GlobalInputFilter.
This widget only prevents intentional user double-clicks (rapid successive clicks).
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """
    Button that prevents user double-clicks.
    
    Hardware duplicates are handled by GlobalInputFilter (0.15s, 8px threshold).
    This widget prevents intentional user double-clicks with a longer threshold (0.3s).
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_release_time = 0
        self._debounce_interval = 0.3  # 300ms - prevents user double-clicks (longer than hardware filter)
    
    def on_touch_down(self, touch):
        """Handle touch down - always allow to proceed"""
        # Always allow touch_down - GlobalInputFilter handles hardware duplicates
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        """Handle touch up - debounce rapid successive user clicks"""
        if not self.collide_point(*touch.pos):
            return super().on_touch_up(touch)
        
        # Check for rapid successive releases (user double-clicks)
        # GlobalInputFilter already handles hardware duplicates, so this is for intentional clicks
        current_time = time.monotonic()
        if current_time - self._last_release_time < self._debounce_interval:
            return True  # Consume the event - too soon after last release (user double-click)
        
        # Update last release time
        self._last_release_time = current_time
        
        # Allow the release to proceed normally - this will trigger on_release
        return super().on_touch_up(touch)

