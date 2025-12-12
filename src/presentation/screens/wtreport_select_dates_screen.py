"""
WT Report date selection screen.
"""
import datetime
import logging
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.clock import Clock

from src.presentation.popups.date_picker_popup import DatePickerPopup
from src.wt_report import generate_wt_report
from src.export_utils import get_export_directory

logger = logging.getLogger(__name__)


class WTReportSelectDatesScreen(Screen):
    selected_employee = ObjectProperty(None, allownone=True)
    start_date = ObjectProperty(None, allownone=True)
    end_date = ObjectProperty(None, allownone=True)
    
    def on_enter(self):
        """Set default dates when screen is entered"""
        today = datetime.date.today()
        if not self.start_date:
            self.start_date = today
        if not self.end_date:
            self.end_date = today
        self._update_date_display()
    
    def _update_date_display(self):
        """Update the date display buttons"""
        if not hasattr(self, 'ids'):
            return
        start_text = f"Von:\n{self.start_date.strftime('%d.%m.%Y')}" if self.start_date else "Von:\nDatum wählen"
        end_text = f"Bis:\n{self.end_date.strftime('%d.%m.%Y')}" if self.end_date else "Bis:\nDatum wählen"
        if 'start_date_button' in self.ids:
            self.ids.start_date_button.text = start_text
        if 'end_date_button' in self.ids:
            self.ids.end_date_button.text = end_text
    
    def open_start_date_picker(self):
        """Open date picker for start date"""
        DatePickerPopup(
            current_date=self.start_date or datetime.date.today(),
            on_select=self._set_start_date
        ).open()
    
    def open_end_date_picker(self):
        """Open date picker for end date"""
        DatePickerPopup(
            current_date=self.end_date or datetime.date.today(),
            on_select=self._set_end_date
        ).open()
    
    def _set_start_date(self, date):
        self.start_date = date
        self._update_date_display()
    
    def _set_end_date(self, date):
        self.end_date = date
        self._update_date_display()
    
    def generate_report(self):
        """Generate report and navigate to display screen"""
        if not self.selected_employee:
            App.get_running_app().show_popup("Error", "Bitte wählen Sie zuerst einen Mitarbeiter.")
            return
        
        if not self.start_date or not self.end_date:
            App.get_running_app().show_popup("Error", "Bitte wählen Sie Start- und Enddatum aus.")
            return
        
        try:
            # Generate report using selected dates
            report = generate_wt_report(self.selected_employee, self.start_date, self.end_date)
            
            # Navigate to display screen
            app = App.get_running_app()
            display_screen = app.root.get_screen('wtreport_display')
            display_screen.selected_employee = self.selected_employee
            display_screen.current_report = report
            display_screen.start_date = self.start_date
            display_screen.end_date = self.end_date
            display_screen.update_report_display()
            app.root.current = 'wtreport_display'
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            App.get_running_app().show_popup("Error", f"Failed to generate report: {str(e)}")
    
    def export_report(self):
        """Export report directly without displaying"""
        if not self.selected_employee:
            App.get_running_app().show_popup("Error", "Bitte wählen Sie zuerst einen Mitarbeiter.")
            return
        
        if not self.start_date or not self.end_date:
            App.get_running_app().show_popup("Error", "Bitte wählen Sie Start- und Enddatum aus.")
            return
        
        try:
            # Generate and export report using selected dates
            report = generate_wt_report(self.selected_employee, self.start_date, self.end_date)
            export_dir = get_export_directory()
            filename = report.to_csv(export_root=export_dir)
            
            # Show success message and return to admin
            app = App.get_running_app()
            app.show_popup("Export Erfolgreich", f"WT Report exportiert nach:\n{filename}")
            Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'admin'), 2.5)
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            App.get_running_app().show_popup("Error", f"Export fehlgeschlagen: {str(e)}")

