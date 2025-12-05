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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty

from .database import (
    initialize_db, close_db, Employee, TimeEntry, db,
    get_employee_by_tag, get_admin_count, create_employee, create_time_entry,
    get_time_entries_for_export, get_all_employees, soft_delete_time_entries
)
from .rfid import get_rfid_provider
from peewee import IntegrityError
from .wt_report import WorkingTimeReport, generate_wt_report
from .export_utils import get_export_directory

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

    def update_status(self, message):
        self.status_message = message
        # Clear message after 3 seconds
        Clock.schedule_once(lambda dt: self.set_default_status(), 3)

    def set_default_status(self):
        self.status_message = "Ready"


class EntryEditorPopup(Popup):
    def __init__(self, employee, on_deleted=None, **kwargs):
        super().__init__(
            title=f"Edit {employee.name} - Today's Entries",
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        self.on_deleted = on_deleted
        self.entries = []
        self._load_today_entries()
        self._build_ui()
    
    def _load_today_entries(self):
        """Load all time entries for today"""
        today = datetime.date.today()
        start_datetime = datetime.datetime.combine(today, datetime.time.min)
        end_datetime = datetime.datetime.combine(today, datetime.time.max)
        
        self.entries = list(TimeEntry.select().where(
            TimeEntry.employee == self.employee,
            TimeEntry.active == True,
            TimeEntry.timestamp >= start_datetime,
            TimeEntry.timestamp <= end_datetime
        ).order_by(TimeEntry.timestamp.asc()))
        
        logger.debug(f"[ENTRY_EDITOR] Loaded {len(self.entries)} entries for {self.employee.name}")
    
    def _build_ui(self):
        """Build the UI with all entries"""
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Header
        notice = Label(
            text="Tap 'Delete' to remove an entry. Actions will auto-update.",
            size_hint_y=None,
            height='35dp',
            font_size='14sp'
        )
        layout.add_widget(notice)
        
        # Scrollable list of entries
        scroll = ScrollView(do_scroll_x=False)
        grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        if not self.entries:
            no_entries = Label(
                text="No entries found for today.",
                size_hint_y=None,
                height='40dp'
            )
            grid.add_widget(no_entries)
        else:
            for entry in self.entries:
                row = self._create_entry_row(entry)
                grid.add_widget(row)
        
        scroll.add_widget(grid)
        layout.add_widget(scroll)
        
        # Close button
        close_btn = Button(
            text="Close",
            size_hint_y=None,
            height='50dp',
            background_color=(0.3, 0.6, 0.9, 1)
        )
        close_btn.bind(on_release=lambda *_: self.dismiss())
        layout.add_widget(close_btn)
        
        self.content = layout
    
    def _create_entry_row(self, entry):
        """Create a row widget for a single entry"""
        row = BoxLayout(size_hint_y=None, height='55dp', spacing=10, padding=[5, 0, 5, 0])
        
        # Timestamp and action label
        action_color = (0.2, 0.8, 0.2, 1) if entry.action == 'in' else (0.8, 0.2, 0.2, 1)
        action_text = "IN" if entry.action == 'in' else "OUT"
        
        label = Label(
            text=f"{entry.timestamp.strftime('%H:%M:%S')} - {action_text}",
            halign='left',
            valign='middle',
            text_size=(None, None),
            size_hint_x=0.7,
            color=action_color,
            font_size='16sp',
            bold=True
        )
        
        # Delete button
        delete_btn = Button(
            text="Delete",
            size_hint_x=0.3,
            background_color=(0.9, 0.2, 0.2, 1),
            font_size='14sp'
        )
        delete_btn.bind(on_release=lambda inst, e=entry: self._delete_entry(e))
        
        row.add_widget(label)
        row.add_widget(delete_btn)
        return row
    
    def _delete_entry(self, entry):
        """Delete a single entry and update subsequent actions"""
        logger.debug(f"[ENTRY_EDITOR] Deleting entry ID={entry.id}, action={entry.action}, time={entry.timestamp}")
        
        try:
            # Soft delete the entry
            soft_delete_time_entries([entry.id])
            logger.info(f"[ENTRY_EDITOR] Deleted entry ID={entry.id}")
            
            # Reload entries FIRST (without the deleted one)
            self._load_today_entries()
            
            # Update actions for remaining entries if needed
            self._update_actions_after_deletion()
            
            # Call on_deleted callback if provided
            if self.on_deleted:
                self.on_deleted()
            
            # Close the editor popup FIRST, then navigate
            app = App.get_running_app()
            
            # Close popup and schedule navigation after it's closed
            self.dismiss()
            
            # Use Clock to schedule navigation after popup is fully closed
            Clock.schedule_once(lambda dt: self._after_delete_cleanup(app), 0.1)
                
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error deleting entry: {e}")
            App.get_running_app().show_popup("Error", f"Fehler beim Löschen: {str(e)}")
    
    def _after_delete_cleanup(self, app):
        """Called after popup is dismissed to show success and navigate"""
        app.show_popup("Erfolg", "Eintrag erfolgreich gelöscht")
        app.root.current = "timeclock"
    
    def _update_actions_after_deletion(self):
        """Update actions for remaining entries to ensure proper IN/OUT alternation"""
        if not self.entries:
            logger.debug("[ENTRY_EDITOR] No entries remaining after deletion")
            return
        
        logger.debug(f"[ENTRY_EDITOR] Updating actions for {len(self.entries)} remaining entries")
        
        # Get all entries before today to determine the starting state
        today = datetime.date.today()
        start_datetime = datetime.datetime.combine(today, datetime.time.min)
        
        last_before_today = TimeEntry.select().where(
            TimeEntry.employee == self.employee,
            TimeEntry.active == True,
            TimeEntry.timestamp < start_datetime
        ).order_by(TimeEntry.timestamp.desc()).first()
        
        # Determine what the next action should be
        expected_action = 'in'
        if last_before_today:
            expected_action = 'out' if last_before_today.action == 'in' else 'in'
        
        logger.debug(f"[ENTRY_EDITOR] Starting action should be: {expected_action} (last before today: {last_before_today.action if last_before_today else 'none'})")
        
        # Update entries to alternate properly
        updates_needed = []
        for entry in self.entries:
            if entry.action != expected_action:
                logger.debug(f"[ENTRY_EDITOR] Entry ID={entry.id} at {entry.timestamp.strftime('%H:%M:%S')}: changing from {entry.action} to {expected_action}")
                updates_needed.append((entry.id, expected_action))
            # Toggle for next entry
            expected_action = 'out' if expected_action == 'in' else 'in'
        
        # Apply updates
        if updates_needed:
            try:
                with db.atomic():
                    for entry_id, new_action in updates_needed:
                        TimeEntry.update(action=new_action).where(TimeEntry.id == entry_id).execute()
                logger.info(f"[ENTRY_EDITOR] Updated {len(updates_needed)} entry actions")
            except Exception as e:
                logger.error(f"[ENTRY_EDITOR] Error updating actions: {e}")
        else:
            logger.debug("[ENTRY_EDITOR] No action updates needed - entries already in correct order")

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
    _saving = False  # Prevent double-save
    
    def on_enter(self):
        self.tag_id = "Warte auf Scan..."
        self.ids.name_input.text = ""
        self._saving = False
        # If admin setup mode, keep checkbox checked and disabled
        if get_admin_count() == 0:
             self.ids.admin_checkbox.active = True
             self.ids.admin_checkbox.disabled = True
        else:
             self.ids.admin_checkbox.active = False
             self.ids.admin_checkbox.disabled = False
    
    def cancel(self):
        if get_admin_count() == 0:
             # Can't cancel initial setup
             App.get_running_app().show_popup("Error", "Es muss ein Admin registriert werden, um fortzufahren.")
        else:
             self.manager.current = 'admin'

    def save_user(self):
        # Prevent double-save with early return
        if self._saving:
            logger.debug("[REGISTER] save_user blocked - already saving")
            return
        
        # Check if name_input exists before accessing
        if not hasattr(self, 'ids') or 'name_input' not in self.ids:
            logger.error("[REGISTER] name_input not found in ids!")
            return
        
        self._saving = True
        
        # Get raw text before stripping to debug
        raw_name = self.ids.name_input.text
        name = raw_name.strip() if raw_name else ""
        tag = self.tag_id.strip() if self.tag_id else ""
        is_admin = self.ids.admin_checkbox.active
        
        logger.debug(f"[REGISTER] save_user called: raw_name={raw_name!r}, name={name!r}, tag={tag!r}, is_admin={is_admin}")
        logger.debug(f"[REGISTER] name_input.text={self.ids.name_input.text!r}")
        
        if not name:
            logger.warning(f"[REGISTER] Name validation failed: raw_name={raw_name!r}, name={name!r}, len={len(name) if name else 0}")
            self._saving = False
            App.get_running_app().show_popup("Error", "Bitte geben Sie einen Mitarbeiter Namen ein.")
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
            
            # Success - reset flag BEFORE clearing form/navigating
            self._saving = False
            
            # Clear form and navigate
            self.tag_id = "Warte auf Scan..."
            if hasattr(self, 'ids') and 'name_input' in self.ids:
                self.ids.name_input.text = ""
            self.manager.current = 'admin'
            
            App.get_running_app().show_popup("Success", f"Benutzer {employee.name} erfolgreich erstellt.")
            App.get_running_app().rfid.indicate_success()
        except ValueError as e:
            logger.warning(f"[REGISTER] ValueError: {e}")
            self._saving = False
            App.get_running_app().show_popup("Validation Error", str(e))
            App.get_running_app().rfid.indicate_error()
        except IntegrityError as e:
            logger.warning(f"[REGISTER] IntegrityError: {e}")
            self._saving = False
            App.get_running_app().show_popup("Error", f"Tag ist bereits einem anderen Mitarbeiter zugewiesen.")
            App.get_running_app().rfid.indicate_error()
        except Exception as e:
            logger.error(f"[REGISTER] Unexpected error: {e}")
            self._saving = False
            App.get_running_app().show_popup("Error", f"Fehler beim Erstellen des Benutzers: {str(e)}")
            App.get_running_app().rfid.indicate_error()

# Screen 1: Employee Selection
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
                    btn = Button(
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

# Date Picker Popup - User-friendly calendar-style picker
class DatePickerPopup(Popup):
    selected_date = ObjectProperty(None, allownone=True)
    
    def __init__(self, current_date=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        self.title = "Datum Auswählen"
        self.size_hint = (0.75, 0.65)  # Reduced size
        self.auto_dismiss = False
        
        # Use current date or today
        if current_date is None:
            current_date = datetime.date.today()
        
        self.display_date = current_date  # The month/year being displayed
        self.selected_day = current_date.day
        
        # Create main container
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Header: Month/Year navigation
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=8)
        
        prev_month_btn = Button(
            text="◀",
            font_size='24sp',
            size_hint_x=0.15,
            background_color=(0.3, 0.5, 0.7, 1)
        )
        prev_month_btn.bind(on_release=lambda x: self._change_month(-1))
        
        month_year_label = Label(
            text=f"{self._get_month_name(current_date.month)} {current_date.year}",
            font_size='20sp',
            size_hint_x=0.7,
            bold=True
        )
        
        next_month_btn = Button(
            text="▶",
            font_size='24sp',
            size_hint_x=0.15,
            background_color=(0.3, 0.5, 0.7, 1)
        )
        next_month_btn.bind(on_release=lambda x: self._change_month(1))
        
        header.add_widget(prev_month_btn)
        header.add_widget(month_year_label)
        header.add_widget(next_month_btn)
        
        self.month_year_label = month_year_label
        main_layout.add_widget(header)
        
        # Calendar grid with ScrollView
        calendar_container = BoxLayout(orientation='vertical', spacing=3, size_hint_y=None)
        calendar_container.bind(minimum_height=calendar_container.setter('height'))
        
        # Day names header
        day_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        day_header = GridLayout(cols=7, size_hint_y=None, height='30dp', spacing=2)
        for day_name in day_names:
            label = Label(
                text=day_name,
                font_size='14sp',
                bold=True,
                color=(0.5, 0.5, 0.5, 1)
            )
            day_header.add_widget(label)
        calendar_container.add_widget(day_header)
        
        # Days grid
        days_grid = GridLayout(cols=7, spacing=2, size_hint_y=None)
        days_grid.bind(minimum_height=days_grid.setter('height'))
        self.days_grid = days_grid
        self.day_buttons = []
        
        self._update_calendar()
        calendar_container.add_widget(days_grid)
        
        # ScrollView for calendar
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=8
        )
        scroll.add_widget(calendar_container)
        main_layout.add_widget(scroll)
        
        # Quick actions
        quick_actions = BoxLayout(orientation='horizontal', size_hint_y=None, height='45dp', spacing=8)
        today_btn = Button(
            text="Heute",
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='16sp'
        )
        today_btn.bind(on_release=lambda x: self._select_today())
        quick_actions.add_widget(today_btn)
        
        # Action buttons
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=8)
        ok_btn = Button(
            text="Auswählen",
            background_color=(0, 0.7, 0, 1),
            font_size='18sp'
        )
        ok_btn.bind(on_release=lambda x: self._confirm_date())
        cancel_btn = Button(
            text="Abbrechen",
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='18sp'
        )
        cancel_btn.bind(on_release=self.dismiss)
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)
        
        main_layout.add_widget(quick_actions)
        main_layout.add_widget(btn_layout)
        
        self.content = main_layout
    
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
    
    def _update_calendar(self):
        """Update the calendar grid with days"""
        # Clear existing buttons
        self.days_grid.clear_widgets()
        self.day_buttons = []
        
        # Get first day of month and number of days
        first_day = datetime.date(self.display_date.year, self.display_date.month, 1)
        first_weekday = first_day.weekday()  # 0=Monday, 6=Sunday
        
        # Calculate days in month
        if self.display_date.month == 12:
            next_month = datetime.date(self.display_date.year + 1, 1, 1)
        else:
            next_month = datetime.date(self.display_date.year, self.display_date.month + 1, 1)
        days_in_month = (next_month - first_day).days
        
        # Add empty cells for days before month starts
        for _ in range(first_weekday):
            self.days_grid.add_widget(Widget())
        
        # Add day buttons
        today = datetime.date.today()
        for day in range(1, days_in_month + 1):
            date = datetime.date(self.display_date.year, self.display_date.month, day)
            is_today = (date == today)
            is_selected = (day == self.selected_day)
            
            # Determine button color
            if is_selected:
                bg_color = (0.2, 0.6, 0.9, 1)  # Blue for selected
                text_color = (1, 1, 1, 1)
            elif is_today:
                bg_color = (0.3, 0.7, 0.3, 1)  # Green for today
                text_color = (1, 1, 1, 1)
            else:
                bg_color = (0.4, 0.4, 0.4, 1)  # Gray for normal
                text_color = (1, 1, 1, 1)
            
            btn = Button(
                text=str(day),
                font_size='16sp',
                background_color=bg_color,
                color=text_color,
                size_hint_y=None,
                height='45dp'
            )
            btn.bind(on_release=lambda instance, d=day: self._select_day(d))
            self.days_grid.add_widget(btn)
            self.day_buttons.append(btn)
        
        # Fill remaining cells to complete grid
        total_cells = len(self.day_buttons) + first_weekday
        remaining = (7 - (total_cells % 7)) % 7
        for _ in range(remaining):
            self.days_grid.add_widget(Widget())
    
    def _select_day(self, day):
        """Select a day"""
        self.selected_day = day
        # Update button colors
        today = datetime.date.today()
        for i, btn in enumerate(self.day_buttons):
            day_num = i + 1
            date = datetime.date(self.display_date.year, self.display_date.month, day_num)
            is_today = (date == today)
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
            App.get_running_app().show_popup("Fehler", f"Ungültiges Datum: {str(e)}")

# Screen 2: Date Range Selection
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
        if hasattr(self, 'ids'):
            if 'start_date_button' in self.ids:
                if self.start_date:
                    # Format: "DD.MM.YYYY" (German format)
                    date_str = self.start_date.strftime('%d.%m.%Y')
                    self.ids.start_date_button.text = f"Von: {date_str}"
                else:
                    self.ids.start_date_button.text = "Von: Datum auswählen"
            if 'end_date_button' in self.ids:
                if self.end_date:
                    date_str = self.end_date.strftime('%d.%m.%Y')
                    self.ids.end_date_button.text = f"Bis: {date_str}"
                else:
                    self.ids.end_date_button.text = "Bis: Datum auswählen"
    
    def open_start_date_picker(self):
        """Open date picker for start date"""
        DatePickerPopup(
            current_date=self.start_date or datetime.date.today(),
            on_select=lambda date: self._on_start_date_selected(date)
        ).open()
    
    def open_end_date_picker(self):
        """Open date picker for end date"""
        DatePickerPopup(
            current_date=self.end_date or datetime.date.today(),
            on_select=lambda date: self._on_end_date_selected(date)
        ).open()
    
    def _on_start_date_selected(self, date):
        """Handle start date selection"""
        self.start_date = date
        self._update_date_display()
    
    def _on_end_date_selected(self, date):
        """Handle end date selection"""
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

# Screen 3: Report Display
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

class WindowManager(ScreenManager):
    pass

class TimeClockApp(App):
    # Let Kivy auto-load the KV file by specifying the path
    # This ensures it's loaded exactly once, preventing the "loaded multiples times" warning
    # Path is relative to this file's location (src/main.py -> src/timeclock.kv)
    kv_dir = os.path.dirname(os.path.abspath(__file__))
    kv_file = os.path.join(kv_dir, 'timeclock.kv')
    
    def build(self):
        # Initialize database and RFID before returning root (which is auto-loaded from KV file)
        initialize_db()
        self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False) # Attempt real, fallback to mock
        self.rfid.start()
        self._recent_scan_times = {}
        
        # Check if admin exists
        self.check_initial_setup()
        
        # Root widget is automatically loaded from KV file by Kivy
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
            self._reset_clocked_employee_timer()
        except Exception as e:
            logger.error(f"Error performing clock action: {e}")
            self.show_popup("Error", f"Failed to record time: {str(e)}")
            self.rfid.indicate_error()

    def edit_today_sessions(self):
        employee = getattr(self, 'last_clocked_employee', None)
        if not employee:
            self.show_popup("Info", "Please clock in/out before editing today's sessions.")
            return
        EntryEditorPopup(
            employee,
            on_deleted=lambda: self._reset_clocked_employee_timer()
        ).open()

    def show_today_report_popup(self):
        employee = getattr(self, 'last_clocked_employee', None)
        if not employee:
            self.show_popup("Info", "Please clock in/out before viewing today's report.")
            return
        today = datetime.date.today()
        report = generate_wt_report(employee, today, today)
        text = report.to_text()
        
        # Create scrollable content
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            bar_width=10
        )
        
        label = Label(
            text=text,
            font_size='16sp',
            halign='left',
            valign='top',
            size_hint_y=None,
            text_size=(460, None),
            markup=True
        )
        # Bind height to texture size for proper scrolling
        label.bind(texture_size=lambda inst, size: setattr(inst, 'height', size[1]))
        
        scroll.add_widget(label)
        content.add_widget(scroll)
        
        # Add close button
        close_btn = Button(
            text="Schließen",
            size_hint_y=None,
            height='50dp',
            background_color=(0.3, 0.6, 0.9, 1)
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title=f"Tagesbericht - {employee.name}",
            content=content,
            size_hint=(0.9, 0.85),
            auto_dismiss=True
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _reset_clocked_employee_timer(self):
        """Reset timer that clears last_clocked_employee after inactivity"""
        if hasattr(self, '_employee_timeout_event') and self._employee_timeout_event:
            self._employee_timeout_event.cancel()
        self._employee_timeout_event = Clock.schedule_once(lambda dt: self._clear_last_clocked_employee(), 5)

    def _clear_last_clocked_employee(self):
        """Clear last clocked employee after timeout"""
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
