"""
Filtered text input widget to fix double-typing issues.
"""
from kivy.uix.textinput import TextInput


class FilteredTextInput(TextInput):
    """TextInput that filters duplicate characters to fix double-typing issue"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._input_counter = 0
    
    def insert_text(self, substring, from_undo=False):
        # Filter duplicate characters by only accepting every other input
        # This fixes the double-typing issue by "slicing" input in half
        if from_undo:
            # Always allow undo operations
            return super().insert_text(substring, from_undo)
        
        # For multi-character input (paste), process normally but still filter
        if len(substring) > 1:
            # For pasted text, accept it but reset counter
            self._input_counter = 0
            return super().insert_text(substring, from_undo)
        
        # Increment counter and only insert every other character
        self._input_counter += 1
        if self._input_counter % 2 == 0:
            # Skip this input (it's a duplicate)
            return
        
        # Insert the character
        return super().insert_text(substring, from_undo)
    
    def on_focus(self, instance, value):
        # Reset counter when focus changes
        if value:
            self._input_counter = 0
        # on_focus is a property callback, not a method - no need to call super()
    
    def do_backspace(self, from_undo=False, mode='bkspc'):
        # Reset counter when backspace is used
        self._input_counter = 0
        return super().do_backspace(from_undo, mode)

