"""
Date picker popup for selecting dates without constraints.
"""
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.properties import ObjectProperty

from src.presentation.widgets import DebouncedButton

logger = logging.getLogger(__name__)


class DatePickerPopup(Popup):
    """Date picker without date constraints"""
    selected_date = ObjectProperty(None, allownone=True)
    
    def __init__(self, current_date=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        self.title = "Datum Auswählen"
        self.size_hint = (0.95, 0.95)  # Maximize usage for small screens
        self.auto_dismiss = False
        
        # Use current date or today
        if current_date is None:
            current_date = datetime.date.today()
        
        self.display_date = current_date  # The month/year being displayed
        self.selected_day = current_date.day
        
        # Create main container - Horizontal Layout for Landscape
        main_layout = BoxLayout(orientation='horizontal', spacing=10, padding=5)
        
        # --- LEFT PANEL: Calendar (65% width) ---
        left_panel = BoxLayout(orientation='vertical', spacing=5, size_hint_x=0.65)
        
        # Header: Month/Year navigation
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
        
        prev_month_btn = DebouncedButton(
            text="<",
            font_size='30sp',
            size_hint_x=0.2,
            background_color=(0.3, 0.5, 0.7, 1)
        )
        prev_month_btn.bind(on_release=lambda x: self._change_month(-1))
        
        month_year_label = Label(
            text=f"{self._get_month_name(current_date.month)} {current_date.year}",
            font_size='24sp',
            size_hint_x=0.6,
            bold=True
        )
        
        next_month_btn = DebouncedButton(
            text=">",
            font_size='30sp',
            size_hint_x=0.2,
            background_color=(0.3, 0.5, 0.7, 1)
        )
        next_month_btn.bind(on_release=lambda x: self._change_month(1))
        
        header.add_widget(prev_month_btn)
        header.add_widget(month_year_label)
        header.add_widget(next_month_btn)
        
        self.month_year_label = month_year_label
        left_panel.add_widget(header)
        
        # Day names header
        day_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        day_header = GridLayout(cols=7, size_hint_y=None, height='40dp', spacing=2)
        for day_name in day_names:
            label = Label(
                text=day_name,
                font_size='18sp',
                bold=True,
                color=(0.7, 0.7, 0.7, 1)
            )
            day_header.add_widget(label)
        left_panel.add_widget(day_header)
        
        # Days grid - Fills remaining vertical space
        days_grid = GridLayout(cols=7, spacing=3)
        self.days_grid = days_grid
        self.day_buttons = []
        left_panel.add_widget(days_grid)
        
        main_layout.add_widget(left_panel)
        
        # --- RIGHT PANEL: Controls (35% width) ---
        right_panel = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.35, padding=[5, 0, 0, 0])
        
        # Selected Date Display
        self.selected_date_label = Label(
            text="",
            font_size='24sp',
            bold=True,
            color=(0.2, 0.8, 0.2, 1),
            size_hint_y=1  # Fills available space
        )
        right_panel.add_widget(self.selected_date_label)
        
        # Buttons
        btn_height = '60dp'
        
        today_btn = DebouncedButton(
            text="Heute",
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='20sp',
            size_hint_y=None,
            height=btn_height
        )
        today_btn.bind(on_release=lambda x: self._select_today())
        right_panel.add_widget(today_btn)
        
        ok_btn = DebouncedButton(
            text="OK",
            background_color=(0, 0.7, 0, 1),
            font_size='20sp',
            size_hint_y=None,
            height=btn_height
        )
        ok_btn.bind(on_release=lambda x: self._confirm_date())
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
        
        # Initial Update
        self._update_calendar()
        self._update_selected_label()
    
    def _get_month_name(self, month):
        """Get German month name"""
        months = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        return months[month]
    
    def _change_month(self, delta):
        """Change displayed month"""
        year = self.display_date.year
        month = self.display_date.month + delta
        
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1
        
        self.display_date = datetime.date(year, month, 1)
        self.month_year_label.text = f"{self._get_month_name(month)} {year}"
        self._update_calendar()
    
    def _select_today(self):
        """Select today's date"""
        today = datetime.date.today()
        self.display_date = today
        self.selected_day = today.day
        self.month_year_label.text = f"{self._get_month_name(today.month)} {today.year}"
        self._update_calendar()
        self._update_selected_label()
    
    def _update_selected_label(self):
        """Update the label showing selected date"""
        try:
            date = datetime.date(
                self.display_date.year,
                self.display_date.month,
                self.selected_day
            )
            self.selected_date_label.text = date.strftime("%d.%m.%Y")
        except ValueError:
            self.selected_date_label.text = ""
    
    def _update_calendar(self):
        """Update the calendar grid with days"""
        self.days_grid.clear_widgets()
        self.day_buttons = []
        
        first_day = datetime.date(self.display_date.year, self.display_date.month, 1)
        first_weekday = first_day.weekday()
        
        if self.display_date.month == 12:
            next_month = datetime.date(self.display_date.year + 1, 1, 1)
        else:
            next_month = datetime.date(self.display_date.year, self.display_date.month + 1, 1)
        days_in_month = (next_month - first_day).days
        
        # Add empty cells
        for _ in range(first_weekday):
            self.days_grid.add_widget(Widget())
        
        today = datetime.date.today()
        for day in range(1, days_in_month + 1):
            date = datetime.date(self.display_date.year, self.display_date.month, day)
            is_today = (date == today)
            is_selected = (day == self.selected_day)
            
            if is_selected:
                bg_color = (0.2, 0.6, 0.9, 1)
                text_color = (1, 1, 1, 1)
            elif is_today:
                bg_color = (0.3, 0.7, 0.3, 1)
                text_color = (1, 1, 1, 1)
            else:
                bg_color = (0.4, 0.4, 0.4, 1)
                text_color = (1, 1, 1, 1)
            
            btn = DebouncedButton(
                text=str(day),
                font_size='18sp',
                background_color=bg_color,
                color=text_color
            )
            btn.bind(on_release=lambda instance, d=day: self._select_day(d))
            self.days_grid.add_widget(btn)
            self.day_buttons.append(btn)
        
        # Fill remaining cells
        total_cells = first_weekday + days_in_month
        rows_needed = (total_cells + 6) // 7
        total_slots = rows_needed * 7
        
        for _ in range(total_slots - total_cells):
            self.days_grid.add_widget(Widget())
    
    def _select_day(self, day):
        """Select a day"""
        self.selected_day = day
        self._update_selected_label()
        
        # Update button colors
        today = datetime.date.today()
        for i, btn in enumerate(self.day_buttons):
            day_num = i + 1
            date_check = datetime.date(self.display_date.year, self.display_date.month, day_num)
            is_today = (date_check == today)
            is_selected = (day_num == day)
            
            if is_selected:
                btn.background_color = (0.2, 0.6, 0.9, 1)
                btn.color = (1, 1, 1, 1)
            elif is_today:
                btn.background_color = (0.3, 0.7, 0.3, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.4, 0.4, 0.4, 1)
                btn.color = (1, 1, 1, 1)
    
    def _confirm_date(self):
        """Confirm date selection"""
        try:
            selected_date = datetime.date(
                self.display_date.year,
                self.display_date.month,
                self.selected_day
            )
            
            if self.on_select_callback:
                self.on_select_callback(selected_date)
            
            self.dismiss()
        except (ValueError, TypeError) as e:
            from kivy.app import App
            App.get_running_app().show_popup("Fehler", f"Ungültiges Datum: {str(e)}")

