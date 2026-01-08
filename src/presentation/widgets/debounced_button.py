"""
Debounced button widget to prevent double-clicks and rapid clicking.
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """Button that prevents double-clicks and rapid clicking (debouncing)"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_touch_time = 0
        self._last_release_time = 0
        self._debounce_interval = 0.5  # 500ms debounce for both touch and release
        self._touch_id = None  # Track which touch is valid
    
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        # Check for rapid successive touches (debounce)
        current_time = time.time()
        if current_time - self._last_touch_time < self._debounce_interval:
            return True  # Consume the event without action
        
        self._last_touch_time = current_time
        self._touch_id = touch.uid  # Store touch ID to validate release
        
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_up(touch)
        
        # Only process release if it matches the stored touch ID
        if self._touch_id != touch.uid:
            return True  # Ignore release from different touch
        
        # Check for rapid successive releases (debounce)
        current_time = time.time()
        if current_time - self._last_release_time < self._debounce_interval:
            self._touch_id = None  # Clear touch ID
            return True  # Consume the event without action
        
        self._last_release_time = current_time
        self._touch_id = None  # Clear touch ID after valid release
        
        return super().on_touch_up(touch)
