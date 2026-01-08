"""
Debounced button widget to prevent double-clicks and rapid clicking.
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """Button that prevents double-clicks and rapid clicking (debouncing)"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_release_time = 0
        self._debounce_interval = 0.3  # 300ms debounce - only prevent rapid successive releases
        self._active_touch = None  # Track the current active touch
    
    def on_touch_down(self, touch):
        """Handle touch down - always allow, but track the touch"""
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        # Always allow touch_down to proceed - button needs to enter pressed state
        # Store this touch as the active one
        self._active_touch = touch.uid
        
        # Allow the touch to proceed normally - button will enter pressed state
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        """Handle touch up - debounce rapid successive releases"""
        if not self.collide_point(*touch.pos):
            # If touch moved outside button, clean up
            if self._active_touch == touch.uid:
                self._active_touch = None
            return super().on_touch_up(touch)
        
        # Only process release if it matches the stored touch ID
        # This ensures we only process releases from touches that started on this button
        if self._active_touch != touch.uid:
            return True  # Ignore release from touch that didn't start on this button
        
        # Clear the active touch
        self._active_touch = None
        
        # Check for rapid successive releases (debounce)
        current_time = time.monotonic()
        if current_time - self._last_release_time < self._debounce_interval:
            return True  # Consume the event - too soon after last release
        
        # Update last release time
        self._last_release_time = current_time
        
        # Allow the release to proceed normally - this will trigger on_release
        return super().on_touch_up(touch)

