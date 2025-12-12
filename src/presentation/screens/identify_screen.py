"""
Identify screen for scanning and identifying RFID tags.
"""
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty


class IdentifyScreen(Screen):
    tag_info = StringProperty("Scan a tag to identify...")
    
    def on_enter(self):
        self.tag_info = "Ready to Scan..."

    def update_info(self, text):
        self.tag_info = text

