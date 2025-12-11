from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty
import random
import datetime

class MatrixRain(FloatLayout):
    """
    A simplified Matrix Rain effect using Labels for columns.
    Optimized for lower CPU usage (low FPS, shared structures).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = 20
        # Assume fixed landscape 800x480 approx for kiosk, or dynamic
        self.cols_count = int(Window.width / self.font_size)
        self.rows_count = int(Window.height / self.font_size) + 1
        self.columns = []
        self.chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Create labels for each column
        for i in random.sample(range(self.cols_count), self.cols_count):
            lbl = Label(
                text='',
                font_size=f'{self.font_size}sp',
                # font_name='RobotoMono-Regular', # Use default for now, assumes monospace-ish
                color=(0, 1, 0, 0.7),
                size_hint=(None, 1),
                width=self.font_size,
                pos_hint={'x': float(i) / self.cols_count, 'y': 0},
                halign='center',
                valign='top'
            )
            # Pre-fill structure
            self.columns.append({
                'label': lbl,
                'data': [' '] * self.rows_count,
                'active_length': 0,
                'speed': random.randint(1, 4),
                'tick': 0
            })
            self.add_widget(lbl)
            
        self._update_event = None

    def start_animation(self):
        if not self._update_event:
            # 15 FPS is enough for screensaver and saves power
            self._update_event = Clock.schedule_interval(self.update, 1.0 / 15)

    def stop_animation(self):
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def update(self, dt):
        for col in self.columns:
            col['tick'] += 1
            if col['tick'] < col['speed']:
                continue
            col['tick'] = 0
            
            # Shift down
            col['data'].pop() # Remove last
            
            # Determine new character
            # If active_length > 0, we are in a stream
            if col['active_length'] > 0:
                col['active_length'] -= 1
                new_char = random.choice(self.chars)
            else:
                new_char = ' '
                # Chance to start new stream
                if random.random() < 0.02: # 2% chance per update
                    col['active_length'] = random.randint(5, self.rows_count)
            
            col['data'].insert(0, new_char)
            
            # Update label text (join is relatively fast for small lists)
            # Only update if visible change (optimization?) - no, always changing
            col['label'].text = '\n'.join(col['data'])

class ScreensaverScreen(Screen):
    time_str = StringProperty("00:00")
    date_str = StringProperty("Mon, 01 Jan")
    
    def on_enter(self):
        # Start Matrix Rain
        if hasattr(self.ids, 'matrix_bg'):
            self.ids.matrix_bg.start_animation()
        
        # Start Clock update
        self.update_time()
        self._clock_event = Clock.schedule_interval(self.update_time, 1)
        
    def on_leave(self):
        if hasattr(self.ids, 'matrix_bg'):
            self.ids.matrix_bg.stop_animation()
        if hasattr(self, '_clock_event'):
            self._clock_event.cancel()

    def update_time(self, *args):
        now = datetime.datetime.now()
        self.time_str = now.strftime("%H:%M")
        self.date_str = now.strftime("%A, %d. %B %Y")

