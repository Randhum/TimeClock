"""
Add entry popup for manually adding time entries.
"""
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.app import App

from ..widgets import DebouncedButton
from .limited_date_picker_popup import LimitedDatePickerPopup
from .time_picker_popup import TimePickerPopup
from ...data.database import TimeEntry, ensure_db_connection

logger = logging.getLogger(__name__)


class AddEntryPopup(Popup):
    def __init__(self, employee, on_save=None, initial_date=None, **kwargs):
        super().__init__(
            title=f"Manuellen Eintrag hinzufügen - {employee.name}",
            size_hint=(0.9, 0.7),
            auto_dismiss=False,
            **kwargs
        )
        self.employee = employee
        self.on_save_callback = on_save
        now = datetime.datetime.now()
        # Use initial_date if provided, otherwise use today
        self.selected_date = initial_date if initial_date else now.date()
        self.selected_time = now.time().replace(second=0, microsecond=0)
        # Action will be auto-determined based on last entry before timestamp
        self.selected_action = None

        # Main container with ScrollView
        main_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        
        # Scrollable content area
        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=10
        )
        
        # Inner layout for scrollable content
        layout = BoxLayout(
            orientation='vertical',
            spacing=15,
            padding=20,
            size_hint_y=None,
            height=0  # Will be set by minimum_height
        )
        layout.bind(minimum_height=layout.setter('height'))
        
        # Date selection
        self.date_btn = DebouncedButton(
            text=f"Datum: {self.selected_date.strftime('%d.%m.%Y')}",
            size_hint_y=None,
            height='70dp',
            font_size='24sp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.date_btn.bind(on_release=lambda *_: self._pick_date())
        layout.add_widget(self.date_btn)

        # Time selection
        self.time_btn = DebouncedButton(
            text=f"Zeit: {self.selected_time.strftime('%H:%M')}",
            size_hint_y=None,
            height='70dp',
            font_size='24sp',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        self.time_btn.bind(on_release=lambda *_: self._pick_time())
        layout.add_widget(self.time_btn)

        # Action display (auto-determined, read-only)
        self.action_label = Label(
            text="Action: Will be determined automatically",
            size_hint_y=None,
            height='70dp',
            font_size='20sp',
            halign='center',
            valign='middle',
            text_size=(None, None)
        )
        layout.add_widget(self.action_label)
        self._update_action_display()

        # Add layout to scroll view
        scroll.add_widget(layout)
        main_layout.add_widget(scroll)

        # Buttons row (fixed at bottom, outside scroll)
        btn_row = BoxLayout(
            orientation='horizontal',
            spacing=15,
            size_hint_y=None,
            height='70dp',
            padding=(20, 10, 20, 10)
        )
        save_btn = DebouncedButton(
            text="Speichern",
            size_hint_x=0.5,
            font_size='24sp',
            background_color=(0, 0.7, 0, 1)
        )
        cancel_btn = DebouncedButton(
            text="Abbrechen",
            size_hint_x=0.5,
            font_size='24sp',
            background_color=(0.7, 0.2, 0.2, 1)
        )
        save_btn.bind(on_release=lambda *_: self._save())
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        main_layout.add_widget(btn_row)

        self.content = main_layout

    def _pick_date(self):
        """Open date picker, limiting to past 7 days for manual entries"""
        today = datetime.date.today()
        min_date = today - datetime.timedelta(days=7)
        
        LimitedDatePickerPopup(
            current_date=self.selected_date,
            min_date=min_date,
            max_date=today,
            on_select=self._set_date
        ).open()

    def _pick_time(self):
        # Store reference to prevent garbage collection before callback executes
        self._time_picker = TimePickerPopup(
            current_time=self.selected_time,
            on_select=self._set_time
        )
        self._time_picker.open()

    def _set_date(self, date_obj):
        self.selected_date = date_obj
        self.date_btn.text = f"Datum: {self.selected_date.strftime('%d.%m.%Y')}"
        self._update_action_display()

    def _set_time(self, time_obj):
        self.selected_time = time_obj
        self.time_btn.text = f"Zeit: {self.selected_time.strftime('%H:%M')}"
        self._update_action_display()

    def _update_action_display(self):
        """Auto-determine action based on last entry before selected timestamp"""
        try:
            ensure_db_connection()
            timestamp = datetime.datetime.combine(self.selected_date, self.selected_time)
            last_entry = TimeEntry.get_last_before_timestamp(self.employee, timestamp)
            
            # Determine action: if no entry or last was 'out', next is 'in'; otherwise 'out'
            if not last_entry or last_entry.action == 'out':
                self.selected_action = 'in'
            else:
                self.selected_action = 'out'
            
            # Update display
            action_text = "IN" if self.selected_action == 'in' else "OUT"
            action_color = (0.2, 0.8, 0.2, 1) if self.selected_action == 'in' else (0.8, 0.2, 0.2, 1)
            self.action_label.text = f"Action: {action_text} (auto-determined)"
            self.action_label.color = action_color
        except Exception as e:
            logger.error(f"[ADD_ENTRY] Error determining action: {e}")
            self.selected_action = 'in'  # Default fallback
            self.action_label.text = "Action: IN (default)"
            self.action_label.color = (0.2, 0.8, 0.2, 1)

    def _save(self):
        # Prevent double-save (belt and suspenders with DebouncedButton fix)
        if getattr(self, '_saving', False):
            return
        self._saving = True
        
        try:
            if self.selected_action is None:
                # Ensure action is determined before saving
                self._update_action_display()
            
            ts = datetime.datetime.combine(self.selected_date, self.selected_time)
            if self.on_save_callback:
                self.on_save_callback(self.selected_action, ts)
            self.dismiss()
        except Exception as e:
            logger.error(f"[ADD_ENTRY] Error combining date/time: {e}")
            App.get_running_app().show_popup("Error", f"Ungültiges Datum/Zeit: {str(e)}")
        finally:
            self._saving = False

