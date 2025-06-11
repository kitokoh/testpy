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
from kivy.uix.modalview import ModalView

import tempfile
import os # Useful for getting filename if needed, though tempfile handles it well
from kivy.uix.popup import Popup
# from kivy.uix.label import Label # Label is already imported
from kivy.uix.button import Button as PopupButton # To avoid conflict if Button is already aliased
from kivy.uix.boxlayout import BoxLayout as PopupBoxLayout # For popup layout
from kivy.utils import get_color_from_hex

try:
    from plyer import email as plyer_email
    PLYER_EMAIL_AVAILABLE = True
except ImportError:
    PLYER_EMAIL_AVAILABLE = False
    plyer_email = None # Placeholder
    print("Plyer 'email' module not found. Email functionality will be limited.")

try:
    from plyer import sharing as plyer_sharing
    PLYER_SHARING_AVAILABLE = True
except ImportError:
    PLYER_SHARING_AVAILABLE = False
    plyer_sharing = None # Placeholder
    print("Plyer 'sharing' module not found. File sharing/opening will be limited.")

# Data handler import
from . import data_handler as mobile_data_api
from mobile.document_handler import LiteDocumentHandler # Import for PDF generation


class DocumentGenerationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.languages_data = []
        self.countries_data = []
        self.products_data = []
        self.selected_products_for_document = []
        self.currently_selected_available_product = None
        self.templates_data = []
        self.current_selected_template = None
        self.current_pdf_action = 'separate' # Default PDF action
        self.last_pdf_outputs = None # To store the result from LiteDocumentHandler
        self.last_generated_pdf_paths = [] # For email attachments
        self.highlighted_product_button = None
        self.app_temporary_files = [] # Global list for all temp files

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

        # Template Selection
        template_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        template_layout.add_widget(Label(text='Template:', size_hint_x=0.3))
        self.template_spinner = Spinner(text='Select Template', values=(), size_hint_x=0.7)
        self.template_spinner.bind(text=self.on_template_select)
        template_layout.add_widget(self.template_spinner)
        main_layout.add_widget(template_layout)

        # PDF Output Action Selection
        pdf_action_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        pdf_action_layout.add_widget(Label(text='PDF Output:', size_hint_x=0.3))

        self.pdf_action_spinner_values = {
            "Separate PDFs": "separate",
            "Combine PDFs": "combine"
        }
        self.pdf_action_spinner = Spinner(
            text="Separate PDFs", # Default display text
            values=list(self.pdf_action_spinner_values.keys()),
            size_hint_x=0.7
        )
        self.pdf_action_spinner.bind(text=self.on_pdf_action_select)
        pdf_action_layout.add_widget(self.pdf_action_spinner)
        main_layout.add_widget(pdf_action_layout)

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
        self.populate_template_spinner() # Call new method
        self.populate_product_list()
        self.refresh_selected_products_display() # Initial call

        # Action Buttons Layout
        action_buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)

        self.generate_pdf_button = Button(
            text="Generate & Preview PDF",
            size_hint_x=0.5 # Occupy half the space
        )
        self.generate_pdf_button.bind(on_press=self.on_generate_pdf_button_pressed)
        action_buttons_layout.add_widget(self.generate_pdf_button)

        self.email_pdf_button = Button(
            text="Send by Email",
            size_hint_x=0.5 # Occupy other half
        )
        self.email_pdf_button.bind(on_press=self.on_email_pdf_button_pressed)
        action_buttons_layout.add_widget(self.email_pdf_button)

        main_layout.add_widget(action_buttons_layout)

        # Busy Indicator
        self.busy_indicator = ModalView(
            auto_dismiss=False, # Prevent dismissing by clicking outside
            size_hint=(None, None),
            size=('250dp', '120dp') # Adjusted size for better text fit
        )
        busy_label = Label(text='Processing, please wait...', halign='center', valign='middle')
        self.busy_indicator.add_widget(busy_label)

        # Clear Temporary Files Button
        # from kivy.uix.widget import Widget # if not already imported (not needed for this simple add)
        # main_layout.add_widget(Widget(size_hint_y=None, height='20dp')) # Example spacer

        self.clear_temp_files_button = Button(
            text="Clear Temporary Files",
            size_hint_y=None,
            height='48dp',
            # background_color=get_color_from_hex('#FFA07A') # Light Salmon
        )
        # self.clear_temp_files_button.background_normal = ''
        self.clear_temp_files_button.bind(on_press=self.on_clear_temp_files_button_pressed)
        main_layout.add_widget(self.clear_temp_files_button)


    def on_clear_temp_files_button_pressed(self, instance):
        if not self.app_temporary_files:
            self.show_info_popup("Clear Files", "No temporary files to clear.")
            return

        deleted_count = 0
        error_count = 0
        errors_details = []

        # Iterate over a copy of the list if modifying it during iteration by removal
        # However, it's safer to build a new list of files that remain.
        files_to_keep = []

        for file_path in self.app_temporary_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Successfully deleted temporary file: {file_path}")
                    deleted_count += 1
                else:
                    # File was already gone, effectively "deleted" from our tracking perspective for this session
                    print(f"Temporary file not found (already deleted?): {file_path}")
                    # We don't count this as an error, just that it's no longer tracked.
            except (FileNotFoundError, OSError) as e: # Catch FileNotFoundError specifically if needed, OSError for others
                print(f"Error deleting temporary file {file_path}: {e}")
                errors_details.append(f"{os.path.basename(file_path)}: {e}")
                error_count += 1
                files_to_keep.append(file_path) # Keep it in the list if deletion failed

        self.app_temporary_files = files_to_keep # Update the list with files that failed to delete

        summary_message = f"Attempted to clear temporary files.\nSuccessfully deleted: {deleted_count}"
        if error_count > 0:
            summary_message += f"\nFailed to delete: {error_count}"
            # For brevity, maybe only show first few error details or just a general error message.
            # For example: summary_message += f"\nDetails for first error: {errors_details[0]}" if errors_details else ""

        self.show_info_popup("Clear Files Result", summary_message)

        if not self.app_temporary_files: # If all files (including those that failed) are now gone or were removed
            print("All tracked temporary files have been processed or removed.")

    def on_email_pdf_button_pressed(self, instance):
        print("Send by Email button pressed. Generating PDFs...")
        pdf_outputs = self._trigger_pdf_generation() # Call the refactored helper

        if not pdf_outputs:
            print("PDF generation failed or was aborted. Cannot send email.")
            # self.show_error_popup("Email Error", "PDF generation failed. Cannot send email.") # Already shown by _trigger_pdf_generation or its callers.
            return

        self.last_generated_pdf_paths = [] # Store paths for the email step
        successfully_saved_all = True

        for i, (doc_name, pdf_bytes) in enumerate(pdf_outputs):
            temp_pdf_file = None
            try:
                # Use mkstemp for a unique name and handle file opening/closing manually
                fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix=f"{doc_name.replace(' ', '_')}_{i}_")
                with os.fdopen(fd, 'wb') as tmp_file_obj:
                    tmp_file_obj.write(pdf_bytes)

                self.last_generated_pdf_paths.append(temp_path)
                self.app_temporary_files.append(temp_path) # Add to global list as well
                print(f"PDF '{doc_name}' saved for email to: {temp_path}")

            except Exception as e_save:
                print(f"Error saving temporary PDF '{doc_name}' for email: {e_save}")
                self.show_error_popup("File Error", f"Could not save temporary PDF '{doc_name}': {e_save}")
                successfully_saved_all = False
                break # Stop if one file fails to save

        if successfully_saved_all and self.last_generated_pdf_paths:
            print(f"All {len(self.last_generated_pdf_paths)} PDF(s) saved successfully. Preparing for email.")

            if PLYER_EMAIL_AVAILABLE and plyer_email:
                try:
                    subject = "Generated Document(s)"
                    text_body = "Please find the attached document(s) generated by the app."
                    # For recipient, it's best if the user fills it in their email client.
                    # Some platforms might not support pre-filling it, or it might be ignored.
                    # recipient_email = "test@example.com" # Example, but usually omitted

                    print(f"Attempting to send email via plyer with attachments: {self.last_generated_pdf_paths}")
                    plyer_email.send(
                        # recipient=recipient_email, # Best to omit for user to fill
                        subject=subject,
                        text=text_body,
                        attachments=self.last_generated_pdf_paths
                        # create_chooser=True # Optionally force a chooser if multiple email apps
                    )
                    self.show_info_popup("Email Client",
                                         "Attempting to open your email client. Please check if it opened with the attachments.")
                    # TODO: Manage temporary files in self.last_generated_pdf_paths.
                    # They might need to persist until the email client has processed them.
                    # Consider a cleanup strategy (e.g., on app exit, or a cache with TTL).

                except NotImplementedError:
                    print("Plyer email feature is not implemented on this platform.")
                    paths_str = "\n".join(self.last_generated_pdf_paths)
                    self.show_error_popup("Email Feature Unavailable",
                                          f"Could not open email client (not implemented on this platform).\nPDFs saved at:\n{paths_str}")
                except Exception as e_email:
                    print(f"Error using plyer email: {e_email}")
                    paths_str = "\n".join(self.last_generated_pdf_paths)
                    self.show_error_popup("Email Error",
                                          f"An error occurred while trying to open the email client: {e_email}\nPDFs saved at:\n{paths_str}")
            else: # Plyer not available at all (ImportError)
                paths_str = "\n".join(self.last_generated_pdf_paths)
                self.show_error_popup("Email Feature Missing",
                                      f"Plyer email module not found. Cannot send email automatically.\nPDFs saved at:\n{paths_str}")

        elif not self.last_generated_pdf_paths and successfully_saved_all: # No PDFs were generated
            print("No PDFs were generated to email.")
            # This case should ideally be caught by the pdf_outputs check in _trigger_pdf_generation
            # or immediately after calling it.
        # else: (Failed to save one or more PDFs) - error popup already shown by previous logic
            # print("Failed to save one or more PDFs for email. Cannot proceed to email step.")
            # self.show_error_popup("Email Error", "Failed to save all necessary PDF files. Cannot send email.")

    def _trigger_pdf_generation(self) -> list | None:
            print("Failed to save one or more PDFs for email. Cleaning up successfully saved files for this attempt.")
            # Clean up any files already saved in this attempt if some failed later
            for path in self.last_generated_pdf_paths: # these are files from the current attempt
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"Cleaned up {path} from current failed email attempt.")
                        if path in self.app_temporary_files: # Also remove from global list
                            self.app_temporary_files.remove(path)
                except Exception as e_clean:
                    print(f"Error cleaning up {path}: {e_clean}")
            self.last_generated_pdf_paths = [] # Clear paths for current attempt

    def _trigger_pdf_generation(self) -> list | None:
        self.busy_indicator.open()
        try:
            # --- START of existing logic from _trigger_pdf_generation ---
            print("Gathering selections for PDF generation...")

            # 1. Get Language Code (and validation)
            selected_lang_name = self.language_spinner.text
            lang_data = next((lang for lang in self.languages_data if lang['name'] == selected_lang_name), None)
            if not lang_data:
                print("Validation Error: Please select a language.")
                # self.show_error_popup("Validation Error", "Please select a language.") # Popups are now handled by callers
                return None # Return None on validation failure
            language_code = lang_data['code']
            print(f"  Language Code: {language_code}")

            # 2. Get Country Data (and validation)
            selected_country_name = self.country_spinner.text
            country_info = next((country for country in self.countries_data if country['country_name'] == selected_country_name), None)
            if not country_info:
                print("Validation Error: Please select a country.")
                return None
            print(f"  Country Data: {country_info}")

            # 3. Get Selected Products (and validation)
            if not self.selected_products_for_document:
                print("Validation Error: Please add at least one product.")
                return None

            products_for_handler = []
        for item in self.selected_products_for_document:
            original_product_data = item.get('original_data', {})
            products_for_handler.append({
                'product_id': original_product_data.get('product_id'),
                'name': original_product_data.get('product_name'),
                'quantity': item.get('quantity')
            })
        print(f"  Products for Handler: {products_for_handler}")

        # 4. Get Selected Template (and validation)
        if not self.current_selected_template:
            print("Validation Error: Please select a document template.")
            return None
        templates_data_for_handler = [self.current_selected_template]
        print(f"  Template Data: {templates_data_for_handler}")

        # 5. Get PDF Action
        pdf_action = self.current_pdf_action
        print(f"  PDF Action: {pdf_action}")

        print("All selections gathered. Proceeding to call LiteDocumentHandler...")

        try:
            handler = LiteDocumentHandler()


            # Actual PDF generation call (can also raise exceptions)
            handler = LiteDocumentHandler()
            pdf_outputs = handler.generate_and_visualize_pdfs(
                language_code=language_code,
                country_data=country_info,
                products_with_qty=products_for_handler,
                templates_data=templates_data_for_handler,
                pdf_action=pdf_action
            )

            if pdf_outputs is None: # Handler explicitly returned None (e.g. context prep failed)
                print("PDF generation failed as handler returned None.")
                # Popups for this case will be handled by the calling methods (on_generate_pdf_button_pressed, on_email_pdf_button_pressed)
                # based on the None return value.

            return pdf_outputs # Return the outputs (or None if it failed before this)
            # --- END of existing logic ---

        except Exception as e: # Catch any unexpected errors during the process
            print(f"An unexpected error occurred in _trigger_pdf_generation: {e}")
            import traceback
            traceback.print_exc()
            # Popups for this case will be handled by the calling methods based on the None return value
            # or if this exception propagates (though returning None is cleaner here).
            return None # Ensure None is returned on such errors

        finally:
            self.busy_indicator.dismiss()


    def on_generate_pdf_button_pressed(self, instance):
        pdf_outputs = self._trigger_pdf_generation()
        self.last_pdf_outputs = pdf_outputs

        # self.last_pdf_outputs = pdf_outputs # This line should already exist

        if self.last_pdf_outputs:
                print(f"PDF generation successful (mocked). Number of documents: {len(self.last_pdf_outputs)}")

                # For simplicity, handle only the first PDF if multiple are generated by "combine" or "separate"
                doc_name, pdf_bytes = self.last_pdf_outputs[0]

                temp_pdf_file = None
                try:
                    # Create a temporary file to save the PDF
                    temp_pdf_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                    temp_pdf_file.write(pdf_bytes)
                    temp_pdf_path = temp_pdf_file.name
                    temp_pdf_file.close() # Close the file before trying to open it with another app

                    print(f"PDF '{doc_name}' saved temporarily to: {temp_pdf_path}")
                    self.app_temporary_files.append(temp_pdf_path) # Add to global list

                    popup_message_main = f"PDF '{doc_name}' generated and saved to:\n{temp_pdf_path}"
                    popup_message_plyer = ""

                    if PLYER_SHARING_AVAILABLE and plyer_sharing:
                        try:
                            print(f"Attempting to share/open PDF via plyer: {temp_pdf_path}")
                            plyer_sharing.share_file(path=temp_pdf_path)
                            popup_message_plyer = "\n\nAttempting to open/share the file with available apps."
                            # TODO: Manage temporary file temp_pdf_path.
                            # It might need to persist until the sharing action is complete.
                        except NotImplementedError:
                            print("Plyer sharing feature is not implemented on this platform.")
                            popup_message_plyer = "\n\nPlyer sharing is not available on this platform."
                        except Exception as e_share:
                            print(f"Error using plyer sharing: {e_share}")
                            popup_message_plyer = f"\n\nError trying to open/share: {e_share}"
                    else:
                        popup_message_plyer = "\n\nPlyer sharing module not found. Cannot open/share automatically."

                    self.show_info_popup("PDF Generated", popup_message_main + popup_message_plyer)

                except Exception as e_save:
                    print(f"Error saving temporary PDF: {e_save}")
                    self.show_error_popup("File Error", f"Could not save temporary PDF: {e_save}")
                    if temp_pdf_file: # Ensure closed if opened
                        try:
                            temp_pdf_file.close()
                        except: pass

            elif self.last_pdf_outputs is not None and not self.last_pdf_outputs : # Handler returned empty list
                print("PDF generation returned no output (mocked).")
                self.show_error_popup("PDF Generation Error", "No PDF was generated by the handler.")
            elif self.last_pdf_outputs is None: # Error during handler call
                 self.show_error_popup("PDF Generation Error", "An error occurred during PDF processing. Check logs.")


        except Exception as e:
            print(f"An error occurred during PDF generation: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_popup("System Error", f"An unexpected error occurred: {e}") # Changed from commented out to active
            self.last_pdf_outputs = None

    def show_info_popup(self, title, message):
        # Simple popup for information
        popup_layout = PopupBoxLayout(orientation='vertical', padding=10, spacing=10)
        # Allow message to be longer by using text_size for wrapping
        msg_label = Label(text=message, text_size=(self.width * 0.7, None), size_hint_y=None)
        msg_label.bind(texture_size=msg_label.setter('size')) # Adjust height for wrapped text
        popup_layout.add_widget(msg_label)

        close_button = PopupButton(text="OK", size_hint_y=None, height='48dp')
        popup_layout.add_widget(close_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, None), auto_dismiss=False)
        popup.bind(on_open=lambda instance: setattr(msg_label, 'width', instance.content.width - 20)) # Adjust label width on open
        popup.height = msg_label.height + close_button.height + 70 # Adjust popup height dynamically
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def show_error_popup(self, title, message):
        # You can reuse show_info_popup or make it distinct if needed (e.g., different styling)
        self.show_info_popup(title, message) # For now, they are the same

    def populate_template_spinner(self):
        self.templates_data = mobile_data_api.get_document_templates_from_api() # Assuming category=None fetches all relevant
        if self.templates_data:
            template_names = [tpl.get('template_name', 'Unnamed Template') for tpl in self.templates_data]
            self.template_spinner.values = template_names
            if template_names: # Set default text to first item if list is not empty
                self.template_spinner.text = template_names[0]
                # Also pre-select the first template's data
                self.current_selected_template = self.templates_data[0]
            else: # List is empty after fetching
                self.template_spinner.text = 'No templates found'
                self.current_selected_template = None
        else: # API returned None or empty list initially
            self.template_spinner.values = []
            self.template_spinner.text = 'Error loading templates'
            self.current_selected_template = None

    def on_template_select(self, spinner, text):
        selected_template_data = next((tpl for tpl in self.templates_data if tpl.get('template_name', 'Unnamed Template') == text), None)
        if selected_template_data:
            self.current_selected_template = selected_template_data
            print(f"Selected Template: {selected_template_data.get('template_name')}, ID: {selected_template_data.get('template_id')}")
        else:
            self.current_selected_template = None
            print(f"Selected Template Text: {text} (No full data found or 'No templates found')")

    def on_pdf_action_select(self, spinner, text):
        self.current_pdf_action = self.pdf_action_spinner_values.get(text, 'separate') # Get the mapped value
        print(f"Selected PDF Action: {text} (maps to: {self.current_pdf_action})")

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
        if self.highlighted_product_button:
            self.highlighted_product_button.background_color = [1, 1, 1, 1] # Default/White or Kivy's default
            # self.highlighted_product_button.background_normal = 'atlas://data/images/defaulttheme/button' # Example
            self.highlighted_product_button = None

        self.currently_selected_available_product = None
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

        # Reset previously highlighted button if any
        if self.highlighted_product_button and self.highlighted_product_button != button_instance:
            self.highlighted_product_button.background_color = [1, 1, 1, 1] # Default/White or Kivy's default
            # If you disabled background_normal for highlighting, you might need to re-enable it or set its color.
            # self.highlighted_product_button.background_normal = 'atlas://data/images/defaulttheme/button' # Example to reset

        # Highlight the new button
        button_instance.background_color = get_color_from_hex('#ADD8E6') # Light blue
        # Setting background_normal to empty string is often needed when setting background_color
        button_instance.background_normal = ''

        self.highlighted_product_button = button_instance
        self.currently_selected_available_product = product_data

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