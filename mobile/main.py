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

from . import data_handler as mobile_data_api

# Placeholder for the main screen UI that will be developed in ui.py
class DocumentGenerationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.languages_data = []
        self.countries_data = []
        self.products_data = []

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Language Selection
        lang_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        lang_layout.add_widget(Label(text='Language:', size_hint_x=0.3))
        self.language_spinner = Spinner(text='Select Language', values=(), size_hint_x=0.7)
        self.language_spinner.bind(text=self.on_language_select) # Callback for later
        lang_layout.add_widget(self.language_spinner)
        main_layout.add_widget(lang_layout)

        # Country Selection
        country_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        country_layout.add_widget(Label(text='Country:', size_hint_x=0.3))
        self.country_spinner = Spinner(text='Select Country', values=(), size_hint_x=0.7)
        self.country_spinner.bind(text=self.on_country_select) # Callback for later
        country_layout.add_widget(self.country_spinner)
        main_layout.add_widget(country_layout)

        # Product List (ScrollView + GridLayout)
        product_area_label = Label(text="Available Products:", size_hint_y=None, height='30dp')
        main_layout.add_widget(product_area_label)

        self.product_scroll_view = ScrollView(size_hint=(1, 1)) # Fill remaining space
        self.product_list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.product_list_layout.bind(minimum_height=self.product_list_layout.setter('height')) # Make GL expand with content

        self.product_scroll_view.add_widget(self.product_list_layout)
        main_layout.add_widget(self.product_scroll_view)

        # Add a spacer to push content to the top, or let other content fill the space
        # main_layout.add_widget(BoxLayout()) # Spacer

        self.add_widget(main_layout)
        self.populate_spinners()
        self.populate_product_list()

    def populate_spinners(self):
        self.languages_data = mobile_data_api.get_languages_from_api()
        language_names = [lang['name'] for lang in self.languages_data if lang and 'name' in lang]
        self.language_spinner.values = language_names
        if language_names:
            self.language_spinner.text = language_names[0]

        self.countries_data = mobile_data_api.get_all_countries_from_api()
        country_names = [country['country_name'] for country in self.countries_data if country and 'country_name' in country]
        self.country_spinner.values = country_names
        if country_names:
            self.country_spinner.text = country_names[0]

    def on_language_select(self, spinner, text):
        selected_lang_data = next((lang for lang in self.languages_data if lang['name'] == text), None)
        if selected_lang_data:
            print(f"Selected Language: {selected_lang_data['name']}, Code: {selected_lang_data['code']}")
        else:
            print(f"Selected Language Text: {text} (No full data found)")
        self.populate_product_list() # Refresh product list

    def populate_product_list(self):
        self.product_list_layout.clear_widgets()

        selected_language_code = 'en' # Default
        if hasattr(self, 'languages_data') and self.languages_data:
            selected_lang_name = self.language_spinner.text
            lang_data = next((lang for lang in self.languages_data if lang['name'] == selected_lang_name), None)
            if lang_data:
                selected_language_code = lang_data['code']
            elif self.languages_data: # Fallback to first language if current spinner text is not found
                # Check if default spinner text is "Select Language" or similar before using first in list
                if self.language_spinner.text != 'Select Language' and self.languages_data[0] and 'code' in self.languages_data[0]:
                     selected_language_code = self.languages_data[0]['code']


        self.products_data = mobile_data_api.get_all_products_for_selection_from_api(language_code=selected_language_code, name_pattern=None)

        if self.products_data:
            for product in self.products_data:
                product_label = Label(text=f"{product.get('product_name', 'N/A')} - Price: {product.get('price', 'N/A')}", size_hint_y=None, height='40dp')
                self.product_list_layout.add_widget(product_label)
        else:
            self.product_list_layout.add_widget(Label(text="No products found for selected language.", size_hint_y=None, height='40dp'))


    def on_country_select(self, spinner, text):
        selected_country_data = next((country for country in self.countries_data if country['country_name'] == text), None)
        if selected_country_data:
            print(f"Selected Country: {selected_country_data['country_name']}, ID: {selected_country_data['country_id']}")
        else:
            print(f"Selected Country Text: {text} (No full data found)")

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
