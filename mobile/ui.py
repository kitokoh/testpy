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

import tempfile
import os # Useful for getting filename if needed, though tempfile handles it well
from kivy.uix.popup import Popup
# from kivy.uix.label import Label # Label is already imported
from kivy.uix.button import Button as PopupButton # To avoid conflict if Button is already aliased
from kivy.uix.boxlayout import BoxLayout as PopupBoxLayout # For popup layout

try:
    from plyer import email as plyer_email
    PLYER_EMAIL_AVAILABLE = True
except ImportError:
    PLYER_EMAIL_AVAILABLE = False
    plyer_email = None # Placeholder
    print("Plyer 'email' module not found. Email functionality will be limited.")

try:
    from plyer import filechooser
    PLYER_FILECHOOSER_AVAILABLE = True
except ImportError:
    filechooser = None
    PLYER_FILECHOOSER_AVAILABLE = False
    print("Plyer 'filechooser' module not found. PDF display functionality will be limited.")

# NLU, STT, and Controller imports
from . import nlu_handler
from . import nlu_controller # Added for this subtask
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False
    print("speech_recognition library not found. Voice command functionality will be disabled.")


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
        self.last_viewable_pdf_path = None # For displaying PDF


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

        # NLU Controls Section
        nlu_section_label = Label(text="Voice/Text Commands:", size_hint_y=None, height='30dp')
        main_layout.add_widget(nlu_section_label)

        nlu_controls_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, height='150dp')

        self.nlu_command_input = TextInput(hint_text='Type command (e.g., "add 2 apples")', multiline=False, size_hint_y=None, height='48dp')
        nlu_controls_layout.add_widget(self.nlu_command_input)

        nlu_buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        self.submit_command_button = Button(text='Submit Text Command')
        self.submit_command_button.bind(on_press=self.on_submit_command_button_pressed)
        nlu_buttons_layout.add_widget(self.submit_command_button)

        self.voice_command_button = Button(text='Use Voice Command')
        self.voice_command_button.bind(on_press=self.on_voice_command_button_pressed)
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.voice_command_button.disabled = True
            self.voice_command_button.text = 'Voice (mic unavailable)'
        nlu_buttons_layout.add_widget(self.voice_command_button)

        nlu_controls_layout.add_widget(nlu_buttons_layout)

        self.nlu_feedback_label = Label(text='NLU Status: Ready', size_hint_y=None, height='48dp')
        self.nlu_feedback_label.bind(texture_size=self.nlu_feedback_label.setter('size'))
        nlu_controls_layout.add_widget(self.nlu_feedback_label)

        main_layout.add_widget(nlu_controls_layout)

    def on_submit_command_button_pressed(self, instance):
        command_text = self.nlu_command_input.text
        if not command_text:
            self.nlu_feedback_label.text = "NLU: Please enter a command."
            return

        self.nlu_feedback_label.text = f"NLU: Processing command: \"{command_text}\"..."
        try:
            nlu_result = nlu_handler.parse_command(command_text)
            action_dict = nlu_controller.process_nlu_result(nlu_result)
            self._execute_nlu_action(action_dict)
        except Exception as e:
            self.nlu_feedback_label.text = f"NLU Error: Exception during processing: {e}"
            print(f"NLU processing exception: {e}")

    def on_voice_command_button_pressed(self, instance):
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.nlu_feedback_label.text = "NLU: Speech recognition module is not available."
            return

        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.nlu_feedback_label.text = "NLU: Adjusting for ambient noise..."
                self.voice_command_button.disabled = True
                self.submit_command_button.disabled = True
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self.nlu_feedback_label.text = "NLU: Listening..."
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    self.nlu_feedback_label.text = "NLU Error: No speech detected within time limit."
                    self.voice_command_button.disabled = False # Re-enable button
                    self.submit_command_button.disabled = False # Re-enable button
                    return # No need to proceed further

                self.nlu_feedback_label.text = "NLU: Recognizing..."
                # TODO: Add microphone permission check here using Plyer's permissions API
                # before trying to access the microphone, especially for Android/iOS.
                # Example: from plyer import-permissions; permissions.request_permissions([Permission.RECORD_AUDIO])
                try:
                    text = recognizer.recognize_google(audio)
                    self.nlu_command_input.text = text
                    # self.nlu_feedback_label.text = f"NLU: Recognized \"{text}\". Processing..." # on_submit will update this
                    self.on_submit_command_button_pressed(None)
                except sr.UnknownValueError:
                    self.nlu_feedback_label.text = "NLU Error: Speech Recognition could not understand audio."
                except sr.RequestError as e:
                    self.nlu_feedback_label.text = f"NLU Error: Could not request results from Speech Recognition service; {e}"
        except sr.exceptions.ALSAAudioError as e:
            self.nlu_feedback_label.text = f"NLU Audio Error: {e}. Check microphone."
            print(f"ALSA Audio Error: {e}")
        except IOError as e:
             self.nlu_feedback_label.text = f"NLU Microphone IO Error: {e}. Check microphone."
             print(f"Microphone IO Error: {e}")
        except Exception as e:
            self.nlu_feedback_label.text = f"NLU Voice Error: An unexpected error occurred: {e}"
            print(f"Unexpected voice error: {e}")
        finally:
            self.voice_command_button.disabled = False
            self.submit_command_button.disabled = False

    def _execute_nlu_action(self, action_dict: dict):
        action_type = action_dict.get('action_type')
        self.nlu_feedback_label.text = f"NLU: Executing action: {action_type}" # Initial feedback

        if action_type == "TRIGGER_PDF_GENERATION":
            pdf_outputs = self._perform_pdf_generation()
            if pdf_outputs and len(pdf_outputs) > 0: # Check if list is not None and not empty
                self.nlu_feedback_label.text = f"NLU: Successfully generated {len(pdf_outputs)} PDF document(s)."
                # Optionally trigger preview for the first document
                # self.on_generate_pdf_button_pressed(None) # This might re-trigger generation. Be careful.
                # Instead, directly call preview logic if needed:
                # doc_name, pdf_bytes = pdf_outputs[0]
                # self._preview_generated_pdf(doc_name, pdf_bytes) # Assuming such a refactored preview method
            elif pdf_outputs is not None and len(pdf_outputs) == 0: # Empty list means success but no files
                self.nlu_feedback_label.text = "NLU: PDF generation process completed, but no documents were produced."
            else: # pdf_outputs is None, meaning an error occurred
                self.nlu_feedback_label.text = "NLU: PDF generation failed or was cancelled. Check selections."

        elif action_type == "TRIGGER_PDF_DISPLAY":
            if PLYER_FILECHOOSER_AVAILABLE and self.last_viewable_pdf_path and os.path.exists(self.last_viewable_pdf_path):
                pdf_basename = os.path.basename(self.last_viewable_pdf_path)
                self.nlu_feedback_label.text = f"NLU: Attempting to open {pdf_basename} with an external viewer..."
                try:
                    filechooser.open_file(self.last_viewable_pdf_path)
                    self.nlu_feedback_label.text = f"NLU: {pdf_basename} sent to external viewer. Please check your system."
                except NotImplementedError:
                    self.nlu_feedback_label.text = "NLU Error: PDF viewing is not supported on this platform."
                    self.show_error_popup("Feature Unavailable", "PDF viewing is not supported on this device/platform.")
                except Exception as e:
                    self.nlu_feedback_label.text = f"NLU Error: Could not open PDF. {e}"
                    self.show_error_popup("PDF Display Error", f"Could not open the PDF file: {e}\nPath: {self.last_viewable_pdf_path}")
            elif not PLYER_FILECHOOSER_AVAILABLE:
                self.nlu_feedback_label.text = "NLU Error: PDF viewing feature (Plyer filechooser) is not available."
                self.show_error_popup("Feature Unavailable", "The PDF viewing feature is currently unavailable on this app installation.")
            else:
                self.nlu_feedback_label.text = "NLU: No PDF has been generated or the path is invalid. Please generate a PDF first."
                self.show_error_popup("No PDF Found", "Please generate a PDF document first using the 'Generate' button or a voice command.")


        elif action_type == "TRIGGER_EMAIL_SENDING":
            # Ensure PDFs are generated first if not already done
            if not self.last_pdf_outputs or len(self.last_pdf_outputs) == 0:
                self.nlu_feedback_label.text = "NLU: Please generate PDFs first before attempting to email."
                # Optionally, try to generate them now:
                # self.nlu_feedback_label.text = "NLU: Generating PDFs before emailing..."
                # pdf_outputs = self._perform_pdf_generation()
                # if not pdf_outputs:
                #     self.nlu_feedback_label.text = "NLU: PDF generation failed. Cannot email."
                #     return

            # Assuming PDFs exist (either previously or generated above)
            # The on_email_pdf_button_pressed method saves them to temp files and calls plyer.
            # It also uses self.last_generated_pdf_paths which should be populated correctly if _perform_pdf_generation was called.
            # However, on_email_pdf_button_pressed itself calls _perform_pdf_generation internally.
            # This could lead to double generation if not handled carefully.
            # For now, let's call it and rely on its internal logic.
            # The `on_email_pdf_button_pressed` was refactored to use `_perform_pdf_generation`
            # and then save files.

            recipient = action_dict.get('recipient')
            subject = action_dict.get('subject')

            feedback_msg = "NLU: Initiating email"
            if recipient:
                feedback_msg += f" to {recipient if len(recipient) < 30 else recipient[:27] + '...'}"
            if subject:
                feedback_msg += f" with subject \"{subject if len(subject) < 30 else subject[:27] + '...'}\""
            self.nlu_feedback_label.text = feedback_msg + "..." # This provides initial feedback

            self._initiate_email_sending(recipient=recipient, subject=subject)
            # _initiate_email_sending will set further feedback on NLU label if it was an NLU call.


        elif action_type == "ADD_UI_PRODUCT":
            product_name = action_dict.get("product_name")
            quantity = action_dict.get("quantity", 1)

            found_product_data = None
            # Ensure products_data is loaded, typically based on current language
            if not self.products_data:
                 self.populate_product_list() # Attempt to load products if list is empty
                 if not self.products_data:
                    self.nlu_feedback_label.text = f"NLU Error: Product list is empty. Select a language first."
                    return

            for p_data in self.products_data:
                if p_data.get("product_name", "").lower() == product_name.lower():
                    found_product_data = p_data
                    break

            if found_product_data:
                product_to_add = {'original_data': found_product_data, 'quantity': quantity}
                self.selected_products_for_document.append(product_to_add)
                self.refresh_selected_products_display()
                self.nlu_feedback_label.text = f"NLU: Added {quantity} of {product_name.title()} to document." # .title() for consistency
            else:
                self.nlu_feedback_label.text = f"NLU: Product '{product_name.title()}' not found. Try 'set language to [language]' if products for it are not listed, or check spelling."

        elif action_type == "UPDATE_UI_LANGUAGE":
            language_name = action_dict.get("language_name")
            # Case-insensitive search for language name in spinner values
            matched_value = next((val for val in self.language_spinner.values if val.lower() == language_name.lower()), None)
            if matched_value:
                self.language_spinner.text = matched_value # This triggers on_language_select -> populate_product_list
                self.nlu_feedback_label.text = f"NLU: Language set to {matched_value}."
            else:
                self.nlu_feedback_label.text = f"NLU Error: Language '{language_name}' not available. Available: {', '.join(self.language_spinner.values[:3])}..."


        elif action_type == "UPDATE_UI_COUNTRY":
            country_name = action_dict.get("country_name")
            matched_value = next((val for val in self.country_spinner.values if val.lower() == country_name.lower()), None)
            if matched_value:
                self.country_spinner.text = matched_value
                self.nlu_feedback_label.text = f"NLU: Country set to {matched_value}."
            else:
                self.nlu_feedback_label.text = f"NLU Error: Country '{country_name}' not available. Available: {', '.join(self.country_spinner.values[:3])}..."

        elif action_type == "UPDATE_UI_TEMPLATE":
            template_name = action_dict.get("template_name")
            matched_value = next((val for val in self.template_spinner.values if val.lower() == template_name.lower()), None)
            if matched_value:
                self.template_spinner.text = matched_value
                self.nlu_feedback_label.text = f"NLU: Template set to {matched_value}."
            else:
                self.nlu_feedback_label.text = f"NLU Error: Template '{template_name}' not available. Available: {', '.join(self.template_spinner.values[:3])}..."

        elif action_type in ["DISPLAY_NLU_HELP", "NLU_ERROR", "NLU_CLARIFICATION_NEEDED"]:
            message = action_dict.get('message', "NLU: An issue occurred.")
            self.nlu_feedback_label.text = f"NLU: {message}"
            # For HELP, might want a popup instead of just label
            if action_type == "DISPLAY_NLU_HELP":
                self.show_info_popup("Voice Command Help", message)


        else:
            unknown_action_msg = f"NLU: Unknown action type '{action_type}'."
            if action_dict.get('message'): # If controller provided a message for unknown
                unknown_action_msg = f"NLU: {action_dict.get('message')}"
            self.nlu_feedback_label.text = unknown_action_msg
            print(f"Unhandled NLU action: {action_dict}")

    def _initiate_email_sending(self, recipient: str = None, subject: str = None, text_body: str = None):
        """
        Handles the logic for sending an email, including PDF generation if necessary,
        saving PDFs to temporary files, and invoking the email client via Plyer.
        """
        print(f"Initiating email sending. Recipient: {recipient}, Subject: {subject}")

        if not PLYER_EMAIL_AVAILABLE:
            self.show_error_popup("Email Feature Missing", "Plyer email module not found. Cannot send email.")
            if recipient or subject: # If called from NLU, update NLU feedback
                self.nlu_feedback_label.text = "NLU Error: Email feature (Plyer) is not available."
            return

        # Step 1: Ensure PDFs are generated.
        # _perform_pdf_generation updates self.last_pdf_outputs and self.last_viewable_pdf_path.
        # It also handles its own error popups for PDF generation failures.
        current_pdf_outputs = self.last_pdf_outputs
        if not current_pdf_outputs:
            print("No PDFs previously generated. Generating now for email...")
            current_pdf_outputs = self._perform_pdf_generation()
            if not current_pdf_outputs: # Generation failed or produced nothing
                feedback = "NLU: PDF generation failed. Cannot email." if (recipient or subject) else "PDF generation failed for email."
                self.nlu_feedback_label.text = feedback # Update NLU label if applicable
                # _perform_pdf_generation already shows an error popup.
                return

        # Step 2: Save these PDFs to temporary files for attachment.
        # self.last_generated_pdf_paths will be populated here.
        self.last_generated_pdf_paths = []
        successfully_saved_all = True

        for i, (doc_name, pdf_bytes) in enumerate(current_pdf_outputs):
            try:
                fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix=f"{doc_name.replace(' ', '_')}_{i}_email_")
                with os.fdopen(fd, 'wb') as tmp_file_obj:
                    tmp_file_obj.write(pdf_bytes)
                self.last_generated_pdf_paths.append(temp_path)
                print(f"PDF '{doc_name}' saved for email attachment to: {temp_path}")
            except Exception as e_save:
                print(f"Error saving temporary PDF '{doc_name}' for email: {e_save}")
                self.show_error_popup("File Error", f"Could not save temporary PDF '{doc_name}': {e_save}")
                successfully_saved_all = False
                # Clean up any files already saved in this attempt
                for path_to_clean in self.last_generated_pdf_paths:
                    try:
                        if os.path.exists(path_to_clean): os.remove(path_to_clean)
                    except Exception as e_clean: print(f"Error cleaning up {path_to_clean}: {e_clean}")
                self.last_generated_pdf_paths = []
                break

        if not successfully_saved_all or not self.last_generated_pdf_paths:
            msg = "NLU: Failed to save PDFs for email attachment." if (recipient or subject) else "Failed to save PDFs for email."
            self.nlu_feedback_label.text = msg
            # Error popups for file saving are handled above.
            return

        # Step 3: Call Plyer email.send.
        print(f"All {len(self.last_generated_pdf_paths)} PDF(s) saved. Preparing for email client.")

        final_subject = subject if subject else "Generated Document(s) from App"
        final_text_body = text_body if text_body else "Please find the attached document(s)."

        try:
            plyer_email.send(
                recipient=recipient, # Plyer handles None recipient
                subject=final_subject,
                text=final_text_body,
                attachments=self.last_generated_pdf_paths
            )
            popup_msg = "Attempting to open your email client."
            if recipient: popup_msg += f"\nTo: {recipient}"
            if final_subject: popup_msg += f"\nSubject: {final_subject}"
            self.show_info_popup("Email Client", popup_msg)

            # Update NLU feedback label more specifically if called from NLU
            if recipient or subject: # Check if it was likely an NLU call
                 self.nlu_feedback_label.text = "NLU: Email client invoked. Please check for the draft."
            else: # Manual button press
                 self.nlu_feedback_label.text = "Email client invoked. Please check for the draft." # Or clear, or previous message from on_email_pdf_button_pressed

        except NotImplementedError:
            paths_str = "\n".join(self.last_generated_pdf_paths)
            error_message = f"Could not open email client (not implemented on this platform).\nPDFs saved at:\n{paths_str}"
            self.show_error_popup("Email Feature Unavailable", error_message)
            if recipient or subject: self.nlu_feedback_label.text = "NLU Error: Email feature not available on this platform."
        except Exception as e_email:
            paths_str = "\n".join(self.last_generated_pdf_paths)
            error_message = f"An error occurred with the email client: {e_email}\nPDFs saved at:\n{paths_str}"
            self.show_error_popup("Email Error", error_message)
            if recipient or subject: self.nlu_feedback_label.text = f"NLU Error: Email client error: {e_email}"
        # Note: Temporary files in self.last_generated_pdf_paths are not cleaned up here,
        # as the email client needs them. A robust app might have a cleanup strategy on exit or via cache management.

    def on_email_pdf_button_pressed(self, instance):
        print("Send by Email button (manual press) initiated.")
        self.nlu_feedback_label.text = "Initiating email..." # Generic feedback for button press
        self._initiate_email_sending()

    # Refactored PDF generation logic:
    # - _perform_pdf_generation: Core logic to gather data and call LiteDocumentHandler.
    # - on_generate_pdf_button_pressed: Calls _perform_pdf_generation and handles UI for preview.
    # - on_email_pdf_button_pressed: Calls _perform_pdf_generation, saves files, and handles email logic.

    def _perform_pdf_generation(self) -> list | None:
        """
        Gathers all necessary data from UI, calls LiteDocumentHandler to generate PDFs,
        and stores the output in self.last_pdf_outputs.
        Returns the list of (doc_name, pdf_bytes) tuples or None if generation fails or validations fail.
        Handles popups for validation errors.
        Also saves the path of the first generated PDF to self.last_viewable_pdf_path.
        """
        print("Gathering selections for PDF generation...")
        self.last_viewable_pdf_path = None # Reset before attempting generation

        selected_lang_name = self.language_spinner.text
        lang_data = next((lang for lang in self.languages_data if lang['name'] == selected_lang_name), None)
        if not lang_data or self.language_spinner.text == 'Select Language' or self.language_spinner.text == 'Error loading languages':
            self.show_error_popup("Validation Error", "Please select a valid language.")
            return None
        language_code = lang_data['code']

        selected_country_name = self.country_spinner.text
        country_info = next((country for country in self.countries_data if country['country_name'] == selected_country_name), None)
        if not country_info or self.country_spinner.text == 'Select Country' or self.country_spinner.text == 'Error loading countries':
            self.show_error_popup("Validation Error", "Please select a valid country.")
            return None

        if not self.selected_products_for_document:
            self.show_error_popup("Validation Error", "Please add at least one product to the document.")
            return None

        products_for_handler = []
        for item in self.selected_products_for_document:
            original_product_data = item.get('original_data', {})
            products_for_handler.append({
                'product_id': original_product_data.get('product_id'),
                'name': original_product_data.get('product_name'),
                'quantity': item.get('quantity')
            })

        if not self.current_selected_template or self.template_spinner.text == 'Select Template' or self.template_spinner.text == 'Error loading templates' or self.template_spinner.text == 'No templates found':
            self.show_error_popup("Validation Error", "Please select a valid document template.")
            return None
        templates_data_for_handler = [self.current_selected_template]
        pdf_action = self.current_pdf_action

        print(f"  Language: {language_code}, Country: {country_info.get('country_code')}, Products: {len(products_for_handler)}, Template: {self.current_selected_template.get('template_name')}, Action: {pdf_action}")
        print("Proceeding to call LiteDocumentHandler...")
        try:
            handler = LiteDocumentHandler()
            pdf_outputs = handler.generate_and_visualize_pdfs(
                language_code=language_code,
                country_data=country_info,
                products_with_qty=products_for_handler,
                templates_data=templates_data_for_handler,
                pdf_action=pdf_action
            )
            self.last_pdf_outputs = pdf_outputs

            if pdf_outputs: # Successfully generated one or more PDFs
                print(f"PDF generation successful. Number of documents: {len(pdf_outputs)}")
                # Save the first PDF for potential viewing.
                # This part is crucial for the DISPLAY_PDF intent.
                # We need to save it to a temp file that persists long enough.
                first_doc_name, first_pdf_bytes = pdf_outputs[0]
                try:
                    # Use mkstemp for a unique name and handle file opening/closing manually
                    # Prefix helps identify these specific temp files if cleanup is manual later.
                    fd, temp_view_path = tempfile.mkstemp(suffix=".pdf", prefix="invoice_app_view_")
                    with os.fdopen(fd, 'wb') as tmp_file_obj:
                        tmp_file_obj.write(first_pdf_bytes)
                    self.last_viewable_pdf_path = temp_view_path
                    print(f"First PDF '{first_doc_name}' saved for viewing to: {self.last_viewable_pdf_path}")
                    # Note: This file (self.last_viewable_pdf_path) should be cleaned up eventually,
                    # e.g., when a new PDF is generated, or on app exit.
                except Exception as e_save_view:
                    print(f"Error saving temporary PDF for viewing: {e_save_view}")
                    # Not critical enough to fail the whole generation, but log it.
                    self.last_viewable_pdf_path = None
                    # Optionally show a non-blocking warning to user or dev log.

            elif pdf_outputs is not None and not pdf_outputs:
                 print("PDF generation returned no output, though the process was successful.")
                 self.show_info_popup("PDF Generation", "The document generation process completed, but no files were produced (e.g., empty product list for selected template).")

            return pdf_outputs
        except Exception as e:
            print(f"An error occurred during PDF generation: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_popup("System Error", f"An unexpected error occurred during PDF generation: {e}")
            self.last_pdf_outputs = None
            return None

    def on_generate_pdf_button_pressed(self, instance):
        """Handles the 'Generate & Preview PDF' button press."""
        pdf_outputs = self._perform_pdf_generation() # This now handles popups for validation

        if pdf_outputs and len(pdf_outputs) > 0:
            print(f"PDF generation successful (for preview). Number of documents: {len(pdf_outputs)}")
            doc_name, pdf_bytes = pdf_outputs[0]

            temp_pdf_file = None # Should be fd, temp_pdf_path from mkstemp
            try:
                fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf", prefix=f"{doc_name.replace(' ', '_')}_preview_")
                with os.fdopen(fd, 'wb') as tmp_file_obj:
                    tmp_file_obj.write(pdf_bytes)

                print(f"PDF '{doc_name}' saved temporarily for preview to: {temp_pdf_path}")
                popup_message = (f"PDF '{doc_name}' generated and saved to:\n{temp_pdf_path}\n\n"
                                 "(On a real device, the app would attempt to open this file using a PDF viewer.)")
                # TODO: Add logic here or in popup to actually try and open temp_pdf_path with plyer.filechooser or similar
                self.show_info_popup("PDF Generated for Preview", popup_message)
            except Exception as e_save:
                print(f"Error saving temporary PDF for preview: {e_save}")
                self.show_error_popup("File Error", f"Could not save temporary PDF for preview: {e_save}")

        elif pdf_outputs is None:
             print("PDF generation failed or was cancelled, preview skipped. Error/validation popups handled by _perform_pdf_generation.")
        elif pdf_outputs is not None and len(pdf_outputs) == 0:
            print("PDF generation successful but no documents produced, preview skipped. Info popup handled by _perform_pdf_generation.")

    def show_info_popup(self, title, message):
        popup_layout = PopupBoxLayout(orientation='vertical', padding=10, spacing=10)
        msg_label = Label(text=message, text_size=(self.width * 0.7, None), size_hint_y=None)
        msg_label.bind(texture_size=msg_label.setter('size'))
        popup_layout.add_widget(msg_label)

        close_button = PopupButton(text="OK", size_hint_y=None, height='48dp')
        popup_layout.add_widget(close_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, None), auto_dismiss=True) # Changed auto_dismiss to True for info

        def adjust_label_width_and_popup_height(instance_popup):
            # This ensures that the text_size is set based on the actual content width of the popup
            # after it has been drawn and sized.
            content_width = instance_popup.content.width
            if content_width <=0: # handle case where content_width might not be ready
                content_width = self.width * 0.8 * 0.9 # Estimate based on popup size_hint and padding

            msg_label.text_size = (content_width - 20, None) # 20 for internal padding of popup_layout
            msg_label.texture_update()

            text_height = msg_label.texture_size[1]
            content_height = text_height + close_button.height + 40 # Adjusted padding for better look

            from kivy.core.window import Window
            max_popup_height = Window.height * 0.85 # Max 85% of window height

            final_popup_height = min(content_height, max_popup_height)
            instance_popup.height = final_popup_height
            # Center popup if height is less than max (optional, Kivy usually centers by default)
            # instance_popup.center_y = Window.height / 2


        popup.bind(on_open=adjust_label_width_and_popup_height)
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def show_error_popup(self, title, message):
        # Using a separate implementation for error popups for clarity or future styling
        popup_layout = PopupBoxLayout(orientation='vertical', padding=10, spacing=10)
        msg_label = Label(text=message, text_size=(self.width * 0.7, None), size_hint_y=None)
        msg_label.bind(texture_size=msg_label.setter('size'))
        popup_layout.add_widget(msg_label)

        close_button = PopupButton(text="OK", size_hint_y=None, height='48dp')
        popup_layout.add_widget(close_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, None), auto_dismiss=False) # Errors should not auto_dismiss

        def adjust_label_width_and_popup_height(instance_popup):
            content_width = instance_popup.content.width
            if content_width <=0:
                content_width = self.width * 0.8 * 0.9

            msg_label.text_size = (content_width - 20, None)
            msg_label.texture_update()

            text_height = msg_label.texture_size[1]
            content_height = text_height + close_button.height + 40

            from kivy.core.window import Window
            max_popup_height = Window.height * 0.85

            final_popup_height = min(content_height, max_popup_height)
            instance_popup.height = final_popup_height

        popup.bind(on_open=adjust_label_width_and_popup_height)
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def populate_template_spinner(self):
        self.templates_data = mobile_data_api.get_document_templates_from_api()
        if self.templates_data:
            template_names = [tpl.get('template_name', 'Unnamed Template') for tpl in self.templates_data]
            self.template_spinner.values = sorted(list(set(template_names))) # Unique, sorted
            if self.template_spinner.values:
                self.template_spinner.text = self.template_spinner.values[0]
                self.current_selected_template = next((tpl for tpl in self.templates_data if tpl.get('template_name') == self.template_spinner.text), None)
            else:
                self.template_spinner.text = 'No templates found'
                self.current_selected_template = None
        else:
            self.template_spinner.values = []
            self.template_spinner.text = 'Error loading templates'
            self.current_selected_template = None

    def on_template_select(self, spinner, text):
        # Ensure text matches an actual template name from data, not just spinner values
        selected_template_data = next((tpl for tpl in self.templates_data if tpl.get('template_name', 'Unnamed Template') == text), None)
        if selected_template_data:
            self.current_selected_template = selected_template_data
            print(f"Selected Template: {selected_template_data.get('template_name')}, ID: {selected_template_data.get('template_id')}")
        elif text not in ['Select Template', 'No templates found', 'Error loading templates']:
             print(f"Warning: Spinner text '{text}' selected but no matching template data found. This might be an issue if spinner values got out of sync with data.")
             self.current_selected_template = None # Avoid using stale data
        else: # Handle placeholder texts
            self.current_selected_template = None
            print(f"Template spinner has placeholder text: {text}")

    def populate_spinners(self):
        self.languages_data = mobile_data_api.get_languages_from_api()
        if self.languages_data:
            language_names = [lang['name'] for lang in self.languages_data if lang and 'name' in lang]
            self.language_spinner.values = sorted(list(set(language_names))) # Unique, sorted
            if self.language_spinner.values:
                self.language_spinner.text = self.language_spinner.values[0] # Triggers on_language_select
            else:
                self.language_spinner.text = "No languages found"
        else:
            self.language_spinner.values = []
            self.language_spinner.text = "Error loading languages"


        self.countries_data = mobile_data_api.get_all_countries_from_api()
        if self.countries_data:
            country_names = [country['country_name'] for country in self.countries_data if country and 'country_name' in country]
            self.country_spinner.values = sorted(list(set(country_names))) # Unique, sorted
            if self.country_spinner.values:
                self.country_spinner.text = self.country_spinner.values[0]
            else:
                self.country_spinner.text = "No countries found"
        else:
            self.country_spinner.values = []
            self.country_spinner.text = "Error loading countries"

        # Initial product list population based on default language (if any)
        # self.on_language_select will be called if language_spinner.text was set, which calls populate_product_list
        # If no languages, ensure populate_product_list is still called once.
        if not self.languages_data or not self.language_spinner.values :
            self.populate_product_list()


    def on_language_select(self, spinner, text):
        selected_lang_data = next((lang for lang in self.languages_data if lang['name'] == text), None)
        if selected_lang_data:
            print(f"Selected Language: {selected_lang_data['name']}, Code: {selected_lang_data['code']}")
            # Language change should always refresh the product list
            self.populate_product_list()
        elif text not in ['Select Language', 'No languages found', 'Error loading languages']:
            print(f"Warning: Language spinner text '{text}' selected but no matching language data found.")
            # Potentially clear product list or show error if language is invalid
            self.products_data = [] # Clear product data
            self.populate_product_list() # Refresh to show "No products"
        else:
            print(f"Language spinner has placeholder text: {text}")
            self.products_data = []
            self.populate_product_list()


    def populate_product_list(self):
        self.product_list_layout.clear_widgets()
        self.products_data = [] # Clear existing product data before fetching new

        selected_language_code = None
        if hasattr(self, 'languages_data') and self.languages_data and \
           self.language_spinner.text not in ['Select Language', 'No languages found', 'Error loading languages']:
            selected_lang_name = self.language_spinner.text
            lang_data = next((lang for lang in self.languages_data if lang['name'] == selected_lang_name), None)
            if lang_data:
                selected_language_code = lang_data['code']

        if not selected_language_code:
            # If no valid language selected, or an error state for language spinner
            self.product_list_layout.add_widget(Label(text="Please select a language to see products.", size_hint_y=None, height='40dp'))
            return # Do not attempt to fetch products

        # Fetch new product data
        fetched_products = mobile_data_api.get_all_products_for_selection_from_api(language_code=selected_language_code, name_pattern=None)
        if fetched_products:
            self.products_data = fetched_products # Store the fetched data
            for product in self.products_data:
                product_entry = Button(
                    text=f"{product.get('product_name', 'N/A')} - Price: {product.get('price', 'N/A')}",
                    size_hint_y=None,
                    height='48dp'
                )
                product_entry.product_data = product # Store full product data on the button
                product_entry.bind(on_press=self.on_available_product_tapped)
                self.product_list_layout.add_widget(product_entry)
        else:
            # API returned None or empty list for the selected language
            self.product_list_layout.add_widget(Label(text=f"No products found for {self.language_spinner.text}.", size_hint_y=None, height='40dp'))

        for i, (doc_name, pdf_bytes) in enumerate(pdf_outputs):
            temp_pdf_file = None
            try:
                # Use mkstemp for a unique name and handle file opening/closing manually
                fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix=f"{doc_name.replace(' ', '_')}_{i}_")
                with os.fdopen(fd, 'wb') as tmp_file_obj:
                    tmp_file_obj.write(pdf_bytes)

                self.last_generated_pdf_paths.append(temp_path)
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
            for path in self.last_generated_pdf_paths:
                try:
                    if os.path.exists(path): os.remove(path)
                except Exception as e_clean: print(f"Error cleaning up {path}: {e_clean}")
            self.last_generated_pdf_paths = [] # Clear paths

    def _trigger_pdf_generation(self) -> list | None:
        # Generate PDF Button
        self.generate_pdf_button = Button(
            text="Generate & Preview PDF",
            size_hint_y=None,
            height='48dp'
            # Optional: Add some top margin if needed: padding or add a Spacer before it
            # main_layout.add_widget(Widget(size_hint_y=None, height='10dp')) # Spacer example
        )
        self.generate_pdf_button.bind(on_press=self.on_generate_pdf_button_pressed)
        main_layout.add_widget(self.generate_pdf_button) # Added to main_layout

    def on_generate_pdf_button_pressed(self, instance):
        print("Gathering selections for PDF generation...")

        # 1. Get Language Code
        selected_lang_name = self.language_spinner.text
        lang_data = next((lang for lang in self.languages_data if lang['name'] == selected_lang_name), None)
        if not lang_data:
            print("Validation Error: Please select a language.")
            self.show_error_popup("Validation Error", "Please select a language.")
            return None

        language_code = lang_data['code']
        print(f"  Language Code: {language_code}")

        # 2. Get Country Data
        selected_country_name = self.country_spinner.text
        country_info = next((country for country in self.countries_data if country['country_name'] == selected_country_name), None)
        if not country_info:
            print("Validation Error: Please select a country.")
            self.show_error_popup("Validation Error", "Please select a country.")
            return None

        print(f"  Country Data: {country_info}")

        # 3. Get Selected Products with Quantities
        if not self.selected_products_for_document:
            print("Validation Error: Please add at least one product.")
            self.show_error_popup("Validation Error", "Please add at least one product.")
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

        # 4. Get Selected Template
        if not self.current_selected_template:
            print("Validation Error: Please select a document template.")
            self.show_error_popup("Validation Error", "Please select a document template.")
            return None

        templates_data_for_handler = [self.current_selected_template]
        print(f"  Template Data: {templates_data_for_handler}")

        # 5. Get PDF Action
        pdf_action = self.current_pdf_action
        print(f"  PDF Action: {pdf_action}")

        print("All selections gathered. Proceeding to call LiteDocumentHandler...")

        try:
            handler = LiteDocumentHandler()

            pdf_outputs = handler.generate_and_visualize_pdfs(
                language_code=language_code,
                country_data=country_info,
                products_with_qty=products_for_handler,
                templates_data=templates_data_for_handler,
                pdf_action=pdf_action
            )
            return pdf_outputs # Return the generated outputs

        except Exception as e:
            print(f"An error occurred during PDF generation: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_popup("System Error", f"An unexpected error occurred: {e}")
            return None # Return None on error


    def on_generate_pdf_button_pressed(self, instance):
        pdf_outputs = self._trigger_pdf_generation()
        self.last_pdf_outputs = pdf_outputs

        # self.last_pdf_outputs = pdf_outputs # This line should already exist

        if self.last_pdf_outputs:

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

                    # Inform user via Popup
                    popup_message = f"PDF '{doc_name}' generated and saved to:\n{temp_pdf_path}\n\n(Normally, the app would attempt to open this file.)"
                    # TODO: Use plyer.filechooser.open_file(temp_pdf_path) or plyer.sharing.share_file(temp_pdf_path) to open/share.
                    self.show_info_popup("PDF Generated", popup_message)

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
            # If self.last_pdf_outputs is None, the try-except for handler call already printed an error.
            # We could add an else here to show a generic error popup if self.last_pdf_outputs is None.
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

# Mobile UI Requirements and Placeholder Stubs
# This file outlines the necessary UI screens and components.
# Actual implementation will depend on the chosen mobile framework (e.g., Kivy, React Native, Flutter).

from typing import Optional, List, Dict # Added for type hinting clarity

# --- Data Models (for UI state, not exhaustive) ---
class SelectedProduct:
    def __init__(self, product_id, name, quantity):
        self.product_id = product_id
        self.name = name
        self.quantity = quantity

# --- Main Application Screen ---
class MainScreen:
    def __init__(self, app_controller):
        self.app_controller = app_controller # To handle navigation and actions
        print("UI STUB: Initializing MainScreen")
        # Components:
        # - Button: "Generate New Document" (navigates to DocumentGenerationScreen)
        # - (Optional) List of recently generated documents
        # - Button: "Settings" (navigates to SettingsScreen)

    def display(self):
        print("UI STUB: Displaying MainScreen")

# --- Document Generation Screen ---
class DocumentGenerationScreen:
    def __init__(self, app_controller, document_handler, data_handler):
        self.app_controller = app_controller
        self.document_handler = document_handler # To call for PDF generation
        self.data_handler = data_handler # To fetch data for selectors

        print("UI STUB: Initializing DocumentGenerationScreen")

        # --- State ---
        self.selected_language: Optional[str] = None
        self.selected_country: Optional[str] = None # Country ID
        self.available_products: List[Dict] = []
        self.selected_products: List[SelectedProduct] = []
        self.available_templates: List[Dict] = []
        self.chosen_templates: List[Dict] = [] # Store full template data
        self.pdf_action: str = "separate" # "separate" or "combine"
        self.product_search_term: str = ""
        self.current_product_quantity: int = 1

        # --- UI Elements (Conceptual) ---
        # Language Selector (e.g., Dropdown)
        # Country Selector (e.g., Dropdown)
        # Product Search Input
        # Available Products List (e.g., RecyclerView, ListView)
        # Product Quantity Input
        # Add Product Button
        # Selected Products List
        # Remove Product Button
        # Document Template Selector (e.g., Multi-select list)
        # PDF Action Radio Buttons/Toggle (Separate/Combine)
        # Generate/Preview PDF Button
        # Send by Email Button
        # Back/Cancel Button

    def load_initial_data(self):
        print("UI STUB: DocumentGenerationScreen - Loading initial data (languages, countries, templates, initial products)")
        # self.languages = self.data_handler.get_languages_from_api()
        # self.countries = self.data_handler.get_all_countries_from_api()
        # self.available_templates = self.data_handler.get_document_templates_from_api()
        # self.refresh_available_products()
        pass

    def refresh_available_products(self):
        print(f"UI STUB: DocumentGenerationScreen - Refreshing available products with search: {self.product_search_term}, lang: {self.selected_language}")
        # self.available_products = self.data_handler.get_all_products_for_selection_from_api(
        #     language_code=self.selected_language,
        #     name_pattern=self.product_search_term
        # )
        # Update UI list for available_products
        pass

    def on_add_product_clicked(self, product_data_from_ui_selection):
        print(f"UI STUB: DocumentGenerationScreen - Add product: {product_data_from_ui_selection} with qty: {self.current_product_quantity}")
        # product_id = product_data_from_ui_selection.get('product_id')
        # product_name = product_data_from_ui_selection.get('product_name')
        # new_selected = SelectedProduct(product_id, product_name, self.current_product_quantity)
        # self.selected_products.append(new_selected)
        # Update UI list for selected_products
        pass

    def on_remove_product_clicked(self, product_to_remove: SelectedProduct):
        print(f"UI STUB: DocumentGenerationScreen - Remove product: {product_to_remove.name}")
        # self.selected_products.remove(product_to_remove)
        # Update UI list for selected_products
        pass

    def on_generate_preview_pdf_clicked(self):
        print("UI STUB: DocumentGenerationScreen - Generate/Preview PDF clicked")
        # Validate selections (language, country, products, templates)
        # if not self.selected_language or not self.selected_country or not self.selected_products or not self.chosen_templates:
        #     print("UI ALERT: Please make all necessary selections.")
        #     return

        # Call the document handler
        # pdf_outputs = self.document_handler.generate_and_visualize_pdfs(
        #     language_code=self.selected_language,
        #     country_data={'country_id': self.selected_country, 'country_name': 'MockCountryFromUI'}, # Fetch actual name if needed
        #     products_with_qty=[{'product_id': p.product_id, 'name': p.name, 'quantity': p.quantity} for p in self.selected_products],
        #     templates_data=self.chosen_templates,
        #     pdf_action=self.pdf_action
        # )
        # if pdf_outputs:
        #     # On mobile: save the first PDF (or combined PDF) to a temp file
        #     # Use a platform-specific mechanism to open/share the PDF file.
        #     # For example, using Kivy's plyer: plyer.filechooser.open_file(path_to_pdf)
        #     # or trigger a share intent on Android/iOS.
        #     print(f"UI STUB: {len(pdf_outputs)} PDF(s) generated. Would attempt to open/share now.")
        pass

    def on_send_email_clicked(self):
        print("UI STUB: DocumentGenerationScreen - Send by Email clicked")
        # Similar to generate/preview, but then:
        # 1. Generate PDFs (handler returns list of (name, bytes) tuples).
        # 2. Save PDFs to temporary files.
        # 3. Construct email (recipients, subject, body - possibly prompt user).
        # 4. Use platform-specific email intent with attachments.
        #    Example: Kivy's plyer.email.send(recipient='...', subject='...', text='...', attachments=[path1, path2])
        # Note: The current `document_handler.generate_and_send_email` is heavily commented out
        # as it uses direct SMTP. Mobile apps should use intents.
        # So, the logic here would be:
        #   - Get PDF bytes using similar logic to `generate_and_visualize_pdfs`.
        #   - Then, use mobile's native email client.
        pass

    def display(self):
        print("UI STUB: Displaying DocumentGenerationScreen")
        # self.load_initial_data()
        # Render all UI elements
        pass

# --- Settings Screen ---
class SettingsScreen:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        print("UI STUB: Initializing SettingsScreen")
        # Components:
        # - Input field for API base URL
        # - User account info (if applicable)
        # - Save Settings Button
        # - Back Button

    def display(self):
        print("UI STUB: Displaying SettingsScreen")

# --- App Controller (for navigation and overall app state) ---
class MobileAppController:
    def __init__(self):
        print("UI STUB: Initializing MobileAppController")
        # self.data_handler = mobile_data_api # from mobile.data_handler
        # self.doc_handler = LiteDocumentHandler() # from mobile.document_handler
        # self.main_screen = MainScreen(self)
        # self.doc_gen_screen = DocumentGenerationScreen(self, self.doc_handler, self.data_handler)
        # self.settings_screen = SettingsScreen(self)
        # self.current_screen = self.main_screen

    def start(self):
        print("UI STUB: MobileAppController - Starting app")
        # self.current_screen.display()
        pass

    def navigate_to(self, screen_name: str):
        print(f"UI STUB: MobileAppController - Navigating to {screen_name}")
        # if screen_name == "document_generation":
        #     self.current_screen = self.doc_gen_screen
        # elif screen_name == "settings":
        #     self.current_screen = self.settings_screen
        # else:
        #     self.current_screen = self.main_screen
        # self.current_screen.display()
        pass

# Example of how it might be initiated in main.py (conceptual)
# if __name__ == '__main__':
#     app_controller = MobileAppController()
#     app_controller.start()
