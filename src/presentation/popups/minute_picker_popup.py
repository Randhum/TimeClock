"""
Minute picker popup for selecting minutes (0-59 in 5-minute intervals).
"""
import logging
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty

from ..widgets import DebouncedButton

logger = logging.getLogger(__name__)


class MinutePickerPopup(Popup):
    """Minute picker popup - simple grid of minutes"""
    selected_minute = ObjectProperty(None, allownone=True)
    
    def __init__(self, current_minute=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        # Round to nearest 5 minutes
        if current_minute is not None:
            self.selected_minute = (current_minute // 5) * 5
        else:
            self.selected_minute = 0
        
        self.title = "Minute Auswählen"
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        
        # Create main container - Horizontal Layout for Landscape (matching date picker)
        main_layout = BoxLayout(orientation='horizontal', spacing=10, padding=5)
        
        # --- LEFT PANEL: Minutes Grid (65% width) ---
        left_panel = BoxLayout(orientation='vertical', spacing=5, size_hint_x=0.65, size_hint_y=1)
        
        # Header: Title
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
        header_label = Label(
            text="Minute Auswählen",
            font_size='24sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=1,
            halign='center'
        )
        header_label.bind(text_size=header_label.setter('size'))
        header.add_widget(header_label)
        left_panel.add_widget(header)
        
        # Minutes grid - Scrollable (matching date/hour picker structure)
        minutes_scroll = ScrollView(
            do_scroll_x=False,
            bar_width=10,
            size_hint_y=1
        )
        minute_grid = GridLayout(
            cols=4,
            spacing=3,
            size_hint_y=None
        )
        minute_grid.bind(minimum_height=minute_grid.setter('height'))
        
        self.minute_buttons = []
        minute_values = list(range(0, 60, 5))
        for minute in minute_values:
            btn = DebouncedButton(
                text=f"{minute:02d}",
                font_size='18sp',
                size_hint_y=None,
                height='50dp',
                background_color=(0.4, 0.4, 0.4, 1) if minute != self.selected_minute else (0.2, 0.6, 0.9, 1),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_release=lambda instance, m=minute: self._select_minute(m))
            minute_grid.add_widget(btn)
            self.minute_buttons.append(btn)
        
        minutes_scroll.add_widget(minute_grid)
        left_panel.add_widget(minutes_scroll)
        self._configure_scroll_behavior(minutes_scroll, minute_grid)
        main_layout.add_widget(left_panel)
        
        # --- RIGHT PANEL: Controls (35% width) ---
        right_panel = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.35, padding=[5, 0, 0, 0])
        
        # Selected Minute Display
        self.minute_display = Label(
            text=f"{self.selected_minute:02d}",
            font_size='24sp',
            bold=True,
            color=(0.2, 0.8, 0.2, 1),
            size_hint_y=1  # Fills available space
        )
        right_panel.add_widget(self.minute_display)
        
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
    
    def _select_minute(self, minute):
        """Select a minute"""
        self.selected_minute = minute
        self._update_display()
        self._update_button_colors()
    
    def _update_display(self):
        """Update the minute display label"""
        self.minute_display.text = f"{self.selected_minute:02d}"
    
    def _update_button_colors(self):
        """Update button colors to show selection"""
        minute_values = list(range(0, 60, 5))
        for i, btn in enumerate(self.minute_buttons):
            if minute_values[i] == self.selected_minute:
                btn.background_color = (0.2, 0.6, 0.9, 1)
            else:
                btn.background_color = (0.4, 0.4, 0.4, 1)
    
    def _confirm(self, *_):
        """Confirm minute selection"""
        if self.on_select_callback:
            self.on_select_callback(self.selected_minute)
        self.dismiss()

    def _configure_scroll_behavior(self, scroll_view, grid):
        """Disable scrolling when the grid fits to avoid touch interception."""
        def _update_scroll(*_):
            needs_scroll = grid.height > scroll_view.height
            scroll_view.do_scroll_y = needs_scroll
            scroll_view.bar_width = 10 if needs_scroll else 0

        # Schedule once after layout and keep updated on size changes
        Clock.schedule_once(lambda dt: _update_scroll(), 0)
        scroll_view.bind(height=_update_scroll)
        grid.bind(height=_update_scroll)

