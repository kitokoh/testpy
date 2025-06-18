import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QGroupBox, QMessageBox, QListWidget, QInputDialog,
    QListWidgetItem
)
from PyQt5.QtCore import Qt

# Project specific imports - adjust path if necessary
from .api_client import BotpressClient, BotpressAPIError # Import custom API error
from .crud import (
    get_botpress_settings, create_or_update_botpress_settings,
    get_prompts_for_user, create_user_prompt, update_user_prompt, delete_user_prompt
    # get_prompt_by_name is used internally by CRUD, not directly here.
)
from .models import SessionLocal, create_db_and_tables, UserPrompt # UserPrompt needed for type hint / query in edit
from sqlalchemy.exc import SQLAlchemyError # Import for DB error handling

# Setup basic logging if not already configured by the main application
# This is good practice for module independence.
# In a larger app, the main entry point would usually configure logging.
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class BotpressIntegrationUI(QWidget):
    def __init__(self, parent=None, current_user_id=None):
        super().__init__(parent)
        self.setWindowTitle('Botpress Integration')
        self.logger = logging.getLogger(__name__) # Get a logger for this class
        self.logger.info(f"Initializing BotpressIntegrationUI for user_id: {current_user_id}")

        self.current_user_id = current_user_id
        if not self.current_user_id:
            self.logger.error("BotpressIntegrationUI initialized without a current_user_id!")
            # Potentially show a message box here or disable functionality,
            # but constructor shouldn't have complex UI interactions.
            # For now, rely on later checks in methods like load_settings.

        self.botpress_client = None
        self.db_session = None # Initialize later to handle potential DB connection errors
        self.current_settings_id = None

        try:
            # Ensure DB schema is created (idempotent)
            create_db_and_tables()
            self.db_session = SessionLocal()
            self.logger.info("Database session created and tables ensured.")
        except SQLAlchemyError as e:
            self.logger.critical(f"Failed to connect to database or create tables: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error",
                                 "Could not connect to the database. Some features will be unavailable. "
                                 "Please check logs for details.")
            # self.db_session will remain None, subsequent operations requiring it should fail gracefully.

        self.init_ui()
        if self.db_session: # Only load settings if DB session is available
            self.load_settings()
        else:
            self.logger.warning("Skipping initial load_settings due to DB session failure.")
            # Disable UI elements that depend on DB
            self.save_settings_button.setEnabled(False)
            self.load_settings_button.setEnabled(False)
            self.add_prompt_button.setEnabled(False)
            self.edit_prompt_button.setEnabled(False)
            self.delete_prompt_button.setEnabled(False)


    def init_ui(self):
        self.logger.debug("Initializing UI components.")
        main_layout = QVBoxLayout(self)

        # API Configuration
        api_group = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter Botpress API Key")
        api_layout.addWidget(QLabel("API Key:"))
        api_layout.addWidget(self.api_key_input)

        self.bot_id_input = QLineEdit()
        self.bot_id_input.setPlaceholderText("Enter Botpress Bot ID")
        api_layout.addWidget(QLabel("Bot ID:"))
        api_layout.addWidget(self.bot_id_input)

        config_buttons_layout = QHBoxLayout()
        self.load_settings_button = QPushButton("Load Settings")
        self.load_settings_button.clicked.connect(self.load_settings)
        config_buttons_layout.addWidget(self.load_settings_button)

        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self.save_settings)
        config_buttons_layout.addWidget(self.save_settings_button)
        api_layout.addLayout(config_buttons_layout)

        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # Conversation Display
        conversation_group = QGroupBox("Conversation")
        conversation_layout = QVBoxLayout()
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        conversation_layout.addWidget(self.conversation_display)
        conversation_group.setLayout(conversation_layout)
        main_layout.addWidget(conversation_group)

        # Message Input
        message_input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self.handle_send_message) # Send on Enter
        message_input_layout.addWidget(self.message_input)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send_message)
        message_input_layout.addWidget(self.send_button)
        main_layout.addLayout(message_input_layout)

        # Prompts Management
        prompts_group = QGroupBox("Prompts Management")
        prompts_main_layout = QVBoxLayout() # Main layout for this group

        self.prompts_list_widget = QListWidget()
        self.prompts_list_widget.itemDoubleClicked.connect(self.edit_selected_prompt) # Edit on double click
        prompts_main_layout.addWidget(self.prompts_list_widget)

        prompts_buttons_layout = QHBoxLayout()
        self.add_prompt_button = QPushButton("Add Prompt")
        self.add_prompt_button.clicked.connect(self.add_prompt)
        prompts_buttons_layout.addWidget(self.add_prompt_button)
        self.edit_prompt_button = QPushButton("Edit Prompt")
        self.edit_prompt_button.clicked.connect(self.edit_selected_prompt)
        prompts_buttons_layout.addWidget(self.edit_prompt_button)
        self.delete_prompt_button = QPushButton("Delete Prompt")
        self.delete_prompt_button.clicked.connect(self.delete_selected_prompt)
        prompts_buttons_layout.addWidget(self.delete_prompt_button)

        prompts_main_layout.addLayout(prompts_buttons_layout)
        prompts_group.setLayout(prompts_main_layout)
        main_layout.addWidget(prompts_group)

        self.setLayout(main_layout)

    def load_settings(self):
        if not self.db_session:
            QMessageBox.critical(self, "Database Error", "Database session not available. Cannot load settings.")
            self.logger.error("load_settings called but db_session is None.")
            return

        if not self.current_user_id:
            QMessageBox.warning(self, "User Error", "User ID not set. Cannot load settings.")
            self.logger.warning("load_settings: current_user_id is not set.")
            return

        self.logger.info(f"Loading settings for user_id: {self.current_user_id}")
        try:
            settings = get_botpress_settings(self.db_session, user_id=self.current_user_id)
            if settings:
                self.api_key_input.setText(settings.api_key)
                self.bot_id_input.setText(settings.bot_id)
                self.current_settings_id = settings.id
                self.logger.info(f"Settings found for user {self.current_user_id}. Settings ID: {self.current_settings_id}")
                try:
                    self.botpress_client = BotpressClient(api_key=settings.api_key, bot_id=settings.bot_id)
                    QMessageBox.information(self, "Settings Loaded", "API settings loaded and Botpress client initialized.")
                    self.conversation_display.append("<i>API Client initialized. Ready to chat.</i>")
                    self.load_conversation_history()
                    self.load_prompts()
                except Exception as e: # Catch errors from BotpressClient instantiation (e.g. bad URL if not mock)
                    self.logger.error(f"Failed to initialize Botpress client after loading settings: {e}", exc_info=True)
                    QMessageBox.critical(self, "API Client Error", f"Failed to initialize Botpress client: {e}")
                    self.botpress_client = None
            else:
                self.logger.info(f"No settings found for user {self.current_user_id}. Clearing fields.")
                QMessageBox.information(self, "No Settings", "No API settings found for this user. Please configure.")
                self.api_key_input.clear()
                self.bot_id_input.clear()
                self.botpress_client = None
                self.current_settings_id = None
                self.prompts_list_widget.clear()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error while loading settings for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Error loading settings: {e}. Check logs.")
            self.botpress_client = None # Ensure client is None on DB error
        except Exception as e: # Catch any other unexpected errors
            self.logger.error(f"Unexpected error while loading settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {e}. Check logs.")
            self.botpress_client = None


    def save_settings(self):
        if not self.db_session:
            QMessageBox.critical(self, "Database Error", "Database session not available. Cannot save settings.")
            self.logger.error("save_settings called but db_session is None.")
            return

        if not self.current_user_id:
            QMessageBox.warning(self, "User Error", "User ID not set. Cannot save settings.")
            self.logger.warning("save_settings: current_user_id is not set.")
            return

        api_key = self.api_key_input.text().strip()
        bot_id = self.bot_id_input.text().strip()

        if not api_key or not bot_id:
            QMessageBox.warning(self, "Input Error", "API Key and Bot ID cannot be empty.")
            return

        self.logger.info(f"Saving settings for user_id: {self.current_user_id}")
        try:
            settings = create_or_update_botpress_settings(
                self.db_session,
                user_id=self.current_user_id,
                api_key=api_key,
                bot_id=bot_id
            )
            self.current_settings_id = settings.id
            self.botpress_client = BotpressClient(api_key=api_key, bot_id=bot_id) # Re-initialize client
            QMessageBox.information(self, "Settings Saved", "API settings saved and client re-initialized.")
            self.conversation_display.append("<i>API Client re-initialized with new settings.</i>")
            self.logger.info(f"Settings saved successfully for user {self.current_user_id}. New settings_id: {self.current_settings_id}")
            self.load_prompts() # Refresh prompts list as settings_id might be new
        except SQLAlchemyError as e:
            self.logger.error(f"Database error saving settings for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to save settings due to database error: {e}. Check logs.")
            # self.botpress_client might be in an inconsistent state if it was initialized before commit failed.
            # Best to set it to None or try to reload previous valid settings. For now, set to None.
            self.botpress_client = None
        except Exception as e: # Catch errors from BotpressClient instantiation or other issues
            self.logger.error(f"Error saving settings or initializing client for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}. Check logs.")
            self.botpress_client = None


    def handle_send_message(self):
        self.logger.debug("handle_send_message called.")
        if not self.botpress_client:
            QMessageBox.warning(self, "Client Not Ready", "Botpress client is not initialized. Please check API settings and load them.")
            self.logger.warning("handle_send_message: Botpress client not initialized.")
            return

        user_message = self.message_input.text().strip()
        if not user_message:
            return

        self.conversation_display.append(f"<b>You:</b> {user_message}")
        self.logger.info(f"User sending message: {user_message}")
        try:
            response = self.botpress_client.send_message(user_message)
            self.conversation_display.append(f"<b>Bot:</b> {response}")
            self.logger.info(f"Bot response received: {response}")
        except BotpressAPIError as e: # Catch custom API errors first
            self.logger.error(f"Botpress API error sending message: {e}", exc_info=True)
            QMessageBox.critical(self, "API Error", f"Botpress API error: {e}")
            self.conversation_display.append(f"<i>API Error: {e}</i>")
        except Exception as e: # Catch other errors like ConnectionError from requests
            self.logger.error(f"Error sending message via Botpress client: {e}", exc_info=True)
            QMessageBox.critical(self, "Send Error", f"Failed to send message: {e}")
            self.conversation_display.append(f"<i>Error sending message: {e}</i>")

        self.message_input.clear()
        self.conversation_display.verticalScrollBar().setValue(self.conversation_display.verticalScrollBar().maximum())


    def load_conversation_history(self):
        self.logger.debug("load_conversation_history called.")
        if not self.botpress_client:
            self.logger.info("load_conversation_history: Botpress client not ready.")
            # self.conversation_display.append("<i>Botpress client not initialized. Cannot load history.</i>")
            return

        self.conversation_display.append("<i>Loading conversation history (mock)...</i>")
        try:
            history = self.botpress_client.get_conversations() # Mock
            for message in history:
                sender = "Bot" if message.get("sender", "").lower() == "bot" else "User"
                self.conversation_display.append(f"<b>{sender}:</b> {message.get('text', '')}")
            self.conversation_display.append("<i>--- End of mock history ---</i>")
            self.logger.info("Mock conversation history loaded.")
        except BotpressAPIError as e:
            self.logger.error(f"Botpress API error loading history: {e}", exc_info=True)
            QMessageBox.critical(self, "API Error", f"Botpress API error loading history: {e}")
            self.conversation_display.append(f"<i>API Error loading history: {e}</i>")
        except Exception as e:
            self.logger.error(f"Error loading conversation history: {e}", exc_info=True)
            QMessageBox.critical(self, "History Error", f"Failed to load conversation history: {e}")
            self.conversation_display.append(f"<i>Error loading history: {e}</i>")
        self.conversation_display.verticalScrollBar().setValue(self.conversation_display.verticalScrollBar().maximum())

    # --- Prompts Management ---
    def load_prompts(self):
        self.logger.debug("load_prompts called.")
        self.prompts_list_widget.clear()
        if not self.db_session:
            self.logger.error("load_prompts: db_session is None.")
            # No QMessageBox here as it might be too noisy if DB failed on init
            return

        if not self.current_settings_id:
            self.logger.info("load_prompts: current_settings_id is not set. Cannot load prompts.")
            # self.prompts_list_widget.addItem("Botpress settings not yet configured for this user.")
            return

        self.logger.info(f"Loading prompts for settings_id: {self.current_settings_id}")
        try:
            prompts = get_prompts_for_user(self.db_session, settings_id=self.current_settings_id)
            if not prompts:
                self.prompts_list_widget.addItem(QListWidgetItem("No prompts defined yet.")) # Use QListWidgetItem
                self.logger.info("No prompts found for this user.")
            for prompt in prompts:
                item = QListWidgetItem(f"{prompt.prompt_name}: {prompt.prompt_text[:50]}...")
                item.setData(Qt.UserRole, prompt.id)
                item.setToolTip(f"ID: {prompt.id}\nName: {prompt.prompt_name}\nText: {prompt.prompt_text}")
                self.prompts_list_widget.addItem(item)
            self.logger.info(f"Loaded {len(prompts)} prompts.")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error loading prompts for settings_id {self.current_settings_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Load Prompts Error", f"Failed to load prompts due to database error: {e}. Check logs.")
        except Exception as e:
            self.logger.error(f"Unexpected error loading prompts for settings_id {self.current_settings_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Load Prompts Error", f"An unexpected error occurred while loading prompts: {e}. Check logs.")


    def add_prompt(self):
        self.logger.debug("add_prompt called.")
        if not self.db_session:
            QMessageBox.critical(self, "Database Error", "Database session not available. Cannot add prompt.")
            self.logger.error("add_prompt: db_session is None.")
            return
        if not self.current_settings_id:
            QMessageBox.warning(self, "Action Blocked", "Please save Botpress API/Bot ID settings first before adding prompts.")
            self.logger.warning("add_prompt: current_settings_id is not set.")
            return

        name, ok_name = QInputDialog.getText(self, "Add Prompt", "Prompt Name:")
        if ok_name and name.strip():
            text, ok_text = QInputDialog.getMultiLineText(self, "Add Prompt", f"Prompt Text for '{name.strip()}':")
            if ok_text and text.strip():
                try:
                    create_user_prompt(self.db_session, settings_id=self.current_settings_id, prompt_name=name.strip(), prompt_text=text.strip())
                    self.load_prompts()
                    QMessageBox.information(self, "Prompt Added", f"Prompt '{name.strip()}' added successfully.")
                except ValueError as ve: # Catch duplicate name error from CRUD
                     QMessageBox.warning(self, "Add Prompt Error", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "Add Prompt Error", f"Failed to add prompt: {e}")
                    logging.error(f"Error adding prompt for settings_id {self.current_settings_id}: {e}", exc_info=True)
        elif ok_name and not name.strip():
            QMessageBox.warning(self, "Input Error", "Prompt name cannot be empty.")


    def edit_selected_prompt(self):
        selected_item = self.prompts_list_widget.currentItem()
        if not selected_item or selected_item.text() == "No prompts defined yet.":
            QMessageBox.warning(self, "Selection Error", "Please select a prompt to edit.")
            return

        prompt_id = selected_item.data(Qt.UserRole)
        if prompt_id is None : # Should not happen if item is valid
            QMessageBox.critical(self, "Error", "Selected item has no ID. Cannot edit.")
            return

        # Fetch the full prompt details for editing
        prompt_to_edit = self.db_session.query(UserPrompt).filter(UserPrompt.id == prompt_id).first()
        if not prompt_to_edit:
            QMessageBox.error(self, "Error", f"Prompt with ID {prompt_id} not found in database.")
            self.load_prompts() # Refresh list
            return

        name, ok_name = QInputDialog.getText(self, "Edit Prompt", "Prompt Name:", text=prompt_to_edit.prompt_name)
        if ok_name and name.strip():
            text, ok_text = QInputDialog.getMultiLineText(self, "Edit Prompt", f"Prompt Text for '{name.strip()}':", text=prompt_to_edit.prompt_text)
            if ok_text: # Allow empty text if user wants to clear it
                try:
                    update_user_prompt(self.db_session, prompt_id=prompt_id, prompt_name=name.strip(), prompt_text=text) # Allow empty string for text
                    self.load_prompts()
                    QMessageBox.information(self, "Prompt Updated", f"Prompt '{name.strip()}' updated successfully.")
                except ValueError as ve: # Catch duplicate name error from CRUD
                     QMessageBox.warning(self, "Update Prompt Error", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "Update Prompt Error", f"Failed to update prompt: {e}")
                    logging.error(f"Error updating prompt_id {prompt_id}: {e}", exc_info=True)
        elif ok_name and not name.strip():
             QMessageBox.warning(self, "Input Error", "Prompt name cannot be empty.")


    def delete_selected_prompt(self):
        selected_item = self.prompts_list_widget.currentItem()
        if not selected_item or selected_item.text() == "No prompts defined yet.":
            QMessageBox.warning(self, "Selection Error", "Please select a prompt to delete.")
            return

        prompt_id = selected_item.data(Qt.UserRole)
        if prompt_id is None :
            QMessageBox.critical(self, "Error", "Selected item has no ID. Cannot delete.")
            return

        prompt_name_display = selected_item.text().split(':')[0] # Get name for confirmation

        reply = QMessageBox.question(self, "Delete Prompt", f"Are you sure you want to delete the prompt '{prompt_name_display}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                deleted = delete_user_prompt(self.db_session, prompt_id=prompt_id)
                if deleted:
                    self.load_prompts()
                    QMessageBox.information(self, "Prompt Deleted", f"Prompt '{prompt_name_display}' deleted successfully.")
                else:
                    QMessageBox.warning(self, "Delete Error", "Prompt not found or could not be deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Delete Prompt Error", f"Failed to delete prompt: {e}")
                logging.error(f"Error deleting prompt_id {prompt_id}: {e}", exc_info=True)

    def closeEvent(self, event):
        """Ensure database session is closed when the widget is closed."""
        if self.db_session:
            self.db_session.close()
            logging.info("BotpressIntegrationUI: Database session closed.")
        super().closeEvent(event)


if __name__ == '__main__':
    # This is for testing the UI component independently
    # For real use, it will be instantiated by main_window.py
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    # Mock current_user_id for testing
    test_user_id = "test_dev_user_001"

    # Import UserPrompt for testing prompt retrieval
    from .models import UserPrompt

    main_window = QWidget() # Dummy parent for testing if needed
    window = BotpressIntegrationUI(parent=main_window, current_user_id=test_user_id)
    window.setGeometry(100, 100, 700, 800) # Set a reasonable size for testing
    window.show()

    # Example of how to run app.exec_() only if it's the main instance
    # This helps avoid issues if this __main__ block is imported elsewhere.
    if app is QApplication.instance() and app.applicationName() == '': # A bit of a heuristic
        try:
            sys.exit(app.exec_())
        except SystemExit:
            logging.info("Closing BotpressIntegrationUI test window.")
            if window.db_session: # Ensure session is closed on exit
                window.db_session.close()
                logging.info("Test instance: Database session closed.")
