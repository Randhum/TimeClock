"""
Time picker popup for selecting times - Chains hour and minute pickers.
"""
import datetime
import logging
from kivy.clock import Clock

from .hour_picker_popup import HourPickerPopup
from .minute_picker_popup import MinutePickerPopup

logger = logging.getLogger(__name__)


class TimePickerPopup:
    """Time picker that chains hour and minute selection"""
    
    def __init__(self, current_time=None, on_select=None, **kwargs):
        self.on_select_callback = on_select
        now = current_time or datetime.datetime.now().time()
        self.selected_hour = now.hour
        self.selected_minute = (now.minute // 5) * 5  # round to 5 minutes
    
    def _open_hour_picker(self):
        """Open hour picker first"""
        HourPickerPopup(
            current_hour=self.selected_hour,
            on_select=self._on_hour_selected
        ).open()
    
    def _on_hour_selected(self, hour):
        """Called when hour is selected, open minute picker"""
        self.selected_hour = hour
        # Small delay to ensure hour picker is dismissed before opening minute picker
        Clock.schedule_once(lambda dt: MinutePickerPopup(
            current_minute=self.selected_minute,
            on_select=self._on_minute_selected
        ).open(), 0.05)
    
    def _on_minute_selected(self, minute):
        """Called when minute is selected, combine and call callback"""
        self.selected_minute = minute
        # Schedule callback after popup dismisses to avoid UI blocking
        Clock.schedule_once(lambda dt: self._execute_callback(), 0.05)
    
    def _execute_callback(self):
        """Execute the callback after popup has dismissed"""
        try:
            t = datetime.time(hour=self.selected_hour, minute=self.selected_minute)
            if self.on_select_callback:
                self.on_select_callback(t)
        except ValueError as e:
            logger.error(f"[TIME_PICKER] Error creating time: {e}")
            from kivy.app import App
            App.get_running_app().show_popup("Fehler", "Ungültige Zeit")
    
    def open(self):
        """Open the time picker (starts with hour picker)"""
        self._open_hour_picker()
