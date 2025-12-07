import logging
import csv
import os
import datetime
import time
import random
import io
import sqlite3
import tempfile

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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty

from .database import (
    initialize_db, close_db, Employee, TimeEntry, db,
    get_employee_by_tag, get_admin_count, create_employee, create_time_entry,
    get_time_entries_for_export, get_all_employees, soft_delete_time_entries,
    ensure_db_connection
)
from .rfid import get_rfid_provider
from peewee import IntegrityError
from .wt_report import WorkingTimeReport, generate_wt_report
from .export_utils import get_export_directory, write_file
from .screensaver import ScreensaverScreen

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Hide cursor for touch screen usage
Window.show_cursor = False
# Enable Fullscreen (Kiosk Mode)
Window.fullscreen = 'auto'
# Ensure the keyboard doesn't cover the input field by panning the content
Window.softinput_mode = 'below_target'

class DebouncedButton(Button):
    """Button that prevents double-clicks (debouncing)"""
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        # Check for rapid successive touches (global debounce)
        current_time = time.time()
        if hasattr(self, '_last_touch_time'):
            if current_time - self._last_touch_time < 0.3:  # 300ms debounce
                return True # Consume the event without action
        self._last_touch_time = current_time
        
        return super().on_touch_down(touch)

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


class GlobalInputFilter:
    """
    Brute-force, app-wide input de-duplicator for all touch events
    (buttons, VKeyboard keys, etc.). Any touch that lands within
    a small distance/time window of the previous touch is swallowed.
    """
    def __init__(self, window, time_threshold=0.3, distance_threshold=8):
        self.window = window
        self.time_threshold = time_threshold
        self.distance_threshold = distance_threshold
        self._last_event = None

    def install(self):
        # Bind to all touch events; returning True stops propagation
        self.window.bind(on_touch_down=self._filter_touch)
        self.window.bind(on_touch_move=self._filter_touch)
        self.window.bind(on_touch_up=self._filter_touch)

    def _filter_touch(self, window, touch):
        now = time.monotonic()
        dev = getattr(touch, 'device', '')
        pos = touch.pos if hasattr(touch, 'pos') else (0, 0)

        if self._last_event:
            dt = now - self._last_event['time']
            dx = abs(pos[0] - self._last_event['pos'][0])
            dy = abs(pos[1] - self._last_event['pos'][1])
            same_dev = dev == self._last_event['dev']
            if same_dev and dt < self.time_threshold and dx < self.distance_threshold and dy < self.distance_threshold:
                return True  # Swallow duplicate

        self._last_event = {'time': now, 'pos': pos, 'dev': dev}
        return False

class GlobalKeyFilter:
    """
    Global de-duplication for keyboard/VKeyboard input (text + function keys).
    Any identical token (character or key name) within the debounce window is swallowed.
    """
    def __init__(self, window, time_threshold=0.25):
        self.window = window
        self.time_threshold = time_threshold
        self._last_token = None  # (token, timestamp)

    def install(self):
        # Bind both text input and key_down to catch chars and function keys
        self.window.bind(on_textinput=self._on_textinput)
        self.window.bind(on_key_down=self._on_key_down)
        self.window.bind(on_key_up=self._on_key_up)

    def _should_swallow(self, token):
        now = time.monotonic()
        if self._last_token:
            last_tok, last_time = self._last_token
            if token == last_tok and (now - last_time) < self.time_threshold:
                return True
        self._last_token = (token, now)
        return False

    def _on_textinput(self, window, text):
        if not text:
            return False
        return self._should_swallow(text)

    def _on_key_down(self, window, keycode, scancode, codepoint, modifiers):
        # keycode is (code, name)
        name = keycode[1] if keycode and len(keycode) > 1 else str(keycode)
        token = name or ''
        # Normalize shift variants to one token to catch duplicate shift presses
        if name in ('shift', 'lshift', 'rshift', 'capslock'):
            token = '__SHIFT__'
        if not token:
            return False
        return self._should_swallow(token)

    def _on_key_up(self, window, keycode):
        # Apply same logic on key_up to catch rapid duplicate ups
        name = keycode[1] if keycode and len(keycode) > 1 else str(keycode)
        token = name or ''
        if name in ('shift', 'lshift', 'rshift', 'capslock'):
            token = '__SHIFT__'
        if not token:
            return False
        return self._should_swallow(token)

class TimeClockScreen(Screen):
    status_message = StringProperty("Ready")

    def update_status(self, message):
        self.status_message = message
        # Clear message after 3 seconds
        Clock.schedule_once(lambda dt: self.set_default_status(), 3)

    def set_default_status(self):
        self.status_message = "Ready"


class GreeterPopup(Popup):
    greeting = StringProperty("")
    message = StringProperty("")
    color_theme = ObjectProperty((0, 1, 0, 1)) # Green for IN, Orange for OUT
    
    # Available languages: 'ch' (Schweizerdeutsch), 'de' (Deutsch), 'it' (Italienisch), 'rm' (Rätoromanisch)
    AVAILABLE_LANGUAGES = ['ch', 'de', 'it', 'rm']
    
    def __init__(self, employee, action, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.separator_height = 0
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = True
        
        name = employee.name.split()[0] # First name
        
        # Determine shift based on current time
        shift = self._get_shift()
        
        # Select language based on entropy (tag_id, time, employee_id, cpu_temp)
        language = self._select_language(employee)
        
        # Build filename based on action, shift, and language
        filename = self._get_greeting_filename(action, shift, language)
        
        if action == 'in':
            self.greeting = f"Hallo, {name}!"
            self.message = self._get_random_message(filename, "Gute Schicht!", name)
            self.color_theme = (0.2, 0.8, 0.2, 1) # Green
        else:
            self.greeting = f"Tschüss, {name}!"
            self.message = self._get_random_message(filename, "Schönen Feierabend!", name)
            self.color_theme = (1, 0.6, 0, 1) # Orange
            
        Clock.schedule_once(self.dismiss, 3)

    def _get_shift(self):
        """Determine current shift based on time of day"""
        now = datetime.datetime.now()
        hour = now.hour
        
        # Morning shift: 06:00 - 14:00
        if 6 <= hour < 14:
            return 'morning'
        # Midday shift: 10:00 - 18:00 (overlaps with morning)
        elif 10 <= hour < 18:
            # If in overlap (10-14), prefer midday for more variety
            if 10 <= hour < 14:
                return 'midday'
            return 'midday'
        # Evening shift: 17:00 - end of day
        elif hour >= 17 or hour < 6:
            return 'evening'
        # Default to morning for early hours (0-6)
        else:
            return 'morning'
    
    def _select_language(self, employee):
        """Select language randomly based on entropy from tag_id, time, employee_id, and cpu_temp (I hardclocked this cpu hence no freq rate)"""
        try:
            # Get tag ID (RFID tag)
            tag_id = employee.rfid_tag if hasattr(employee, 'rfid_tag') else ''
            
            # Get current time components for entropy
            now = datetime.datetime.now()
            time_hash = now.hour * 3600 + now.minute * 60 + now.second
            
            # Get employee ID
            employee_id = employee.id if hasattr(employee, 'id') else 0
            
            # Get CPU temperature (Raspberry Pi)
            cpu_temp = self._get_cpu_temperature()
            
            # Combine all entropy sources
            entropy_string = f"{tag_id}{time_hash}{employee_id}{cpu_temp}"
            
            # Create hash from combined string
            entropy_hash = hash(entropy_string)
            
            # Use hash to select language deterministically
            language_index = abs(entropy_hash) % len(self.AVAILABLE_LANGUAGES)
            selected_language = self.AVAILABLE_LANGUAGES[language_index]
            
            logger.debug(f"Language selection: tag={tag_id}, time={time_hash}, emp_id={employee_id}, temp={cpu_temp}, hash={entropy_hash}, lang={selected_language}")
            
            return selected_language
        except Exception as e:
            logger.warning(f"Error selecting language, using default 'de': {e}")
            return 'de'  # Default fallback
    
    def _get_cpu_temperature(self):
        """Read CPU temperature from Raspberry Pi thermal zone"""
        try:
            # Try Raspberry Pi thermal zone
            temp_path = '/sys/class/thermal/thermal_zone0/temp'
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    temp_millidegrees = int(f.read().strip())
                    return temp_millidegrees // 1000  # Convert to degrees Celsius
        except Exception as e:
            logger.debug(f"Could not read CPU temperature: {e}")
        
        # Fallback: use current time in seconds as pseudo-temperature
        return int(time.time()) % 100
    
    def _get_greeting_filename(self, action, shift, language):
        """Build filename based on action, shift, and language"""
        action_part = 'in' if action == 'in' else 'out'
        return f'greetings/greetings_{action_part}_{shift}_{language}.txt'

    def _get_random_message(self, filename, default_msg, employee_name):
        """Load a random message from a file, replace [Name] placeholder, or return default if failed"""
        # Try specific shift file first
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    # Filter out empty lines, section headers, and comments
                    lines = []
                    for line in f:
                        stripped = line.strip()
                        # Skip empty lines, section headers (emojis), and time range comments
                        if stripped and not stripped.startswith('🌅') and not stripped.startswith('☀️') and not stripped.startswith('🌙') and not stripped.startswith('(') and not stripped.startswith('ca.'):
                            lines.append(stripped)
                    if lines:
                        message = random.choice(lines)
                        # Replace [Name] placeholder with actual employee name
                        message = message.replace('[Name]', employee_name)
                        return message
        except Exception as e:
            logger.warning(f"Error loading greeting from {filename}: {e}")
        
        # Fallback to general greeting files if specific shift file not found
        fallback_file = 'greetings/greetings_in.txt' if 'in' in filename else 'greetings/greetings_out.txt'
        try:
            if os.path.exists(fallback_file):
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    lines = []
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('🌅') and not stripped.startswith('☀️') and not stripped.startswith('🌙') and not stripped.startswith('(') and not stripped.startswith('ca.'):
                            lines.append(stripped)
                    if lines:
                        message = random.choice(lines)
                        message = message.replace('[Name]', employee_name)
                        return message
        except Exception as e:
            logger.warning(f"Error loading fallback greeting from {fallback_file}: {e}")
        
        # Replace [Name] in default message too
        return default_msg.replace('[Name]', employee_name) if '[Name]' in default_msg else default_msg

class EntryEditorPopup(Popup):
    def __init__(self, employee, on_deleted=None, **kwargs):
        super().__init__(
            title=f"Edit {employee.name} - Today's Entries",
            size_hint=(0.95, 0.95),
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

        add_btn = DebouncedButton(
            text="Add Manual Entry",
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.7, 1, 1)
        )
        add_btn.bind(on_release=lambda *_: self._open_add_entry())
        layout.add_widget(add_btn)
        
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
        close_btn = DebouncedButton(
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
        delete_btn = DebouncedButton(
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
            
            # Reload entries and update actions for remaining entries
            self._load_today_entries()
            self._update_actions_after_deletion(entry.id)
            
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

    def _open_add_entry(self):
        """Open popup to add a manual entry"""
        AddEntryPopup(
            employee=self.employee,
            on_save=self._save_manual_entry
        ).open()

    def _save_manual_entry(self, action, timestamp):
        """Persist manual entry and refresh state"""
        try:
            ensure_db_connection()
            with db.atomic():
                TimeEntry.create(
                    employee=self.employee,
                    timestamp=timestamp,
                    action=action,
                    active=True
                )
            logger.info(f"[ENTRY_EDITOR] Added manual entry {action} at {timestamp}")
            # Reload entries and inform user
            self._load_today_entries()
            app = App.get_running_app()
            self.dismiss()
            app.show_popup("Erfolg", f"Manueller Eintrag ({action.upper()}) gespeichert.")
            app.root.current = "timeclock"
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error adding manual entry: {e}")
            App.get_running_app().show_popup("Error", f"Fehler beim Hinzufügen: {str(e)}")
    
    def _after_delete_cleanup(self, app):
        """Called after popup is dismissed to show success and navigate"""
        app.show_popup("Erfolg", "Eintrag erfolgreich gelöscht")
        app.root.current = "timeclock"
    
    def _update_actions_after_deletion(self, deleted_entry_id):
        """Flip actions for all entries after the deleted one to maintain IN/OUT alternation"""
        entries_to_flip = [e for e in self.entries if e.id > deleted_entry_id and e.active]
        if not entries_to_flip:
            return
        
        try:
            ensure_db_connection()
            with db.atomic():
                for entry in entries_to_flip:
                    new_action = "out" if entry.action == "in" else "in"
                    TimeEntry.update(action=new_action).where(TimeEntry.id == entry.id).execute()
            logger.info(f"[ENTRY_EDITOR] Flipped {len(entries_to_flip)} entry actions")
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error updating actions: {e}")

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
            fieldnames = ['Employee Name', 'Tag ID', 'Action', 'Timestamp']
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=fieldnames)
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

            write_file(buffer.getvalue().encode('utf-8'), filename)
            
            App.get_running_app().show_popup(
                "Export Success", 
                f"Export ({entry_count} entries) saved to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Failed to export: {str(e)}")

    def export_database(self):
        temp_path = None
        try:
            export_dir = get_export_directory()
            filename = os.path.join(
                export_dir,
                f"timeclock_db_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
            )

            db_path = os.path.abspath(db.database)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            source_conn = sqlite3.connect(db_path, timeout=10)
            dest_conn = sqlite3.connect(temp_path)
            source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()

            with open(temp_path, "rb") as f:
                db_bytes = f.read()

            write_file(db_bytes, filename)
            App.get_running_app().show_popup(
                "Export Success",
                f"Database export saved to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"Database export failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Failed to export database: {str(e)}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not remove temp file {temp_path}: {cleanup_error}")

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
        
        logger.debug(f"[REGISTER] save_user: name={name!r}, tag={tag!r}, is_admin={is_admin}")
        
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
            self.ids.name_input.text = ""
            app = App.get_running_app()

            self.manager.current = 'admin'

            app.show_popup("Success", f"Benutzer {employee.name} erfolgreich erstellt.")
            app.rfid.indicate_success()
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

# Date Picker Popup - Optimized for 800x480 Landscape
class DatePickerPopup(Popup):
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
        
        next_month_btn = Button(
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


class TimePickerPopup(Popup):
    selected_time = ObjectProperty(None, allownone=True)

    def __init__(self, current_time=None, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback = on_select
        now = current_time or datetime.datetime.now().time()
        self.selected_hour = now.hour
        self.selected_minute = (now.minute // 5) * 5  # round to 5 minutes

        self.title = "Zeit Auswählen"
        self.size_hint = (0.6, 0.6)
        self.auto_dismiss = False

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Hour/Minute selectors
        selectors = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='60dp')
        self.hour_spinner = Spinner(
            text=f"{self.selected_hour:02d}",
            values=[f"{h:02d}" for h in range(24)],
            size_hint_x=0.5
        )
        self.minute_spinner = Spinner(
            text=f"{self.selected_minute:02d}",
            values=[f"{m:02d}" for m in range(0, 60, 5)],
            size_hint_x=0.5
        )
        selectors.add_widget(self.hour_spinner)
        selectors.add_widget(self.minute_spinner)
        layout.add_widget(selectors)

        # Buttons
        btn_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='50dp')
        ok_btn = DebouncedButton(text="OK", background_color=(0, 0.7, 0, 1))
        cancel_btn = DebouncedButton(text="Abbrechen", background_color=(0.7, 0.2, 0.2, 1))
        ok_btn.bind(on_release=self._confirm_time)
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        self.content = layout

    def _confirm_time(self, *_):
        try:
            hour = int(self.hour_spinner.text)
            minute = int(self.minute_spinner.text)
            t = datetime.time(hour=hour, minute=minute)
            if self.on_select_callback:
                self.on_select_callback(t)
            self.dismiss()
        except ValueError:
            App.get_running_app().show_popup("Fehler", "Ungültige Zeit")


class AddEntryPopup(Popup):
    def __init__(self, employee, on_save=None, **kwargs):
        super().__init__(
            title=f"Manuellen Eintrag hinzufügen - {employee.name}",
            size_hint=(0.9, 0.7),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        self.on_save_callback = on_save
        now = datetime.datetime.now()
        self.selected_date = now.date()
        self.selected_time = now.time().replace(second=0, microsecond=0)
        self.selected_action = 'in'

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Date selection
        self.date_btn = DebouncedButton(
            text=f"Datum: {self.selected_date.strftime('%d.%m.%Y')}",
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.date_btn.bind(on_release=lambda *_: self._pick_date())
        layout.add_widget(self.date_btn)

        # Time selection
        self.time_btn = DebouncedButton(
            text=f"Zeit: {self.selected_time.strftime('%H:%M')}",
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.time_btn.bind(on_release=lambda *_: self._pick_time())
        layout.add_widget(self.time_btn)

        # Action selection
        action_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='50dp')
        self.in_btn = DebouncedButton(text="IN", background_color=(0.2, 0.8, 0.2, 1))
        self.out_btn = DebouncedButton(text="OUT", background_color=(0.8, 0.2, 0.2, 1))
        self.in_btn.bind(on_release=lambda *_: self._set_action('in'))
        self.out_btn.bind(on_release=lambda *_: self._set_action('out'))
        action_row.add_widget(self.in_btn)
        action_row.add_widget(self.out_btn)
        layout.add_widget(action_row)
        self._update_action_buttons()

        # Buttons
        btn_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='50dp')
        save_btn = DebouncedButton(text="Speichern", background_color=(0, 0.7, 0, 1))
        cancel_btn = DebouncedButton(text="Abbrechen", background_color=(0.7, 0.2, 0.2, 1))
        save_btn.bind(on_release=lambda *_: self._save())
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        self.content = layout

    def _pick_date(self):
        DatePickerPopup(
            current_date=self.selected_date,
            on_select=self._set_date
        ).open()

    def _pick_time(self):
        TimePickerPopup(
            current_time=self.selected_time,
            on_select=self._set_time
        ).open()

    def _set_date(self, date_obj):
        self.selected_date = date_obj
        self.date_btn.text = f"Datum: {self.selected_date.strftime('%d.%m.%Y')}"

    def _set_time(self, time_obj):
        self.selected_time = time_obj
        self.time_btn.text = f"Zeit: {self.selected_time.strftime('%H:%M')}"

    def _set_action(self, action):
        self.selected_action = action
        self._update_action_buttons()

    def _update_action_buttons(self):
        if self.selected_action == 'in':
            self.in_btn.background_color = (0.1, 0.6, 0.1, 1)
            self.out_btn.background_color = (0.6, 0.2, 0.2, 1)
        else:
            self.in_btn.background_color = (0.2, 0.8, 0.2, 1)
            self.out_btn.background_color = (0.6, 0.1, 0.1, 1)

    def _save(self):
        try:
            ts = datetime.datetime.combine(self.selected_date, self.selected_time)
            if self.on_save_callback:
                self.on_save_callback(self.selected_action, ts)
            self.dismiss()
        except Exception as e:
            logger.error(f"[ADD_ENTRY] Error combining date/time: {e}")
            App.get_running_app().show_popup("Error", f"Ungültiges Datum/Zeit: {str(e)}")
    
    def _get_month_name(self, month):
        """Get German month name"""
        months = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        return months[month]
    
    def _change_month(self, delta):
        """Change displayed month"""
        # Debounce handled by DebouncedButton
        
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
        """Update the big label showing selected date"""
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
            
            btn = DebouncedButton(
                text=str(day),
                font_size='18sp',
                background_color=bg_color,
                color=text_color
            )
            btn.bind(on_release=lambda instance, d=day: self._select_day(d))
            self.days_grid.add_widget(btn)
            self.day_buttons.append(btn)
        
        # Fill remaining cells to complete grid (6 rows * 7 columns = 42 cells max usually enough)
        # But GridLayout will just fill. We just want it to look neat.
        # If we want consistent cell sizes, we might need to fill up to 42 (6 rows)
        total_cells = first_weekday + days_in_month
        rows_needed = (total_cells + 6) // 7
        total_slots = rows_needed * 7
        
        for _ in range(total_slots - total_cells):
            self.days_grid.add_widget(Widget())
    
    def _select_day(self, day):
        """Select a day"""
        # Debounce handled by DebouncedButton
        self.selected_day = day
        self._update_selected_label()
        
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
        # Debounce handled by DebouncedButton
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
    idle_seconds = 0
    MAX_IDLE_SECONDS = 60 # Start screensaver after 60 seconds

    def build(self):
        # Initialize database and RFID before returning root (which is auto-loaded from KV file)
        initialize_db()
        self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False) # Attempt real, fallback to mock
        self.rfid.start()
        self._recent_scan_times = {}
        
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
        self.root.current = 'register'
        self.root.get_screen('register').ids.admin_checkbox.active = True
        self.root.get_screen('register').ids.admin_checkbox.disabled = True # Force admin for first user
        self.show_popup("Welcome", "Please register the initial Administrator.")

    def on_rfid_scan(self, tag_id):
        # Schedule handling on main thread
        Clock.schedule_once(lambda dt: self.handle_scan(tag_id), 0)

    def handle_scan(self, tag_id):
        # Reset Idle Timer on every scan
        self.reset_idle_timer()
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

        # If Admin Tag
        if existing_employee.is_admin:
            if current_screen != 'admin':
                self.root.current = 'admin'
            return

        # If Normal Employee
        if current_screen == 'timeclock':
            self.perform_clock_action(existing_employee)
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
            
            # Show Greeter Popup
            self.show_greeter(employee, action)
            
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
        close_btn = DebouncedButton(
            text="Schließen",
            size_hint_y=None,
            height='50dp',
            background_color=(0.3, 0.6, 0.9, 1),
            onclick=lambda: self._reset_clocked_employee_timer()
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title=f"Tagesbericht - {employee.name}",
            content=content,
            size_hint=(0.95, 0.95),
            auto_dismiss=True
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _reset_clocked_employee_timer(self):
        """Reset timer that clears last_clocked_employee after inactivity"""
        if hasattr(self, '_employee_timeout_event') and self._employee_timeout_event:
            self._employee_timeout_event.cancel()
        self._employee_timeout_event = Clock.schedule_once(lambda dt: self._clear_last_clocked_employee(), 120)

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

    def show_greeter(self, employee, action):
        """Show a friendly greeting popup"""
        GreeterPopup(employee, action).open()

if __name__ == '__main__':
    TimeClockApp().run()
