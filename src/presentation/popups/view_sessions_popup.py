"""
View sessions popup with month picker for selecting which month's sessions to view.
"""
import calendar
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.app import App

from ..widgets import DebouncedButton
from ...services.report_service import generate_wt_report

logger = logging.getLogger(__name__)

# German month names
MONTH_NAMES = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


class MonthPickerPopup(Popup):
    """Popup for selecting a month"""
    
    def __init__(self, current_year, current_month, on_select=None, **kwargs):
        super().__init__(
            title="Monat auswählen",
            size_hint=(0.9, 0.9),
            auto_dismiss=False,
            **kwargs
        )
        self.on_select_callback = on_select
        self.selected_year = current_year
        self.selected_month = current_month
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the month picker UI"""
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Year selector row
        year_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='60dp')
        
        prev_year_btn = DebouncedButton(
            text="◀",
            size_hint_x=0.2,
            font_size='24sp',
            background_color=(0.3, 0.3, 0.3, 1)
        )
        prev_year_btn.bind(on_release=lambda *_: self._change_year(-1))
        year_row.add_widget(prev_year_btn)
        
        self.year_label = Label(
            text=str(self.selected_year),
            size_hint_x=0.6,
            font_size='24sp',
            bold=True
        )
        year_row.add_widget(self.year_label)
        
        next_year_btn = DebouncedButton(
            text="▶",
            size_hint_x=0.2,
            font_size='24sp',
            background_color=(0.3, 0.3, 0.3, 1)
        )
        next_year_btn.bind(on_release=lambda *_: self._change_year(1))
        year_row.add_widget(next_year_btn)
        
        layout.add_widget(year_row)
        
        # Month grid (4 columns x 3 rows)
        month_grid = GridLayout(cols=4, spacing=5, size_hint_y=None, height='240dp')
        
        self.month_buttons = []
        for i, month_name in enumerate(MONTH_NAMES):
            month_num = i + 1
            btn = DebouncedButton(
                text=month_name[:3],  # Abbreviated month name
                font_size='16sp',
                background_color=self._get_month_color(month_num)
            )
            btn.bind(on_release=lambda inst, m=month_num: self._select_month(m))
            month_grid.add_widget(btn)
            self.month_buttons.append(btn)
        
        layout.add_widget(month_grid)
        
        # Buttons row
        btn_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='60dp')
        
        cancel_btn = DebouncedButton(
            text="Abbrechen",
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='18sp'
        )
        cancel_btn.bind(on_release=lambda *_: self.dismiss())
        btn_row.add_widget(cancel_btn)
        
        layout.add_widget(btn_row)
        
        self.content = layout
    
    def _get_month_color(self, month_num):
        """Get button color for a month"""
        if month_num == self.selected_month:
            return (0.2, 0.6, 0.9, 1)  # Selected - blue
        return (0.4, 0.4, 0.4, 1)  # Default - gray
    
    def _update_month_colors(self):
        """Update month button colors"""
        for i, btn in enumerate(self.month_buttons):
            btn.background_color = self._get_month_color(i + 1)
    
    def _change_year(self, delta):
        """Change the selected year"""
        self.selected_year += delta
        self.year_label.text = str(self.selected_year)
    
    def _select_month(self, month_num):
        """Select a month and close popup"""
        self.selected_month = month_num
        if self.on_select_callback:
            self.on_select_callback(self.selected_year, self.selected_month)
        self.dismiss()


class ViewSessionsPopup(Popup):
    """Popup for viewing sessions with month selection"""
    
    def __init__(self, employee, **kwargs):
        super().__init__(
            title=f"Sessions - {employee.name}",
            size_hint=(0.95, 0.95),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        
        # Default to current month
        today = datetime.date.today()
        self.selected_year = today.year
        self.selected_month = today.month
        
        # Register with popup service for proper management
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service.close_main_popup()  # Close any existing main popup
            app.popup_service._register_popup(self, is_main=True)
        
        self._build_ui()
        self._load_month_report()
        
        # Ensure proper cleanup on dismiss
        self.bind(on_dismiss=self._on_dismiss)
    
    def _on_dismiss(self, instance):
        """Cleanup when popup is dismissed"""
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service._unregister_popup(self)
    
    def _build_ui(self):
        """Build the UI with month selection and report display"""
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Header with month selection
        header_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='70dp')
        
        # Month selection button
        self.month_btn = DebouncedButton(
            text=self._get_month_display_text(),
            size_hint_x=0.6,
            font_size='18sp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.month_btn.bind(on_release=lambda *_: self._pick_month())
        header_row.add_widget(self.month_btn)
        
        # Close button
        close_btn = DebouncedButton(
            text="Schließen",
            size_hint_x=0.4,
            font_size='18sp',
            background_color=(0.3, 0.6, 0.9, 1)
        )
        close_btn.bind(on_release=lambda *_: self.dismiss())
        header_row.add_widget(close_btn)
        
        layout.add_widget(header_row)
        
        # Scrollable report display
        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=10
        )
        
        self.report_label = Label(
            text="",
            font_size='16sp',
            halign='left',
            valign='top',
            size_hint_y=None,
            text_size=(None, None),
            markup=True
        )
        # Bind height to texture size for proper scrolling
        self.report_label.bind(texture_size=lambda inst, size: setattr(inst, 'height', max(size[1], 100)))
        
        scroll.add_widget(self.report_label)
        layout.add_widget(scroll)
        
        self.content = layout
    
    def _get_month_display_text(self):
        """Get display text for the selected month"""
        month_name = MONTH_NAMES[self.selected_month - 1]
        return f"{month_name} {self.selected_year}"
    
    def _pick_month(self):
        """Open month picker popup"""
        MonthPickerPopup(
            current_year=self.selected_year,
            current_month=self.selected_month,
            on_select=self._set_month
        ).open()
    
    def _set_month(self, year, month):
        """Update selected month and reload report"""
        if year != self.selected_year or month != self.selected_month:
            self.selected_year = year
            self.selected_month = month
            self.month_btn.text = self._get_month_display_text()
            self._load_month_report()
    
    def _load_month_report(self):
        """Load and display report for the selected month (sessions with IN action in the month)"""
        try:
            # Calculate first and last day of month
            first_day = datetime.date(self.selected_year, self.selected_month, 1)
            last_day = datetime.date(self.selected_year, self.selected_month, 
                                     calendar.monthrange(self.selected_year, self.selected_month)[1])
            
            # Generate and display report
            # The report service filters sessions where IN action is within the date range
            report = generate_wt_report(self.employee, first_day, last_day)
            self.report_label.text = report.to_text()
        except Exception as e:
            logger.error(f"Error loading month report: {e}")
            self.report_label.text = f"Fehler beim Laden des Monatsberichts:\n{str(e)}"
