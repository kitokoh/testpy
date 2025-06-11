import kivy
kivy.require('2.0.0') # Or a version available in the environment

from kivy.app import App
# BoxLayout and Label are already imported, Spinner is new
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

# Removed data_handler import from here as it's used in ui.py now
# from . import data_handler as mobile_data_api

from .ui import DocumentGenerationScreen # Import the screen from ui.py

class MobileApp(App):
    def build(self):
        # Using ScreenManager to allow for future screen additions
        sm = ScreenManager()
        # The actual screen content will be built out in other plan steps
        # For now, we just add a placeholder screen to the manager
        doc_gen_screen = DocumentGenerationScreen(name='doc_gen')
        sm.add_widget(doc_gen_screen)
        sm.current = 'doc_gen' # Set the current screen
        return sm

if __name__ == '__main__':
    MobileApp().run()
print("Mobile App Main Entry Point")
