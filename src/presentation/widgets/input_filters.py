"""
Global input filters for touchscreen and keyboard deduplication.
"""
import time


class GlobalInputFilter:
    """
    Brute-force, app-wide input de-duplicator for all touch events
    (buttons, VKeyboard keys, etc.). Any touch that lands within
    a small distance/time window of the previous touch is swallowed.
    """
    
    def __init__(self, window, time_threshold=0.15, distance_threshold=8):
        self.window = window
        self.time_threshold = time_threshold  # Reduced from 0.3 to 0.15 to be less aggressive
        self.distance_threshold = distance_threshold
        self._last_event = None

    def install(self):
        """Install the filter on the window"""
        # Bind to all touch events; returning True stops propagation
        self.window.bind(on_touch_down=self._filter_touch)
        self.window.bind(on_touch_move=self._filter_touch)
        self.window.bind(on_touch_up=self._filter_touch)

    def _filter_touch(self, window, touch):
        """Filter touch events to prevent duplicates"""
        now = time.monotonic()
        dev = getattr(touch, 'device', '')
        pos = touch.pos if hasattr(touch, 'pos') else (0, 0)

        if self._last_event:
            dt = now - self._last_event['time']
            dx = abs(pos[0] - self._last_event['pos'][0])
            dy = abs(pos[1] - self._last_event['pos'][1])
            same_dev = dev == self._last_event['dev']
            if same_dev and dt < self.time_threshold and dx < self.distance_threshold and dy < self.distance_threshold:
                return True  # Swallow duplicate

        self._last_event = {'time': now, 'pos': pos, 'dev': dev}
        return False


class GlobalKeyFilter:
    """
    Global de-duplication for keyboard/VKeyboard input (text + function keys).
    Any identical token (character or key name) within the debounce window is swallowed.
    """
    
    def __init__(self, window, time_threshold=0.25):
        self.window = window
        self.time_threshold = time_threshold
        self._last_token = None  # (token, timestamp)

    def install(self):
        """Install the filter on the window"""
        # Bind both text input and key_down to catch chars and function keys
        self.window.bind(on_textinput=self._on_textinput)
        self.window.bind(on_key_down=self._on_key_down)
        self.window.bind(on_key_up=self._on_key_up)

    def _should_swallow(self, token):
        """Check if token should be swallowed (duplicate)"""
        now = time.monotonic()
        if self._last_token:
            last_tok, last_time = self._last_token
            if token == last_tok and (now - last_time) < self.time_threshold:
                return True
        self._last_token = (token, now)
        return False

    def _on_textinput(self, window, text):
        """Handle text input events"""
        if not text:
            return False
        return self._should_swallow(text)

    def _on_key_down(self, window, keycode, scancode, codepoint, modifiers):
        """Handle key down events"""
        # keycode is (code, name)
        name = keycode[1] if keycode and len(keycode) > 1 else str(keycode)
        token = name or ''
        # Normalize shift variants to one token to catch duplicate shift presses
        if name in ('shift', 'lshift', 'rshift', 'capslock'):
            token = '__SHIFT__'
        if not token:
            return False
        return self._should_swallow(token)

    def _on_key_up(self, window, keycode):
        """Handle key up events"""
        # Apply same logic on key_up to catch rapid duplicate ups
        name = keycode[1] if keycode and len(keycode) > 1 else str(keycode)
        token = name or ''
        if name in ('shift', 'lshift', 'rshift', 'capslock'):
            token = '__SHIFT__'
        if not token:
            return False
        return self._should_swallow(token)

