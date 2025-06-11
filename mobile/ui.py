import kivy # Good practice to have the base kivy import

# Kivy imports identified for DocumentGenerationScreen
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

# Data handler import
from . import data_handler as mobile_data_api

class DocumentGenerationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.languages_data = []
        self.countries_data = []
        self.products_data = []
        self.selected_products_for_document = []
        self.currently_selected_available_product = None

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

        # Quantity Input and Add Button
        add_product_controls_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)

        add_product_controls_layout.add_widget(Label(text='Quantity:', size_hint_x=0.2))
        self.quantity_input = TextInput(text='1', multiline=False, input_filter='int', size_hint_x=0.2)
        add_product_controls_layout.add_widget(self.quantity_input)

        self.add_to_document_button = Button(text='Add to Document', size_hint_x=0.6)
        self.add_to_document_button.bind(on_press=self.on_add_to_document_button_pressed)
        add_product_controls_layout.add_widget(self.add_to_document_button)

        main_layout.add_widget(add_product_controls_layout)

        # Product List (ScrollView + GridLayout)
        product_area_label = Label(text="Available Products:", size_hint_y=None, height='30dp')
        main_layout.add_widget(product_area_label)

        self.product_scroll_view = ScrollView(size_hint_y=0.4) # Adjusted size_hint_y to make space for controls
        self.product_list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.product_list_layout.bind(minimum_height=self.product_list_layout.setter('height')) # Make GL expand with content

        self.product_scroll_view.add_widget(self.product_list_layout)
        main_layout.add_widget(self.product_scroll_view)

        # Selected Products Area
        selected_products_area_label = Label(text="Selected Products for Document:", size_hint_y=None, height='30dp')
        main_layout.add_widget(selected_products_area_label)

        self.selected_products_scroll_view = ScrollView(size_hint_y=0.3) # Adjusted size_hint_y
        self.selected_products_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.selected_products_layout.bind(minimum_height=self.selected_products_layout.setter('height'))

        self.selected_products_scroll_view.add_widget(self.selected_products_layout)
        main_layout.add_widget(self.selected_products_scroll_view)

        # Add a spacer to push content to the top, or let other content fill the space
        # main_layout.add_widget(BoxLayout()) # Spacer

        self.add_widget(main_layout)
        self.populate_spinners()
        self.populate_product_list()
        self.refresh_selected_products_display() # Initial call

    def refresh_selected_products_display(self):
        self.selected_products_layout.clear_widgets() # Clear previous entries

        if not self.selected_products_for_document:
            self.selected_products_layout.add_widget(
                Label(text="No products added yet.", size_hint_y=None, height='40dp')
            )
            return

        for i, selected_item in enumerate(self.selected_products_for_document):
            item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=5)

            product_name = selected_item['original_data'].get('product_name', 'N/A')
            quantity = selected_item['quantity']
            item_label_text = f"{product_name} (Qty: {quantity})"
            item_label = Label(text=item_label_text, size_hint_x=0.7)
            item_layout.add_widget(item_label)

            remove_button = Button(text='Remove', size_hint_x=0.3)
            # Store a reference to the item or its index for removal
            remove_button.product_to_remove_data = selected_item
            # Alternatively, store the index: remove_button.product_index_to_remove = i
            remove_button.bind(on_press=self.on_remove_selected_product)
            item_layout.add_widget(remove_button)

            self.selected_products_layout.add_widget(item_layout)

    def on_remove_selected_product(self, button_instance):
        product_to_remove = button_instance.product_to_remove_data

        if product_to_remove in self.selected_products_for_document:
            self.selected_products_for_document.remove(product_to_remove)
            product_name = product_to_remove['original_data'].get('product_name', 'N/A')
            print(f"Removed '{product_name}' from document list.")
            self.refresh_selected_products_display() # Refresh the display
        else:
            print("Error: Could not find the product to remove in the list.")

    def on_add_to_document_button_pressed(self, instance):
        if not self.currently_selected_available_product:
            print("No product selected from the available list to add.")
            # Optionally, show a popup or label message to the user
            return

        try:
            quantity = int(self.quantity_input.text)
            if quantity <= 0:
                raise ValueError("Quantity must be positive.")
        except ValueError:
            print("Invalid quantity. Defaulting to 1.")
            quantity = 1
            self.quantity_input.text = '1' # Reset UI

        product_to_add = {
            'original_data': self.currently_selected_available_product, # Contains name, price, id etc.
            'quantity': quantity
        }

        self.selected_products_for_document.append(product_to_add)

        product_name = self.currently_selected_available_product.get('product_name', 'N/A')
        print(f"Added '{product_name}' (Qty: {quantity}) to document list.")

        # Call refresh for the selected products display (will be fully built in next step)
        if hasattr(self, 'refresh_selected_products_display'):
            self.refresh_selected_products_display()
        else:
            print("DEBUG: refresh_selected_products_display method not yet implemented.")

        # Optional: Reset selection
        self.currently_selected_available_product = None
        # You might also want to visually de-highlight the product in the available list here.
        self.quantity_input.text = '1'

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
                product_entry = Button(
                    text=f"{product.get('product_name', 'N/A')} - Price: {product.get('price', 'N/A')}",
                    size_hint_y=None,
                    height='48dp'
                )
                product_entry.product_data = product
                product_entry.bind(on_press=self.on_available_product_tapped)
                self.product_list_layout.add_widget(product_entry)
        else:
            self.product_list_layout.add_widget(Label(text="No products found for selected language.", size_hint_y=None, height='40dp'))

    def on_available_product_tapped(self, button_instance):
        product_data = button_instance.product_data
        print(f"Tapped on available product: {product_data.get('product_name', 'N/A')}")
        # Store this for potential use by an "Add" button, for example
        self.currently_selected_available_product = product_data
        # Optionally, you could change the button's appearance here to show it's "selected"
        # For example, button_instance.background_color = (0.5, 0.5, 1, 1) # Highlight color
        # You'd also need to manage de-highlighting other buttons.

    def on_country_select(self, spinner, text):
        selected_country_data = next((country for country in self.countries_data if country['country_name'] == text), None)
        if selected_country_data:
            print(f"Selected Country: {selected_country_data['country_name']}, ID: {selected_country_data['country_id']}")
        else:
            print(f"Selected Country Text: {text} (No full data found)")

# Note: The conceptual UI stubs previously in this file (MainScreen, SettingsScreen, MobileAppController, SelectedProduct)
# have been overwritten by the Kivy-specific DocumentGenerationScreen.
# Further refactoring would be needed to integrate them with a Kivy architecture if they were to be developed.
# For this task, ui.py now primarily holds the DocumentGenerationScreen Kivy widget.
