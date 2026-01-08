"""
TimeClock Application - Main Entry Point

Architecture Overview:
---------------------
This module implements the Presentation Layer of the TimeClock application:
- Screen Controllers: Manage UI state and user interactions
- Popup Components: Dialogs for notifications and data entry
- Input Handling: Custom components for touchscreen/keyboard issues
- Application Entry Point: Main app class and screen manager

See ARCHITECTURE.md for detailed architecture documentation.
"""

import logging
import datetime

# IMPORTANT: Config must be set BEFORE importing Kivy modules
from kivy.config import Config

# Raspberry Pi Touchscreen Optimization / Kiosk Mode
# Disable red dots on touch (multitouch simulation)
# Use mtdev for better multitouch handling if available, otherwise standard mouse

# Config: Explicitly use mtdev for touchscreen and disable mouse to prevent double-events
# This prevents Kivy from adding a "mouse" provider automatically if it detects one
Config.set('input', 'touch', 'probesysfs,provider=mtdev')
Config.set('input', 'mouse', '') # Disable default mouse provider

# Enable Kivy's built-in VKeyboard (systemanddock tries system first, then VKeyboard)
Config.set('kivy', 'keyboard_mode', 'systemanddock')
# Force VKeyboard layout
Config.set('kivy', 'keyboard_layout', 'qwerty')

# Now import Kivy modules
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
from kivy.core.window import Window

from .data.database import (
    initialize_db, close_db,
    get_employee_by_tag, get_admin_count
)
from .hardware.rfid import get_rfid_provider
from .presentation.screens.screensaver_screen import ScreensaverScreen

# Import new services
from .services.clock_service import ClockService
from .services.state_service import StateService
from .services.popup_service import PopupService

# Import extracted widgets (needed for KV file imports)
from .presentation.widgets import DebouncedButton, FilteredTextInput, GlobalInputFilter, GlobalKeyFilter, GlobalInputFilter, GlobalKeyFilter

# Import extracted popups
from .presentation.popups import (
    GreeterPopup,
    BadgeIdentificationPopup,
    EntryEditorPopup,
    LimitedDatePickerPopup,
    DatePickerPopup,
    TimePickerPopup,
    AddEntryPopup,
)

# Import extracted screens
from .presentation.screens import (
    TimeClockScreen,
    AdminScreen,
    IdentifyScreen,
    RegisterScreen,
    WTReportSelectEmployeeScreen,
    WTReportSelectDatesScreen,
    WTReportDisplayScreen,
)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Hide cursor for touch screen usage
Window.show_cursor = False
# Enable Fullscreen (Kiosk Mode)
Window.fullscreen = 'auto'
# Ensure the keyboard doesn't cover the input field by panning the content
Window.softinput_mode = 'below_target'

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

class WindowManager(ScreenManager):
    """Screen manager with popup cleanup on screen change"""
    
    def on_current(self, instance, value):
        """Called when current screen changes - close all popups"""
        super().on_current(instance, value)
        # Close all popups when switching screens to prevent overlap
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service.close_all_popups()

class TimeClockApp(App):
    """Main application - refactored to use services"""
    
    idle_seconds = 0
    MAX_IDLE_SECONDS = 60  # Start screensaver after 60 seconds

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize services
        self.state_service = StateService()
        self.popup_service = PopupService()
        self.clock_service = None  # Will be initialized after RFID is ready
        self.rfid = None
        
        # Set KV file path - Kivy will load it automatically with correct context
        import os
        kv_path = os.path.join(os.path.dirname(__file__), 'presentation', 'timeclock.kv')
        if os.path.exists(kv_path):
            self.kv_file = kv_path
        else:
            self.kv_file = None

    def build(self):
        """Build UI - delegate to services"""
        
        # Initialize database and RFID before returning root
        initialize_db()
        self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False)  # Attempt real, fallback to mock
        self.rfid.start()
        
        # Initialize clock service with RFID and other services
        self.clock_service = ClockService(self.rfid, self.popup_service, self.state_service)
        
        # Global input de-duplication (touch) to suppress double events everywhere
        self._input_filter = GlobalInputFilter(Window)
        self._input_filter.install()
        # Global keyboard/VKeyboard de-duplication (text + function keys)
        self._key_filter = GlobalKeyFilter(Window)
        self._key_filter.install()

        # Idle Timer Setup
        Clock.schedule_interval(self.check_idle, 1)
        Window.bind(on_motion=self.on_user_activity)
        
        # Check if admin exists
        self.check_initial_setup()
        
        # Root widget is automatically loaded from KV file by Kivy
        return self.root

    def check_idle(self, dt):
        """Check if we should start screensaver"""
        # Don't activate if already screensaver
        if self.root.current == 'screensaver':
            return
            
        self.idle_seconds += 1
        if self.idle_seconds >= self.MAX_IDLE_SECONDS:
            self.start_screensaver()

    def on_user_activity(self, window, etype, motionevent):
        """Reset idle timer on any touch/mouse movement"""
        self.reset_idle_timer()

    def reset_idle_timer(self, force_unlock=False):
        self.idle_seconds = 0
        if force_unlock or self.root.current == 'screensaver':
            if self.root.current == 'screensaver':
                self.stop_screensaver()

    def start_screensaver(self):
        self.previous_screen = self.root.current
        self.root.current = 'screensaver'

    def stop_screensaver(self):
        # Return to timeclock (safe default) or previous screen
        target = 'timeclock'
        # If we were in a deeply nested screen, maybe better to reset to home for security?
        # Stick to timeclock for now.
        self.root.current = target

    def check_initial_setup(self):
        if get_admin_count() == 0:
            # No admin, force setup
            Clock.schedule_once(lambda dt: self.show_initial_setup(), 0.5)

    def show_initial_setup(self):
        """Show initial setup screen"""
        self.root.current = 'register'
        self.root.get_screen('register').ids.admin_checkbox.active = True
        self.root.get_screen('register').ids.admin_checkbox.disabled = True  # Force admin for first user
        self.popup_service.show_info("Welcome", "Please register the initial Administrator.")

    def on_rfid_scan(self, tag_id):
        # Schedule handling on main thread
        Clock.schedule_once(lambda dt: self.handle_scan(tag_id), 0)

    def handle_scan(self, tag_id):
        """Handle RFID scan - uses state service for debouncing"""
        # Reset Idle Timer on every scan
        self.reset_idle_timer()
        logger.info(f"Handling scan: {tag_id}")
        
        current_screen = self.root.current
        
        # Check for recent scan (debounce) using state service
        if self.state_service.is_recent_scan(tag_id):
            logger.debug(f"Ignoring duplicate scan for {tag_id}")
            return
        
        # Check if tag belongs to an existing employee
        existing_employee = get_employee_by_tag(tag_id)

        if current_screen == 'register':
            logger.debug(f"[RFID] Register screen - tag={tag_id}, existing_employee={existing_employee}")
            if existing_employee:
                if existing_employee.is_admin:
                    # Admin tag scanned while registering -> Cancel/Go to Admin
                    if get_admin_count() > 0:
                        logger.debug("[RFID] Admin tag scanned, switching to admin screen")
                        self.root.current = 'admin'
                    else:
                        logger.debug("[RFID] Admin tag but no admins exist - error")
                        self.show_popup("Error", "This tag is already an Admin. Please use a new tag for the initial Admin.")
                        self.rfid.indicate_error()
                else:
                    logger.debug(f"[RFID] Tag already assigned to {existing_employee.name} - showing error")
                    self.show_popup("Error", f"Tag already assigned to {existing_employee.name}")
                    self.rfid.indicate_error()
            else:
                # New tag
                logger.debug(f"[RFID] New tag detected, setting tag_id to {tag_id.upper()}")
                self.root.get_screen('register').tag_id = str(tag_id).upper()
                self.rfid.indicate_success()
            return

        if current_screen == 'identify':
            if existing_employee:
                role = "Administrator" if existing_employee.is_admin else "Employee"
                info = f"Name: {existing_employee.name}\nID: {existing_employee.rfid_tag}\nRole: {role}"
            else:
                info = f"Tag ID: {tag_id}\nStatus: Unregistriert"
            
            self.root.get_screen('identify').update_info(info)
            return

        # Check for pending badge identification (for view/edit actions)
        pending_id = self.state_service.pending_identification
        if pending_id:
            if existing_employee:
                # Employee identified - notify popup
                if pending_id.popup:
                    pending_id.popup.on_employee_identified(existing_employee)
                self.rfid.indicate_success()
                return
            else:
                # Unknown tag during identification
                if pending_id.popup:
                    pending_id.popup.status_label.text = "Unbekanntes Badge. Bitte versuchen Sie es erneut."
                    pending_id.popup.status_label.color = (1, 0.2, 0.2, 1)  # Red
                self.rfid.indicate_error()
                return

        if not existing_employee:
            self.popup_service.show_error("Unbekannter Tag", f"Tag ID: {tag_id}")
            return

        # If Admin Tag
        if existing_employee.is_admin:
            if current_screen != 'admin':
                self.root.current = 'admin'
            return

        # If Normal Employee
        if current_screen == 'timeclock':
            self.perform_clock_action(existing_employee)
        elif current_screen == 'admin':
            self.popup_service.show_info("Admin Modus", "Please switch to Timeclock mode to clock in/out.")

    def perform_clock_action(self, employee):
        """Perform clock action using clock service"""
        result = self.clock_service.clock_in_out(employee)
        
        if result.success:
            # Show greeter using popup service
            self.popup_service.show_greeter(result.employee, result.action)
            
            # Update UI
            msg = f"Clocked {result.action.upper()} - {result.employee.name}"
            self.root.get_screen('timeclock').update_status(msg)
            
            # Note: State is now updated by ClockService internally
        # Note: Errors are now handled by ClockService internally

    def edit_today_sessions(self):
        """Edit today's sessions - uses state service"""
        employee = self.state_service.last_clocked_employee
        if employee:
            # Within grace period, proceed directly
            # Close any existing main popups before opening new one
            self.popup_service.close_main_popup()
            # Small delay to ensure previous popup is fully closed
            Clock.schedule_once(
                lambda dt: self._open_entry_editor(employee),
                0.1
            )
        else:
            # Outside grace period, require badge identification
            self._request_badge_identification('edit_sessions')
    
    def _open_entry_editor(self, employee):
        """Open entry editor popup after delay"""
        popup = EntryEditorPopup(
            employee,
            on_deleted=lambda: self.state_service.clear_last_clocked_employee()
        )
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()

    def show_today_report_popup(self):
        """Show today's report - uses state service"""
        employee = self.state_service.last_clocked_employee
        if employee:
            # Within grace period, proceed directly
            self._display_today_report(employee)
        else:
            # Outside grace period, require badge identification
            self._request_badge_identification('view_report')
    
    def _display_today_report(self, employee):
        """Display today's report for the given employee with date picker"""
        from .presentation.popups.view_sessions_popup import ViewSessionsPopup
        # Close any existing main popups before opening new one
        self.popup_service.close_main_popup()
        # Small delay to ensure previous popup is fully closed
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._open_view_sessions(employee), 0.1)
    
    def _open_view_sessions(self, employee):
        """Open view sessions popup after delay"""
        from .presentation.popups.view_sessions_popup import ViewSessionsPopup
        popup = ViewSessionsPopup(employee)
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
    
    def _request_badge_identification(self, action_type):
        """
        Show popup requesting badge identification for an action.
        
        Args:
            action_type: 'view_report' or 'edit_sessions'
        """
        # Close any existing identification popup using state service
        self.state_service.clear_pending_identification()
        # Close any existing main popups before opening new one
        self.popup_service.close_main_popup()
        
        # Small delay to ensure previous popup is fully closed
        Clock.schedule_once(
            lambda dt: self._open_badge_identification(action_type),
            0.1
        )
    
    def _open_badge_identification(self, action_type):
        """Open badge identification popup after delay"""
        # Create identification popup
        popup = BadgeIdentificationPopup(
            action_type=action_type,
            on_identified=lambda emp: self._on_employee_identified(emp, action_type)
        )
        if not (hasattr(popup, 'is_open') and popup.is_open):
            popup.open()
        
        # Store pending identification using state service
        self.state_service.set_pending_identification(action_type, popup)
    
    def _on_employee_identified(self, employee, action_type):
        """Handle employee identification and execute the requested action"""
        # Clear pending identification before executing action using state service
        self.state_service.clear_pending_identification()
        
        if action_type == 'view_report':
            self._display_today_report(employee)
        elif action_type == 'edit_sessions':
            EntryEditorPopup(
                employee,
                on_deleted=lambda: self.state_service.clear_last_clocked_employee()
            ).open()

    def show_popup(self, title, content):
        """Legacy method - delegate to popup service"""
        self.popup_service.show_info(title, content)

    def show_greeter(self, employee, action):
        """Legacy method - delegate to popup service"""
        self.popup_service.show_greeter(employee, action)

    def on_stop(self):
        """Cleanup on app stop"""
        if self.rfid:
            self.rfid.stop()
        close_db()


if __name__ == '__main__':
    TimeClockApp().run()
