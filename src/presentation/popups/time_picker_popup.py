"""
Time picker popup for selecting times.
"""
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.properties import ObjectProperty
from kivy.app import App

from src.presentation.widgets import DebouncedButton

logger = logging.getLogger(__name__)


class TimePickerPopup(Popup):
    selected_time = ObjectProperty(None, allownone=True)

    def __init__(self, current_time=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        now = current_time or datetime.datetime.now().time()
        self.selected_hour = now.hour
        self.selected_minute = (now.minute // 5) * 5  # round to 5 minutes

        self.title = "Zeit Auswählen"
        self.size_hint = (0.6, 0.6)
        self.auto_dismiss = False

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Hour/Minute selectors
        selectors = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='60dp')
        self.hour_spinner = Spinner(
            text=f"{self.selected_hour:02d}",
            values=[f"{h:02d}" for h in range(24)],
            size_hint_x=0.5
        )
        self.minute_spinner = Spinner(
            text=f"{self.selected_minute:02d}",
            values=[f"{m:02d}" for m in range(0, 60, 5)],
            size_hint_x=0.5
        )
        selectors.add_widget(self.hour_spinner)
        selectors.add_widget(self.minute_spinner)
        layout.add_widget(selectors)

        # Buttons
        btn_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='50dp')
        ok_btn = DebouncedButton(text="OK", background_color=(0, 0.7, 0, 1))
        cancel_btn = DebouncedButton(text="Abbrechen", background_color=(0.7, 0.2, 0.2, 1))
        ok_btn.bind(on_release=self._confirm_time)
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        self.content = layout

    def _confirm_time(self, *_):
        try:
            hour = int(self.hour_spinner.text)
            minute = int(self.minute_spinner.text)
            t = datetime.time(hour=hour, minute=minute)
            if self.on_select_callback:
                self.on_select_callback(t)
            self.dismiss()
        except ValueError:
            App.get_running_app().show_popup("Fehler", "Ungültige Zeit")

