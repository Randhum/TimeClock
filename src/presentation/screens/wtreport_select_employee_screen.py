"""
WT Report employee selection screen.
"""
import logging
from kivy.uix.screenmanager import Screen
from kivy.app import App

from src.database import get_all_employees
from src.presentation.widgets import DebouncedButton

logger = logging.getLogger(__name__)


class WTReportSelectEmployeeScreen(Screen):
    def on_enter(self):
        """Load employees when screen is entered"""
        self.load_employees()
    
    def load_employees(self):
        """Load list of employees and create selection buttons"""
        try:
            employees = list(get_all_employees(include_inactive=False))
            
            # Clear existing buttons
            if hasattr(self, 'ids') and 'employee_buttons_container' in self.ids:
                container = self.ids.employee_buttons_container
                container.clear_widgets()
                
                # Create button for each employee
                for employee in employees:
                    btn = DebouncedButton(
                        text=f"{employee.name} ({employee.rfid_tag})",
                        size_hint_y=None,
                        height='80dp',
                        font_size='24sp'
                    )
                    # Bind button to select this employee
                    btn.bind(on_release=lambda instance, emp=employee: self.select_employee(emp))
                    container.add_widget(btn)
                    
        except Exception as e:
            logger.error(f"Error loading employees: {e}")
    
    def select_employee(self, employee):
        """Select an employee and navigate to date selection screen"""
        app = App.get_running_app()
        date_screen = app.root.get_screen('wtreport_select_dates')
        date_screen.selected_employee = employee
        app.root.current = 'wtreport_select_dates'

