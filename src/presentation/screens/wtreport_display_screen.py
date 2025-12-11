"""
WT Report display screen.
"""
import logging
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.clock import Clock

from src.export_utils import get_export_directory

logger = logging.getLogger(__name__)


class WTReportDisplayScreen(Screen):
    selected_employee = ObjectProperty(None, allownone=True)
    current_report = ObjectProperty(None, allownone=True)
    start_date = ObjectProperty(None, allownone=True)
    end_date = ObjectProperty(None, allownone=True)
    
    def on_enter(self):
        """Update report display when screen is entered"""
        self.update_report_display()
    
    def update_report_display(self):
        """Update the report display label"""
        if self.current_report and hasattr(self, 'ids') and 'report_display' in self.ids:
            self.ids.report_display.text = self.current_report.to_text()
            # Update label height after texture is calculated
            def update_height(dt):
                if hasattr(self, 'ids') and 'report_display' in self.ids:
                    label = self.ids.report_display
                    if label.texture_size:
                        label.height = max(label.texture_size[1], 100)
            Clock.schedule_once(update_height, 0.1)
    
    def export_report(self):
        """Export current report to CSV"""
        if not self.current_report:
            App.get_running_app().show_popup("Error", "Kein Bericht vorhanden.")
            return
        
        try:
            export_dir = get_export_directory()
            filename = self.current_report.to_csv(export_root=export_dir)
            
            # Show success message and return to admin
            app = App.get_running_app()
            app.show_popup("Export Erfolgreich", f"WT Report exportiert nach:\n{filename}")
            Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'admin'), 2.5)
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            App.get_running_app().show_popup("Error", f"Export fehlgeschlagen: {str(e)}")

