"""
Hour picker popup for selecting hours (0-23).
"""
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty

from ..widgets import DebouncedButton

logger = logging.getLogger(__name__)


class HourPickerPopup(Popup):
    """Hour picker popup - simple grid of hours"""
    selected_hour = ObjectProperty(None, allownone=True)
    
    def __init__(self, current_hour=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        self.selected_hour = current_hour if current_hour is not None else 12
        
        self.title = "Stunde Auswählen"
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        
        # Create main container - Horizontal Layout for Landscape (matching date picker)
        main_layout = BoxLayout(orientation='horizontal', spacing=10, padding=5)
        
        # --- LEFT PANEL: Hours Grid (65% width) ---
        left_panel = BoxLayout(orientation='vertical', spacing=5, size_hint_x=0.65, size_hint_y=1)
        
        # Header: Title
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
        header_label = Label(
            text="Stunde Auswählen",
            font_size='24sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=1,
            halign='center'
        )
        header_label.bind(text_size=header_label.setter('size'))
        header.add_widget(header_label)
        left_panel.add_widget(header)
        
        # Hours grid - Scrollable (fills remaining height)
        hours_scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=10,
            size_hint_y=1,
            size_hint_x=1
        )
        hour_grid = GridLayout(
            cols=4,
            spacing=3,
            size_hint_y=None
        )
        hour_grid.bind(minimum_height=hour_grid.setter('height'))
        
        self.hour_buttons = []
        for hour in range(24):
            btn = DebouncedButton(
                text=f"{hour:02d}",
                font_size='18sp',
                size_hint_y=None,
                height='50dp',
                background_color=(0.4, 0.4, 0.4, 1) if hour != self.selected_hour else (0.2, 0.6, 0.9, 1),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_release=lambda instance, h=hour: self._select_hour(h))
            hour_grid.add_widget(btn)
            self.hour_buttons.append(btn)
        
        hours_scroll.add_widget(hour_grid)
        left_panel.add_widget(hours_scroll)
        main_layout.add_widget(left_panel)
        
        # --- RIGHT PANEL: Controls (35% width) ---
        right_panel = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.35, padding=[5, 0, 0, 0])
        
        # Selected Hour Display
        self.hour_display = Label(
            text=f"{self.selected_hour:02d}",
            font_size='24sp',
            bold=True,
            color=(0.2, 0.8, 0.2, 1),
            size_hint_y=1  # Fills available space
        )
        right_panel.add_widget(self.hour_display)
        
        # Buttons
        btn_height = '60dp'
        
        ok_btn = DebouncedButton(
            text="OK",
            background_color=(0, 0.7, 0, 1),
            font_size='20sp',
            size_hint_y=None,
            height=btn_height
        )
        ok_btn.bind(on_release=self._confirm)
        right_panel.add_widget(ok_btn)
        
        cancel_btn = DebouncedButton(
            text="Abbrechen",
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='20sp',
            size_hint_y=None,
            height=btn_height
        )
        cancel_btn.bind(on_release=self.dismiss)
        right_panel.add_widget(cancel_btn)
        
        main_layout.add_widget(right_panel)
        self.content = main_layout
    
    def _select_hour(self, hour):
        """Select an hour"""
        self.selected_hour = hour
        self._update_display()
        self._update_button_colors()
    
    def _update_display(self):
        """Update the hour display label"""
        self.hour_display.text = f"{self.selected_hour:02d}"
    
    def _update_button_colors(self):
        """Update button colors to show selection"""
        for i, btn in enumerate(self.hour_buttons):
            if i == self.selected_hour:
                btn.background_color = (0.2, 0.6, 0.9, 1)
            else:
                btn.background_color = (0.4, 0.4, 0.4, 1)
    
    def _confirm(self, *_):
        """Confirm hour selection"""
        if self.on_select_callback:
            self.on_select_callback(self.selected_hour)
        self.dismiss()

