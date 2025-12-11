"""
TimeClock main screen.
"""
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.clock import Clock


class TimeClockScreen(Screen):
    status_message = StringProperty("Ready")

    def update_status(self, message):
        self.status_message = message
        # Clear message after 3 seconds
        Clock.schedule_once(lambda dt: self.set_default_status(), 3)

    def set_default_status(self):
        self.status_message = "Ready"

