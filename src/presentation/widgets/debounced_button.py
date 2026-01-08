"""
Debounced button widget to prevent double-clicks and rapid clicking.
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """Button that prevents double-clicks and rapid clicking (debouncing)"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_click_time = 0
        self._debounce_interval = 0.3  # 300ms debounce between completed clicks
        self._active_touches = {}  # Track active touches: {touch.uid: touch_down_time}
    
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        # Check for rapid successive clicks (debounce based on last click completion)
        current_time = time.monotonic()
        if current_time - self._last_click_time < self._debounce_interval:
            return True  # Consume the event - too soon after last click
        
        # Store this touch and its start time
        self._active_touches[touch.uid] = current_time
        
        # Allow the touch to proceed normally - button will enter pressed state
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos):
            # If touch moved outside button, clean up
            if touch.uid in self._active_touches:
                del self._active_touches[touch.uid]
            return super().on_touch_up(touch)
        
        # Only process release if it matches a stored touch ID
        # This ensures we only process releases from touches that started on this button
        if touch.uid not in self._active_touches:
            return True  # Ignore release from touch that didn't start on this button
        
        # Remove the touch from active touches
        del self._active_touches[touch.uid]
        
        # Update last click time to prevent rapid successive clicks
        # This debounces the NEXT click, not the current one
        current_time = time.monotonic()
        self._last_click_time = current_time
        
        # Allow the release to proceed normally - this will trigger on_release
        return super().on_touch_up(touch)

