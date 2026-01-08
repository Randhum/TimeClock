"""
Greeter popup for welcoming employees on clock in/out.
"""
import os
import time
import random
import datetime
import logging
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock

logger = logging.getLogger(__name__)


class GreeterPopup(Popup):
    """Popup that displays friendly greeting messages"""
    
    greeting = StringProperty("")
    message = StringProperty("")
    color_theme = ObjectProperty((0, 1, 0, 1))  # Green for IN, Orange for OUT
    
    # Available languages: 'ch' (Schweizerdeutsch), 'de' (Deutsch), 'it' (Italienisch), 'rm' (Rätoromanisch)
    AVAILABLE_LANGUAGES = ['ch', 'de', 'it', 'rm']
    
    def __init__(self, employee, action, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.separator_height = 0
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = True
        
        name = employee.name.split()[0]  # First name
        
        # Determine shift based on current time
        shift = self._get_shift()
        
        # Select language based on entropy (tag_id, time, employee_id, cpu_temp)
        language = self._select_language(employee)
        
        # Build filename based on action, shift, and language
        filename = self._get_greeting_filename(action, shift, language)
        
        if action == 'in':
            self.greeting = f"Hallo, {name}!"
            self.message = self._get_random_message(filename, "Gute Schicht!", name)
            self.color_theme = (0.2, 0.8, 0.2, 1)  # Green
        else:
            self.greeting = f"Tschüss, {name}!"
            self.message = self._get_random_message(filename, "Schönen Feierabend!", name)
            self.color_theme = (1, 0.6, 0, 1)  # Orange
            
        Clock.schedule_once(self.dismiss, 8)

    def _get_shift(self):
        """Determine current shift based on time of day"""
        now = datetime.datetime.now()
        hour = now.hour
        
        # Morning shift: 04:00 - 11:00
        if 4 <= hour < 11:
            return 'morning'
        # Midday shift: 11:00 - 17:00 (overlaps with morning)
        elif 11 <= hour < 17:
            return 'midday'
        # Evening shift: 17:00 - 04:00
        elif hour >= 17 or hour < 4:
            return 'evening'
        # Default to midday for early hours (0-4)
        else:
            return 'midday'
    
    def _select_language(self, employee):
        """Select language randomly based on entropy from tag_id, time, employee_id, and cpu_temp"""
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
            logger.warning(f"Error selecting language, using default 'rm': {e}")
            return 'rm'  # Default fallback
    
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
        # Get path relative to src directory
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base_path, 'data', 'greetings', f'greetings_{action_part}_{shift}_{language}.txt')

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
                        # Convert literal \n strings to actual newlines
                        message = message.replace('\\n', '\n')
                        return message
        except Exception as e:
            logger.warning(f"Error loading greeting from {filename}: {e}")
        
        # Fallback to general greeting files if specific shift file not found
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        fallback_file = os.path.join(base_path, 'data', 'greetings', 'greetings_in.txt' if 'in' in filename else 'greetings_out.txt')
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
                        # Convert literal \n strings to actual newlines
                        message = message.replace('\\n', '\n')
                        return message
        except Exception as e:
            logger.warning(f"Error loading fallback greeting from {fallback_file}: {e}")
        
        # Replace [Name] in default message too
        return default_msg.replace('[Name]', employee_name) if '[Name]' in default_msg else default_msg

