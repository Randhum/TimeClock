"""
Debounced button widget to prevent double-clicks.
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """Button that prevents double-clicks (debouncing)"""
    
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        # Check for rapid successive touches (global debounce)
        current_time = time.time()
        if hasattr(self, '_last_touch_time'):
            if current_time - self._last_touch_time < 0.3:  # 300ms debounce
                return True  # Consume the event without action
        self._last_touch_time = current_time
        
        return super().on_touch_down(touch)

