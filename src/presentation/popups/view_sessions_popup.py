"""
View sessions popup with date picker for selecting which day's sessions to view.
"""
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.app import App

from ..widgets import DebouncedButton
from .limited_date_picker_popup import LimitedDatePickerPopup
from ...services.report_service import generate_wt_report

logger = logging.getLogger(__name__)


class ViewSessionsPopup(Popup):
    """Popup for viewing sessions with date selection"""
    
    def __init__(self, employee, **kwargs):
        super().__init__(
            title=f"Sessions - {employee.name}",
            size_hint=(0.95, 0.95),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        self.selected_date = datetime.date.today()
        
        # Register with popup service for proper management
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service.close_main_popup()  # Close any existing main popup
            app.popup_service._register_popup(self, is_main=True)
        
        self._build_ui()
        self._load_report_for_date()
        
        # Ensure proper cleanup on dismiss
        self.bind(on_dismiss=self._on_dismiss)
    
    def _on_dismiss(self, instance):
        """Cleanup when popup is dismissed"""
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service._unregister_popup(self)
    
    def _build_ui(self):
        """Build the UI with date selection and report display"""
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Header with date selection
        header_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='70dp')
        
        # Date selection button
        self.date_btn = DebouncedButton(
            text=f"Datum: {self.selected_date.strftime('%d.%m.%Y')}",
            size_hint_x=0.6,
            font_size='20sp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.date_btn.bind(on_release=lambda *_: self._pick_date())
        header_row.add_widget(self.date_btn)
        
        # Close button
        close_btn = DebouncedButton(
            text="Schließen",
            size_hint_x=0.4,
            font_size='20sp',
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
    
    def _pick_date(self):
        """Open date picker limited to past 7 days"""
        today = datetime.date.today()
        min_date = today - datetime.timedelta(days=7)
        
        LimitedDatePickerPopup(
            current_date=self.selected_date,
            min_date=min_date,
            max_date=today,
            on_select=self._set_date
        ).open()
    
    def _set_date(self, date_obj):
        """Update selected date and reload report"""
        if date_obj != self.selected_date:
            self.selected_date = date_obj
            self.date_btn.text = f"Datum: {self.selected_date.strftime('%d.%m.%Y')}"
            self._load_report_for_date()
    
    def _load_report_for_date(self):
        """Load and display report for the selected date"""
        try:
            report = generate_wt_report(self.employee, self.selected_date, self.selected_date)
            text = report.to_text()
            self.report_label.text = text
        except Exception as e:
            logger.error(f"Error loading report for {self.selected_date}: {e}")
            self.report_label.text = f"Fehler beim Laden des Berichts:\n{str(e)}"

