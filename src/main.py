import logging
import csv
import os
import datetime
import time

# IMPORTANT: Config must be set BEFORE importing Kivy modules
from kivy.config import Config

# Raspberry Pi Touchscreen Optimization / Kiosk Mode
# Disable red dots on touch (multitouch simulation)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
# Enable Kivy's built-in VKeyboard (systemanddock tries system first, then VKeyboard)
Config.set('kivy', 'keyboard_mode', 'systemanddock')
# Force VKeyboard layout
Config.set('kivy', 'keyboard_layout', 'qwerty')

# Now import Kivy modules
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty

from database import (
    initialize_db, close_db, Employee, TimeEntry, db,
    get_employee_by_tag, get_admin_count, create_employee, create_time_entry,
    get_time_entries_for_export, get_all_employees, soft_delete_time_entries
)
from rfid import get_rfid_provider
from peewee import IntegrityError
from wt_report import WorkingTimeReport, generate_wt_report
from export_utils import get_export_directory

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Hide cursor for touch screen usage
Window.show_cursor = False
# Enable Fullscreen (Kiosk Mode)
Window.fullscreen = 'auto'
# Ensure the keyboard doesn't cover the input field by panning the content
Window.softinput_mode = 'below_target'

class FilteredTextInput(TextInput):
    """TextInput that filters duplicate characters to fix double-typing issue"""
    _input_counter = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._input_counter = 0
    
    def insert_text(self, substring, from_undo=False):
        # Filter duplicate characters by only accepting every other input
        # This fixes the double-typing issue by "slicing" input in half
        if from_undo:
            # Always allow undo operations
            return super().insert_text(substring, from_undo)
        
        # For multi-character input (paste), process normally but still filter
        if len(substring) > 1:
            # For pasted text, accept it but reset counter
            self._input_counter = 0
            return super().insert_text(substring, from_undo)
        
        # Increment counter and only insert every other character
        self._input_counter += 1
        if self._input_counter % 2 == 0:
            # Skip this input (it's a duplicate)
            return
        
        # Insert the character
        return super().insert_text(substring, from_undo)
    
    def on_focus(self, instance, value):
        # Reset counter when focus changes
        if value:
            self._input_counter = 0
        # on_focus is a property callback, not a method - no need to call super()
    
    def do_backspace(self, from_undo=False, mode='bkspc'):
        # Reset counter when backspace is used
        self._input_counter = 0
        return super().do_backspace(from_undo, mode)

class TimeClockScreen(Screen):
    status_message = StringProperty("Ready")
    show_today_buttons = BooleanProperty(False)

    def update_status(self, message):
        self.status_message = message
        # Clear message after 3 seconds
        Clock.schedule_once(lambda dt: self.set_default_status(), 3)

    def set_default_status(self):
        self.status_message = "Ready"


class EntryEditorPopup(Popup):
    def __init__(self, employee, sessions, on_deleted=None, **kwargs):
        super().__init__(
            title=f"Edit {employee.name} Entries",
            size_hint=(None, None),
            size=(520, 420),
            auto_dismiss=False,
            **kwargs
        )
        self.sessions = sessions or []
        self.on_deleted = on_deleted
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        notice = Label(text="Delete sessions to fix double entries", size_hint_y=None, height='40dp')
        layout.add_widget(notice)
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for session in self.sessions:
            clock_in = session.get('clock_in')
            clock_out = session.get('clock_out')
            if not clock_in or not clock_out:
                continue
            row = BoxLayout(size_hint_y=None, height='60dp', spacing=10)
            label = Label(
                text=f"{clock_in.strftime('%H:%M:%S')} → {clock_out.strftime('%H:%M:%S')} ({session['formatted_time']})",
                halign='left',
                valign='middle',
                text_size=(400, None)
            )
            label.bind(size=lambda inst, size: label.setter('text_size')(inst, (size[0], None)))
            delete_btn = Button(text="Delete", size_hint_x=None, width='120dp', background_color=(1, 0.2, 0.2, 1))
            delete_btn.bind(on_release=lambda inst, sess=session: self._delete_session(sess))
            row.add_widget(label)
            row.add_widget(delete_btn)
            grid.add_widget(row)
        scroll.add_widget(grid)
        layout.add_widget(scroll)
        close_btn = Button(text="Close", size_hint_y=None, height='50dp')
        close_btn.bind(on_release=lambda *_: self.dismiss())
        layout.add_widget(close_btn)
        self.content = layout

    def _delete_session(self, session):
        entry_ids = [session.get('clock_in_entry_id'), session.get('clock_out_entry_id')]
        entry_ids = [eid for eid in entry_ids if eid]
        if not entry_ids:
            return
        soft_delete_time_entries(entry_ids)
        if self.on_deleted:
            self.on_deleted()
        self.dismiss()

class AdminScreen(Screen):
    def export_csv(self):
        try:
            export_dir = get_export_directory()
            filename = os.path.join(
                export_dir,
                f"timeclock_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            entries = get_time_entries_for_export()
            entry_count = entries.count()
            
            if entry_count == 0:
                App.get_running_app().show_popup("Export Info", "No time entries to export.")
                return
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Employee Name', 'Tag ID', 'Action', 'Timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                
                for entry in entries:
                    try:
                        writer.writerow({
                            'Employee Name': entry.employee.name,
                            'Tag ID': entry.employee.rfid_tag,
                            'Action': entry.action.upper(),
                            'Timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except Exception as e:
                        logger.warning(f"Skipping entry due to error: {e}")
                        continue
            
            App.get_running_app().show_popup(
                "Export Success", 
                f"Exported {entry_count} entries to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Failed to export: {str(e)}")

class IdentifyScreen(Screen):
    tag_info = StringProperty("Scan a tag to identify...")
    
    def on_enter(self):
        self.tag_info = "Ready to Scan..."

    def update_info(self, text):
        self.tag_info = text

class RegisterScreen(Screen):
    tag_id = StringProperty("Warte auf Scan...")
    _last_input_time = 0.0
    _saving = False  # Prevent double-save
    
    def on_enter(self):
        self.tag_id = "Warte auf Scan..."
        self.ids.name_input.text = ""
        self._last_input_time = 0.0
        self._saving = False
        # If admin setup mode, keep checkbox checked and disabled
        if get_admin_count() == 0:
             self.ids.admin_checkbox.active = True
             self.ids.admin_checkbox.disabled = True
        else:
             self.ids.admin_checkbox.active = False
             self.ids.admin_checkbox.disabled = False
    
    def on_textinput_focus(self, instance, value):
        """Handle focus events to ensure keyboard shows properly"""
        if value:  # When focused
            # TextInput automatically requests keyboard when focused
            # No additional action needed - Kivy handles it
            pass

    def cancel(self):
        if get_admin_count() == 0:
             # Can't cancel initial setup
             App.get_running_app().show_popup("Error", "Es muss ein Admin registriert werden, um fortzufahren.")
        else:
             self.manager.current = 'admin'

    def save_user(self):
        # Prevent double-save
        if self._saving:
            logger.debug("[REGISTER] save_user blocked - already saving")
            return
        self._saving = True
        
        name = self.ids.name_input.text.strip()
        tag = self.tag_id.strip() if self.tag_id else ""
        is_admin = self.ids.admin_checkbox.active
        
        logger.debug(f"[REGISTER] save_user called: name={name!r}, tag={tag!r}, is_admin={is_admin}")
        
        if not name:
            App.get_running_app().show_popup("Error", "Bitte geben Sie einen Mitarbeiter Namen ein.")
            self._saving = False
            return
        
        if not tag or tag == "Warte auf Scan..." or len(tag) < 4:
            App.get_running_app().show_popup("Error", "Bitte scannen Sie zuerst ein RFID Tag.")
            self._saving = False
            return
        normalized_tag = tag.upper()
        self.tag_id = normalized_tag
        
        try:
            logger.debug(f"[REGISTER] Calling create_employee({name!r}, {normalized_tag!r}, {is_admin})")
            employee = create_employee(name, normalized_tag, is_admin)
            logger.debug(f"[REGISTER] Employee created successfully: {employee.name}")
            
            # Clear form and navigate
            self.tag_id = "Warte auf Scan..."
            self.ids.name_input.text = ""
            self.manager.current = 'admin'
            
            App.get_running_app().show_popup("Success", f"Benutzer {employee.name} erfolgreich erstellt.")
            App.get_running_app().rfid.indicate_success()
        except ValueError as e:
            logger.warning(f"[REGISTER] ValueError: {e}")
            App.get_running_app().show_popup("Validation Error", str(e))
            App.get_running_app().rfid.indicate_error()
        except IntegrityError as e:
            logger.warning(f"[REGISTER] IntegrityError: {e}")
            App.get_running_app().show_popup("Error", f"Tag ist bereits einem anderen Mitarbeiter zugewiesen.")
            App.get_running_app().rfid.indicate_error()
        except Exception as e:
            logger.error(f"[REGISTER] Unexpected error: {e}")
            App.get_running_app().show_popup("Error", f"Fehler beim Erstellen des Benutzers: {str(e)}")
            App.get_running_app().rfid.indicate_error()
        finally:
            self._saving = False

class WTReportScreen(Screen):
    report_text = StringProperty("Wählen Sie einen Mitarbeiter und einen Zeitraum, um einen Bericht zu generieren...")
    selected_employee = ObjectProperty(None, allownone=True)
    
    def on_enter(self):
        """Load employees when screen is entered"""
        self.load_employees()
        self.report_text = "Wählen Sie einen Mitarbeiter und einen Zeitraum, um einen Bericht zu generieren..."
        self.selected_employee = None
        if hasattr(self, 'ids') and 'report_display' in self.ids:
            self.ids.report_display.text = self.report_text
    
    def load_employees(self):
        """Load list of employees and create selection buttons"""
        try:
            employees = list(get_all_employees(include_inactive=False))
            self.employees_list = employees
            
            # Clear existing buttons
            if hasattr(self, 'ids') and 'employee_buttons_container' in self.ids:
                container = self.ids.employee_buttons_container
                container.clear_widgets()
                
                # Create button for each employee
                for employee in employees:
                    btn = Button(
                        text=f"{employee.name} ({employee.rfid_tag})",
                        size_hint_y=None,
                        height='60dp',
                        font_size='20sp'
                    )
                    # Bind button to select this employee
                    btn.bind(on_release=lambda instance, emp=employee: self.select_employee(emp))
                    container.add_widget(btn)
                    
        except Exception as e:
            logger.error(f"Error loading employees: {e}")
            self.employees_list = []
    
    def generate_report(self):
        """Generate WT report for selected employee"""
        if not hasattr(self, 'selected_employee') or self.selected_employee is None:
            App.get_running_app().show_popup("Error", "Bitte wählen Sie zuerst einen Mitarbeiter.")
            return
        
        try:
            # Get date range from inputs (if they exist)
            start_date = None
            end_date = None
            
            # Try to get dates from text inputs if they exist
            if hasattr(self, 'ids'):
                if 'start_date_input' in self.ids and self.ids.start_date_input.text:
                    try:
                        start_date = datetime.datetime.strptime(self.ids.start_date_input.text, '%Y-%m-%d').date()
                    except ValueError:
                        App.get_running_app().show_popup("Error", "Ungültiges Startdatum Format. Verwenden Sie YYYY-MM-DD")
                        return
                
                if 'end_date_input' in self.ids and self.ids.end_date_input.text:
                    try:
                        end_date = datetime.datetime.strptime(self.ids.end_date_input.text, '%Y-%m-%d').date()
                    except ValueError:
                        App.get_running_app().show_popup("Error", "Ungültiges Enddatum Format. Verwenden Sie YYYY-MM-DD")
                        return
            
            # Generate report (generate_wt_report already calls generate() internally)
            report = generate_wt_report(self.selected_employee, start_date, end_date)
            
            # Display report
            self.report_text = report.to_text()
            if hasattr(self, 'ids') and 'report_display' in self.ids:
                self.ids.report_display.text = self.report_text
                # Update height
                self.ids.report_display.height = max(self.ids.report_display.texture_size[1] if self.ids.report_display.texture_size else 200, 200)
            
            # Store report for export
            self.current_report = report
            
            App.get_running_app().show_popup("Success", "Report generated successfully!")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            App.get_running_app().show_popup("Error", f"Failed to generate report: {str(e)}")
    
    def export_report(self):
        """Export current report to CSV"""
        if not hasattr(self, 'current_report'):
            App.get_running_app().show_popup("Error", "Please generate a report first.")
            return
        
        try:
            export_dir = get_export_directory()
            filename = self.current_report.to_csv(export_root=export_dir)
            App.get_running_app().show_popup(
                "Export Success",
                f"WT Report exported to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            App.get_running_app().show_popup("Error", f"Failed to export report: {str(e)}")
    
    def select_employee(self, employee):
        """Select an employee for the report"""
        self.selected_employee = employee
        if hasattr(self, 'ids') and 'employee_label' in self.ids:
            self.ids.employee_label.text = f"Selected: {employee.name}"
            self.ids.employee_label.color = 0, 1, 0, 1  # Green color

    def prepare_for_report(self, employee, start_date, end_date):
        self.load_employees()
        self.select_employee(employee)
        if hasattr(self, 'ids'):
            if 'start_date_input' in self.ids:
                self.ids.start_date_input.text = start_date.strftime('%Y-%m-%d')
            if 'end_date_input' in self.ids:
                self.ids.end_date_input.text = end_date.strftime('%Y-%m-%d')
        self.generate_report()

class WindowManager(ScreenManager):
    pass

class TimeClockApp(App):
    def build(self):
        initialize_db()
        self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False) # Attempt real, fallback to mock
        self.rfid.start()
        self._recent_scan_times = {}
        
        # Load KV
        self.root = Builder.load_file('src/timeclock.kv')
        
        # Check if admin exists
        self.check_initial_setup()
        
        return self.root

    def check_initial_setup(self):
        if get_admin_count() == 0:
            # No admin, force setup
            Clock.schedule_once(lambda dt: self.show_initial_setup(), 0.5)

    def show_initial_setup(self):
        self.root.current = 'register'
        self.root.get_screen('register').ids.admin_checkbox.active = True
        self.root.get_screen('register').ids.admin_checkbox.disabled = True # Force admin for first user
        self.show_popup("Welcome", "Please register the initial Administrator.")

    def on_rfid_scan(self, tag_id):
        # Schedule handling on main thread
        Clock.schedule_once(lambda dt: self.handle_scan(tag_id), 0)

    def handle_scan(self, tag_id):
        logger.info(f"Handling scan: {tag_id}")
        
        current_screen = self.root.current
        now = time.monotonic()
        last_scan = self._recent_scan_times.get(tag_id)
        if last_scan and now - last_scan < 1.2:
            logger.debug("Ignoring duplicate scan for %s", tag_id)
            return
        self._recent_scan_times[tag_id] = now
        
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

        if not existing_employee:
            self.show_popup("Unbekannter Tag", f"Tag ID: {tag_id}")
            return

        employee = existing_employee

        # If Admin Tag
        if employee.is_admin:
            if current_screen != 'admin':
                self.root.current = 'admin'
            return

        # If Normal Employee
        if current_screen == 'timeclock':
            self.perform_clock_action(employee)
        elif current_screen == 'admin':
            self.show_popup("Admin Modus", "Please switch to Timeclock mode to clock in/out.")

    def perform_clock_action(self, employee):
        try:
            # Find last entry
            last_entry = TimeEntry.get_last_for_employee(employee)
            
            action = 'in'
            if last_entry and last_entry.action == 'in':
                action = 'out'
            
            create_time_entry(employee, action)
            
            msg = f"Clocked {action.upper()} - {employee.name}"
            self.root.get_screen('timeclock').update_status(msg)
            logger.info(msg)
            self.rfid.indicate_success()
            self.last_clocked_employee = employee
            self._reveal_today_button_panel()
        except Exception as e:
            logger.error(f"Error performing clock action: {e}")
            self.show_popup("Error", f"Failed to record time: {str(e)}")
            self.rfid.indicate_error()

    def open_today_wt_report(self):
        employee = getattr(self, 'last_clocked_employee', None)
        if not employee:
            self.show_popup("Info", "Please clock in/out before viewing today's report.")
            return
        today = datetime.date.today()
        self.open_wt_report(employee, today, today)

    def edit_today_sessions(self):
        employee = getattr(self, 'last_clocked_employee', None)
        if not employee:
            self.show_popup("Info", "Please clock in/out before editing today's sessions.")
            return
        today = datetime.date.today()
        report = generate_wt_report(employee, today, today)
        EntryEditorPopup(employee, report.daily_sessions, on_deleted=lambda: self._reveal_today_button_panel()).open()

    def show_today_report_popup(self):
        employee = getattr(self, 'last_clocked_employee', None)
        if not employee:
            self.show_popup("Info", "Please clock in/out before viewing today's report.")
            return
        today = datetime.date.today()
        report = generate_wt_report(employee, today, today)
        text = report.to_text()
        scroll = ScrollView(size_hint=(1, 1))
        label = Label(text=text, font_size='18sp', halign='left', valign='top', text_size=(480, None))
        label.bind(texture_size=lambda inst, size: label.setter('height')(inst, size[1]))
        scroll.add_widget(label)
        popup = Popup(title="Today's Report", content=scroll, size_hint=(None, None), size=(520, 520))
        popup.open()

    def open_wt_report(self, employee, start_date, end_date):
        screen = self.root.get_screen('wtreport')
        screen.prepare_for_report(employee, start_date, end_date)
        self.root.current = 'wtreport'

    def open_entry_editor(self, employee, sessions, on_deleted):
        if not sessions:
            App.get_running_app().show_popup("Info", "No sessions to edit.")
            return
        editor = EntryEditorPopup(employee, sessions, on_deleted=lambda: self._reveal_today_button_panel())
        editor.open()

    def _reveal_today_button_panel(self):
        screen = self.root.get_screen('timeclock')
        screen.show_today_buttons = True
        if hasattr(self, '_today_buttons_event') and self._today_buttons_event:
            self._today_buttons_event.cancel()
        self._today_buttons_event = Clock.schedule_once(lambda dt: self._hide_today_button_panel(), 5)

    def _hide_today_button_panel(self):
        screen = self.root.get_screen('timeclock')
        screen.show_today_buttons = False
        self.last_clocked_employee = None

    def show_popup(self, title, content):
        popup = Popup(title=title, content=Label(text=content), size_hint=(None, None), size=(400, 200))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 3)

    def on_stop(self):
        self.rfid.stop()
        close_db()

if __name__ == '__main__':
    TimeClockApp().run()
