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
        """Delete a single entry and update subsequent actions with proper transaction handling and employee-level locking"""
        from ...data.database import _get_employee_lock
        
        logger.debug(f"[ENTRY_EDITOR] Deleting entry ID={entry.id}, action={entry.action}, time={entry.timestamp}")
        
        # Acquire employee-specific lock to prevent concurrent modifications
        employee_lock = _get_employee_lock(self.employee.id)
        
        with employee_lock:
            try:
                ensure_db_connection()
                
                # Perform delete and recalculation in separate transactions for safety
                # First: Soft delete the entry
                with db.atomic():
            soft_delete_time_entries([entry.id])
            logger.info(f"[ENTRY_EDITOR] Deleted entry ID={entry.id}")
            
                # Second: Recalculate all actions for all active entries
                # This is in a separate transaction to ensure delete completes first
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
            
                # Close popup and schedule navigation after it's fully closed
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
        """Persist manual entry and refresh state with validation and employee-level locking"""
        from ...data.database import _get_employee_lock
        
        # Acquire employee-specific lock to prevent concurrent modifications
        employee_lock = _get_employee_lock(self.employee.id)
        
        with employee_lock:
        try:
            ensure_db_connection()
                
                # Re-validate action against current database state before saving
                # This prevents saving incorrect actions if database changed between UI determination and save
                last_entry = TimeEntry.get_last_before_timestamp(self.employee, timestamp)
                
                # Determine what action should be based on current database state
                if not last_entry or last_entry.action == 'out':
                    expected_action = 'in'
                else:
                    expected_action = 'out'
                
                # If provided action doesn't match expected, use expected action and log warning
                if action != expected_action:
                    logger.warning(f"[ENTRY_EDITOR] Action mismatch: provided '{action}', expected '{expected_action}' based on current DB state. Using expected action.")
                    action = expected_action
                
                # Validate timestamp is reasonable (not too far in future or past)
                now = datetime.datetime.now()
                max_future = now + datetime.timedelta(days=1)  # Allow 1 day in future for corrections
                min_past = now - datetime.timedelta(days=365)  # Allow 1 year in past
                
                if timestamp > max_future:
                    raise ValueError(f"Timestamp cannot be more than 1 day in the future. Got: {timestamp}")
                if timestamp < min_past:
                    raise ValueError(f"Timestamp cannot be more than 1 year in the past. Got: {timestamp}")
                
                # Validate action is valid
                if action not in ('in', 'out'):
                    raise ValueError(f"Invalid action: {action}. Must be 'in' or 'out'")
                
                # Validate employee is still active
                if not self.employee.active:
                    raise ValueError("Cannot create time entry for inactive employee")
                
                # Create entry within transaction
            with db.atomic():
                    entry = TimeEntry.create(
                    employee=self.employee,
                    timestamp=timestamp,
                    action=action,
                    active=True
                )
            logger.info(f"[ENTRY_EDITOR] Added manual entry {action} at {timestamp}")
            
            # Recalculate all actions for all active entries before reloading
                # This ensures any logical errors are fixed
            self._recalculate_all_actions()
            
            # Reload entries and inform user
            self._load_entries_for_date()
            # Rebuild UI to show new entry
            self._rebuild_entries_list()
            app = App.get_running_app()
            app.show_popup("Erfolg", f"Manueller Eintrag ({action.upper()}) gespeichert.")
            except ValueError as e:
                logger.error(f"[ENTRY_EDITOR] Validation error adding manual entry: {e}")
                App.get_running_app().show_popup("Error", f"Validierungsfehler: {str(e)}")
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
        Only fixes entries that are logically incorrect (e.g., two 'in' in a row, two 'out' in a row).
        Preserves existing actions when they form a valid IN/OUT alternation pattern.
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
            
            # Check if actions form a valid pattern (alternating in/out)
            # Only recalculate if there are logical errors (same action twice in a row)
            needs_recalculation = False
            for i in range(1, len(all_entries)):
                if all_entries[i].action == all_entries[i-1].action:
                    needs_recalculation = True
                    logger.debug(f"[ENTRY_EDITOR] Found consecutive {all_entries[i].action.upper()} actions, recalculation needed")
                    break
            
            # If actions already form a valid pattern, don't change them
            if not needs_recalculation:
                logger.debug(f"[ENTRY_EDITOR] Actions already form valid pattern for {len(all_entries)} entries, no recalculation needed")
                return
            
            # Calculate expected actions based on chronological order
            # Start with the first entry's action (preserve it if it's valid)
            # If first entry is 'out', that's valid (maybe they forgot to clock in), so preserve it
            expected_actions = []
            first_action = all_entries[0].action
            
            # If first entry is 'out', we'll start with 'out' and alternate from there
            # Otherwise start with 'in' and alternate
            if first_action == 'out':
                expected_actions.append('out')
                    else:
                expected_actions.append('in')
            
            # Alternate from the first action
            for i in range(1, len(all_entries)):
                prev_expected = expected_actions[i-1]
                expected_actions.append('out' if prev_expected == 'in' else 'in')
                    
            # Now update only entries that are logically incorrect
            updates_made = 0
            try:
                with db.atomic():
                    for entry, expected_action in zip(all_entries, expected_actions):
                        # Only update if action is different AND it creates a logical error
                    if entry.action != expected_action:
                            # Check if current action creates a problem with neighbors
                            entry_idx = all_entries.index(entry)
                            has_problem = False
                            
                            # Check previous entry
                            if entry_idx > 0:
                                prev_entry = all_entries[entry_idx - 1]
                                if entry.action == prev_entry.action:
                                    has_problem = True
                            
                            # Check next entry
                            if entry_idx < len(all_entries) - 1:
                                next_entry = all_entries[entry_idx + 1]
                                if entry.action == next_entry.action:
                                    has_problem = True
                            
                            # Only update if there's a logical problem
                            if has_problem:
                        TimeEntry.update(action=expected_action).where(TimeEntry.id == entry.id).execute()
                                logger.debug(f"[ENTRY_EDITOR] Fixed entry ID={entry.id} action from {entry.action} to {expected_action} (logical error)")
                                updates_made += 1
                                # Update the entry object in memory so subsequent reads are correct
                                entry.action = expected_action
                    db.commit()  # Explicit commit
                    
                if updates_made > 0:
                    logger.info(f"[ENTRY_EDITOR] Recalculated actions for {len(all_entries)} entries ({updates_made} fixed)")
                else:
                    logger.debug(f"[ENTRY_EDITOR] No action fixes needed for {len(all_entries)} entries")
            except Exception as e:
                logger.error(f"[ENTRY_EDITOR] Error updating actions in transaction: {e}")
                try:
                    db.rollback()
                except:
                    pass
                raise
        except Exception as e:
            logger.error(f"[ENTRY_EDITOR] Error recalculating actions: {e}")
            # Don't raise - allow operation to continue even if recalculation fails

