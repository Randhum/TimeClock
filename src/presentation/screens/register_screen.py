"""
Register screen for registering new employees.
"""
import logging
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.app import App
from peewee import IntegrityError

from src.database import get_admin_count, create_employee

logger = logging.getLogger(__name__)


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

