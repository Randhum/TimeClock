"""
TimeClock Application - Refactored Main Entry Point

This is the refactored version using the new service-based architecture.
Once verified, this will replace main.py.
"""
import logging
import os
import datetime

# IMPORTANT: Config must be set BEFORE importing Kivy modules
from kivy.config import Config

# Raspberry Pi Touchscreen Optimization / Kiosk Mode
Config.set('input', 'touch', 'probesysfs,provider=mtdev')
Config.set('input', 'mouse', '')  # Disable default mouse provider
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('kivy', 'keyboard_layout', 'qwerty')

# Now import Kivy modules
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.core.window import Window

# Import services
from .services.clock_service import ClockService
from .services.state_service import StateService
from .services.popup_service import PopupService

# Import widgets
from .presentation.widgets import DebouncedButton, FilteredTextInput, GlobalInputFilter, GlobalKeyFilter

# Import database
from .database import (
    initialize_db, close_db, Employee, TimeEntry,
    get_employee_by_tag, get_admin_count, create_employee, create_time_entry,
    get_time_entries_for_export, get_all_employees, soft_delete_time_entries
)

# Import RFID
from .rfid import get_rfid_provider

# Import other modules
from peewee import IntegrityError
from .wt_report import generate_wt_report
from .export_utils import get_export_directory, write_file
from .screensaver import ScreensaverScreen

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Window configuration
Window.show_cursor = False
Window.fullscreen = 'auto'
Window.softinput_mode = 'below_target'


# Import screens and popups (will be extracted)
# For now, import from main to maintain compatibility
import sys
from pathlib import Path
# We'll import the old classes temporarily until fully extracted
# This allows incremental migration

# Screen classes - to be extracted
class TimeClockScreen(Screen):
    status_message = StringProperty("Ready")

    def update_status(self, message):
        self.status_message = message
        Clock.schedule_once(lambda dt: self.set_default_status(), 3)

    def set_default_status(self):
        self.status_message = "Ready"


class WindowManager(ScreenManager):
    pass


class TimeClockApp(App):
    """Main application - refactored to use services"""
    
    idle_seconds = 0
    MAX_IDLE_SECONDS = 60
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize services
        self.state_service = StateService()
        self.popup_service = PopupService()
        self.clock_service = None  # Will be initialized after RFID is ready
        self.rfid = None
    
    def build(self):
        """Build UI - minimal logic, delegate to services"""
        # Initialize database
        initialize_db()
        
        # Initialize RFID
        self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False)
        self.rfid.start()
        
        # Initialize clock service with RFID
        self.clock_service = ClockService(self.rfid)
        
        # Global input de-duplication
        self._input_filter = GlobalInputFilter(Window)
        self._input_filter.install()
        self._key_filter = GlobalKeyFilter(Window)
        self._key_filter.install()

        # Idle Timer Setup
        Clock.schedule_interval(self.check_idle, 1)
        Window.bind(on_motion=self.on_user_activity)
        
        # Check if admin exists
        self.check_initial_setup()
        
        return self.root

    def check_idle(self, dt):
        """Check if we should start screensaver"""
        if self.root.current == 'screensaver':
            return
            
        self.idle_seconds += 1
        if self.idle_seconds >= self.MAX_IDLE_SECONDS:
            self.start_screensaver()

    def on_user_activity(self, window, etype, motionevent):
        """Reset idle timer on any touch/mouse movement"""
        self.reset_idle_timer()

    def reset_idle_timer(self, force_unlock=False):
        """Reset idle timer"""
        self.idle_seconds = 0
        if force_unlock or self.root.current == 'screensaver':
            if self.root.current == 'screensaver':
                self.stop_screensaver()

    def start_screensaver(self):
        """Start screensaver"""
        self.previous_screen = self.root.current
        self.root.current = 'screensaver'

    def stop_screensaver(self):
        """Stop screensaver"""
        self.root.current = 'timeclock'

    def check_initial_setup(self):
        """Check if initial admin setup is needed"""
        if get_admin_count() == 0:
            Clock.schedule_once(lambda dt: self.show_initial_setup(), 0.5)

    def show_initial_setup(self):
        """Show initial setup screen"""
        self.root.current = 'register'
        self.root.get_screen('register').ids.admin_checkbox.active = True
        self.root.get_screen('register').ids.admin_checkbox.disabled = True
        self.popup_service.show_info("Welcome", "Please register the initial Administrator.")

    def on_rfid_scan(self, tag_id):
        """RFID callback - delegate to service"""
        Clock.schedule_once(lambda dt: self.handle_scan(tag_id), 0)

    def handle_scan(self, tag_id):
        """Handle RFID scan - uses state service for debouncing"""
        # Reset idle timer
        self.reset_idle_timer()
        
        logger.info(f"Handling scan: {tag_id}")
        
        # Check for recent scan (debounce)
        if self.state_service.is_recent_scan(tag_id):
            logger.debug(f"Ignoring duplicate scan for {tag_id}")
            return
        
        current_screen = self.root.current
        
        # Check if tag belongs to an existing employee
        existing_employee = get_employee_by_tag(tag_id)

        # Handle register screen
        if current_screen == 'register':
            self._handle_register_scan(tag_id, existing_employee)
            return

        # Handle identify screen
        if current_screen == 'identify':
            self._handle_identify_scan(tag_id, existing_employee)
            return

        # Check for pending badge identification
        pending_id = self.state_service.pending_identification
        if pending_id:
            self._handle_pending_identification(tag_id, existing_employee, pending_id)
            return

        # Handle unknown tag
        if not existing_employee:
            self.popup_service.show_error("Unbekannter Tag", f"Tag ID: {tag_id}")
            return

        # Handle admin tag
        if existing_employee.is_admin:
            if current_screen != 'admin':
                self.root.current = 'admin'
            return

        # Handle normal employee clock action
        if current_screen == 'timeclock':
            self.perform_clock_action(existing_employee)
        elif current_screen == 'admin':
            self.popup_service.show_info("Admin Modus", "Please switch to Timeclock mode to clock in/out.")

    def _handle_register_scan(self, tag_id, existing_employee):
        """Handle scan on register screen"""
        logger.debug(f"[RFID] Register screen - tag={tag_id}, existing_employee={existing_employee}")
        if existing_employee:
            if existing_employee.is_admin:
                if get_admin_count() > 0:
                    logger.debug("[RFID] Admin tag scanned, switching to admin screen")
                    self.root.current = 'admin'
                else:
                    logger.debug("[RFID] Admin tag but no admins exist - error")
                    self.popup_service.show_error("Error", "This tag is already an Admin. Please use a new tag for the initial Admin.")
                    self.rfid.indicate_error()
            else:
                logger.debug(f"[RFID] Tag already assigned to {existing_employee.name} - showing error")
                self.popup_service.show_error("Error", f"Tag already assigned to {existing_employee.name}")
                self.rfid.indicate_error()
        else:
            # New tag
            logger.debug(f"[RFID] New tag detected, setting tag_id to {tag_id.upper()}")
            self.root.get_screen('register').tag_id = str(tag_id).upper()
            self.rfid.indicate_success()

    def _handle_identify_scan(self, tag_id, existing_employee):
        """Handle scan on identify screen"""
        if existing_employee:
            role = "Administrator" if existing_employee.is_admin else "Employee"
            info = f"Name: {existing_employee.name}\nID: {existing_employee.rfid_tag}\nRole: {role}"
        else:
            info = f"Tag ID: {tag_id}\nStatus: Unregistriert"
        
        self.root.get_screen('identify').update_info(info)

    def _handle_pending_identification(self, tag_id, existing_employee, pending_id):
        """Handle scan during pending identification"""
        if existing_employee:
            # Employee identified - notify popup
            if pending_id.popup:
                pending_id.popup.on_employee_identified(existing_employee)
            self.rfid.indicate_success()
        else:
            # Unknown tag during identification
            if pending_id.popup:
                pending_id.popup.status_label.text = "Unbekanntes Badge. Bitte versuchen Sie es erneut."
                pending_id.popup.status_label.color = (1, 0.2, 0.2, 1)  # Red
            self.rfid.indicate_error()

    def perform_clock_action(self, employee):
        """Perform clock action using clock service"""
        result = self.clock_service.clock_in_out(employee)
        
        if result.success:
            # Show greeter
            self.popup_service.show_greeter(result.employee, result.action)
            
            # Update UI
            msg = f"Clocked {result.action.upper()} - {result.employee.name}"
            self.root.get_screen('timeclock').update_status(msg)
            
            # Update state
            self.state_service.set_last_clocked_employee(result.employee)
        else:
            # Handle error
            self.popup_service.show_error("Error", f"Failed to record time: {result.error}")

    def on_stop(self):
        """Cleanup on app stop"""
        if self.rfid:
            self.rfid.stop()
        close_db()

    def show_popup(self, title, content):
        """Legacy method - delegate to popup service"""
        self.popup_service.show_info(title, content)

    def show_greeter(self, employee, action):
        """Legacy method - delegate to popup service"""
        self.popup_service.show_greeter(employee, action)


if __name__ == '__main__':
    TimeClockApp().run()

