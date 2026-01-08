"""
Entry editor popup for viewing and editing time entries.
"""
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.app import App
from kivy.clock import Clock

from ..widgets import DebouncedButton
from .limited_date_picker_popup import LimitedDatePickerPopup
from .add_entry_popup import AddEntryPopup
from ...data.database import TimeEntry, db, ensure_db_connection, soft_delete_time_entries

logger = logging.getLogger(__name__)


class EntryEditorPopup(Popup):
    def __init__(self, employee, on_deleted=None, **kwargs):
        super().__init__(
            title=f"Edit {employee.name} - Entries",
            size_hint=(0.95, 0.95),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        self.on_deleted = on_deleted
        self.entries = []
        # Default to today, but allow selection of past 7 days
        self.selected_date = datetime.date.today()
        
        # Register with popup service for proper management
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service.close_main_popup()  # Close any existing main popup
            app.popup_service._register_popup(self, is_main=True)
        
        # Don't recalculate on open - only recalculate when entries are modified
        # This prevents actions from being incorrectly changed when just viewing entries
        # Recalculation happens automatically when entries are added or deleted
        self._load_entries_for_date()
        self._build_ui()
        
        # Ensure proper cleanup on dismiss
        self.bind(on_dismiss=self._on_dismiss)
    
    def _on_dismiss(self, instance):
        """Cleanup when popup is dismissed"""
        app = App.get_running_app()
        if app and hasattr(app, 'popup_service'):
            app.popup_service._unregister_popup(self)
    
    def _load_entries_for_date(self):
        """Load all time entries for the selected date (fresh from database)"""
        ensure_db_connection()
        start_datetime = datetime.datetime.combine(self.selected_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(self.selected_date, datetime.time.max)
        
        # Query fresh from database to ensure we have the latest action values
        self.entries = list(TimeEntry.select().where(
            TimeEntry.employee == self.employee,
            TimeEntry.active == True,
            TimeEntry.timestamp >= start_datetime,
            TimeEntry.timestamp <= end_datetime
        ).order_by(TimeEntry.timestamp.asc()))
        
        logger.debug(f"[ENTRY_EDITOR] Loaded {len(self.entries)} entries for {self.selected_date}")
    
    def _build_ui(self):
        """Build the UI with all entries"""
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
        
        # Add Manual Entry button
        add_btn = DebouncedButton(
            text="Add Entry",
            size_hint_x=0.4,
            font_size='20sp',
            background_color=(0.2, 0.7, 1, 1)
        )
        add_btn.bind(on_release=lambda *_: self._open_add_entry())
        header_row.add_widget(add_btn)
        
        layout.add_widget(header_row)
        
        # Notice
        notice = Label(
            text="Tap 'Delete' to remove an entry. Actions are automatically determined.",
            size_hint_y=None,
            height='35dp',
            font_size='14sp'
        )
        layout.add_widget(notice)
        
        # Scrollable list of entries
        scroll = ScrollView(do_scroll_x=False)
        grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        # Store references for rebuilding
        self.entries_scroll = scroll
        self.entries_grid = grid
        
        self._populate_entries_grid()
        
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
        
        # Ensure we're reading the actual database value (refresh if needed)
        # Reload the entry from database to ensure we have the latest action value
        try:
            fresh_entry = TimeEntry.get_by_id(entry.id)
            entry.action = fresh_entry.action
        except TimeEntry.DoesNotExist:
            logger.warning(f"[ENTRY_EDITOR] Entry ID={entry.id} no longer exists")
        
        # Timestamp and action label - display the actual database value
        action_color = (0.2, 0.8, 0.2, 1) if entry.action == 'in' else (0.8, 0.2, 0.2, 1)
        action_text = "IN" if entry.action == 'in' else "OUT"
        logger.debug(f"[ENTRY_EDITOR] Displaying entry ID={entry.id}: {entry.timestamp} - {entry.action.upper()}")
        
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
            
            # Recalculate all actions for all active entries before reloading
            self._recalculate_all_actions()
            
            # Reload entries
            self._load_entries_for_date()
            # Rebuild UI to reflect changes
            self._rebuild_entries_list()
            
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

    def _populate_entries_grid(self):
        """Populate the entries grid with current entries"""
        self.entries_grid.clear_widgets()
        if not self.entries:
            date_str = "today" if self.selected_date == datetime.date.today() else self.selected_date.strftime('%d.%m.%Y')
            no_entries = Label(
                text=f"No entries found for {date_str}.",
                size_hint_y=None,
                height='40dp'
            )
            self.entries_grid.add_widget(no_entries)
        else:
            for entry in self.entries:
                row = self._create_entry_row(entry)
                self.entries_grid.add_widget(row)
    
    def _rebuild_entries_list(self):
        """Rebuild the entries list after changes"""
        self._populate_entries_grid()
    
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
        """Update selected date and reload entries"""
        if date_obj != self.selected_date:
            self.selected_date = date_obj
            self.date_btn.text = f"Datum: {self.selected_date.strftime('%d.%m.%Y')}"
            self._load_entries_for_date()
            self._rebuild_entries_list()
    
    def _open_add_entry(self):
        """Open popup to add a manual entry"""
        # Pre-select the date in the add entry popup
        AddEntryPopup(
            employee=self.employee,
            initial_date=self.selected_date,
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
            
            # Recalculate all actions for all active entries before reloading
            self._recalculate_all_actions()
            
            # Reload entries and inform user
            self._load_entries_for_date()
            # Rebuild UI to show new entry
            self._rebuild_entries_list()
            app = App.get_running_app()
            app.show_popup("Erfolg", f"Manueller Eintrag ({action.upper()}) gespeichert.")
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error adding manual entry: {e}")
            App.get_running_app().show_popup("Error", f"Fehler beim Hinzufügen: {str(e)}")
    
    def _after_delete_cleanup(self, app):
        """Called after popup is dismissed to show success and navigate"""
        app.show_popup("Erfolg", "Eintrag erfolgreich gelöscht")
        app.root.current = "timeclock"
    
    def _recalculate_all_actions(self):
        """
        Recalculate actions for all active entries for this employee in chronological order.
        This ensures proper IN/OUT alternation regardless of edits/deletions.
        """
        try:
            ensure_db_connection()
            
            # Get all active entries for this employee, ordered chronologically
            all_entries = list(TimeEntry.select().where(
                TimeEntry.employee == self.employee,
                TimeEntry.active == True
            ).order_by(TimeEntry.timestamp.asc()))
            
            if not all_entries:
                return
            
            # First, calculate all expected actions in memory (based on chronological order)
            # This ensures we use the correct logic, not stale database values
            expected_actions = []
            for i in range(len(all_entries)):
                if i == 0:
                    # First entry should always be 'in'
                    expected_actions.append('in')
                else:
                    # Alternate based on previous expected action (not the database value!)
                    prev_expected = expected_actions[i-1]
                    expected_actions.append('out' if prev_expected == 'in' else 'in')
            
            # Now update all entries that need changes
            updates_made = 0
            with db.atomic():
                for entry, expected_action in zip(all_entries, expected_actions):
                    # Update if action is incorrect
                    if entry.action != expected_action:
                        TimeEntry.update(action=expected_action).where(TimeEntry.id == entry.id).execute()
                        logger.debug(f"[ENTRY_EDITOR] Updated entry ID={entry.id} action from {entry.action} to {expected_action}")
                        updates_made += 1
                        # Update the entry object in memory so subsequent reads are correct
                        entry.action = expected_action
            
            if updates_made > 0:
                logger.info(f"[ENTRY_EDITOR] Recalculated actions for {len(all_entries)} entries ({updates_made} updated)")
            else:
                logger.debug(f"[ENTRY_EDITOR] Actions already correct for {len(all_entries)} entries")
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error recalculating actions: {e}")

