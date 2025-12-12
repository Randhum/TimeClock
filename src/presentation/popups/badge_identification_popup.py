"""
Badge identification popup for employee authentication.
"""
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.app import App

from ..widgets.debounced_button import DebouncedButton


class BadgeIdentificationPopup(Popup):
    """Popup that prompts user to scan their badge for identification"""
    
    def __init__(self, action_type, on_identified=None, **kwargs):
        """
        Args:
            action_type: 'view_report' or 'edit_sessions'
            on_identified: Callback(employee) called when badge is identified
        """
        super().__init__(
            title="Identifikation erforderlich",
            size_hint=(0.8, 0.5),
            auto_dismiss=False,
            **kwargs
        )
        self.action_type = action_type
        self.on_identified = on_identified
        self.identified_employee = None
        
        # Build UI
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)
        
        # Message based on action type
        if action_type == 'view_report':
            message = "Bitte scannen Sie Ihr Badge,\num Ihren Tagesbericht anzuzeigen."
        else:  # edit_sessions
            message = "Bitte scannen Sie Ihr Badge,\num Ihre Einträge zu bearbeiten."
        
        label = Label(
            text=message,
            font_size='28sp',
            halign='center',
            valign='middle',
            text_size=(None, None),
            size_hint_y=None,
            height='120dp'
        )
        layout.add_widget(label)
        
        # Status label
        self.status_label = Label(
            text="Warte auf Badge-Scan...",
            font_size='24sp',
            halign='center',
            color=(1, 1, 0.5, 1),  # Yellow
            size_hint_y=None,
            height='60dp'
        )
        layout.add_widget(self.status_label)
        
        # Cancel button
        cancel_btn = DebouncedButton(
            text="Abbrechen",
            size_hint_y=None,
            height='60dp',
            background_color=(0.7, 0.2, 0.2, 1)
        )
        cancel_btn.bind(on_release=self._on_cancel)
        layout.add_widget(cancel_btn)
        
        self.content = layout
    
    def _on_cancel(self, *args):
        """Handle cancel button - clear pending identification"""
        app = App.get_running_app()
        if app and hasattr(app, 'state_service'):
            app.state_service.clear_pending_identification()
        self.dismiss()
    
    def on_employee_identified(self, employee):
        """Called when an employee is identified via badge scan"""
        self.identified_employee = employee
        self.status_label.text = f"Identifiziert: {employee.name}"
        self.status_label.color = (0.2, 1, 0.2, 1)  # Green
        
        # Call callback after brief delay
        if self.on_identified:
            Clock.schedule_once(lambda dt: self._execute_callback(), 0.5)
    
    def _execute_callback(self):
        """Execute the identification callback and close popup"""
        if self.identified_employee and self.on_identified:
            self.on_identified(self.identified_employee)
        self.dismiss()

