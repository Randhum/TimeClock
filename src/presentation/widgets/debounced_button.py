"""
Debounced button widget to prevent double-clicks and rapid clicking.
"""
import time
from kivy.uix.button import Button


class DebouncedButton(Button):
    """
    Button that prevents rapid double-clicks.
    
    Only debounces completed click actions (on_release), not individual touch events.
    This ensures touch_down/touch_up pairing works correctly.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_action_time = 0
        self._debounce_interval = 0.5  # 500ms between completed clicks
    
    def on_release(self):
        """Debounce at the action level, not the touch level"""
        current_time = time.time()
        
        # Block rapid successive clicks
        if current_time - self._last_action_time < self._debounce_interval:
            return  # Ignore this click, don't call super
        
        self._last_action_time = current_time
        return super().on_release()
