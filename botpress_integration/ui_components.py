import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QGroupBox, QMessageBox, QListWidget, QInputDialog,
    QListWidgetItem, QSplitter, QScrollArea, QSystemTrayIcon, QStyle
)
from PyQt5.QtGui import QIcon # Added for QSystemTrayIcon
from PyQt5.QtCore import Qt, QItemSelectionModel, QTimer, QFile, QUrl # Added QTimer, QFile, QUrl
# Optional for sound:
# from PyQt5.QtMultimedia import QSoundEffect

import json
from datetime import datetime
# Project specific imports - adjust path if necessary
from .api_client import BotpressClient, BotpressAPIError
from .crud import (
    get_botpress_settings, create_or_update_botpress_settings,
    get_prompts_for_user, create_user_prompt, update_user_prompt, delete_user_prompt,
    get_or_create_conversation, add_message, get_messages_for_conversation,
    update_conversation_timestamp, get_conversation_by_botpress_id,
    count_unread_bot_messages, has_unread_bot_messages, mark_messages_as_read # Added new crud functions
)
from .models import SessionLocal, create_db_and_tables, UserPrompt, Conversation, Message
from sqlalchemy.exc import SQLAlchemyError

# Setup basic logging if not already configured by the main application
# This is good practice for module independence.
# In a larger app, the main entry point would usually configure logging.
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Constants for QListWidgetItem data roles
CONVO_ID_ROLE = Qt.UserRole
BP_CONVO_ID_ROLE = Qt.UserRole + 1
IS_UNREAD_ROLE = Qt.UserRole + 2


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
        self.db_session = None
        self.current_settings_id = None
        self.current_db_conversation_id = None
        self.current_botpress_conversation_id = "default"
        self.has_unread_bot_messages = False # For polling state

        self.notification_timer = QTimer(self)
        self.notification_timer.timeout.connect(self.check_for_new_messages)

        # Initialize QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = "icons/logo.svg" # Consider making this configurable or part of resources
        if QFile.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            standard_icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation) # Fallback icon
            self.tray_icon.setIcon(standard_icon)
            self.logger.warning(f"Custom tray icon not found at {icon_path}, using standard icon.")

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()
            self.tray_icon.activated.connect(self.handle_tray_icon_activated)
            self.logger.info("System tray icon initialized and shown.")
        else:
            self.logger.warning("System tray not available on this system.")
            # self.tray_icon will exist but won't be shown. Methods using it should check isVisible().

        # Optional Sound Setup (ensure sound file exists or handle gracefully)
        # self.notification_sound = QSoundEffect(self)
        # sound_file_path = "assets/notification.wav"
        # if QFile.exists(sound_file_path):
        #     self.notification_sound.setSource(QUrl.fromLocalFile(sound_file_path))
        # else:
        #     self.logger.warning(f"Notification sound file not found at {sound_file_path}")


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
        top_level_layout = QVBoxLayout(self) # This will be the actual main layout for the QWidget

        # Main application layout will be a QHBoxLayout inside a QSplitter for resizable areas
        main_splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel: Conversations List ---
        conversations_group = QGroupBox("Recent Conversations")
        conversations_panel_layout = QVBoxLayout() # Layout for the group box
        self.conversations_list_widget = QListWidget()
        self.conversations_list_widget.currentItemChanged.connect(self.handle_conversation_selected)
        conversations_panel_layout.addWidget(self.conversations_list_widget)
        conversations_group.setLayout(conversations_panel_layout)
        main_splitter.addWidget(conversations_group)

        # --- Right Panel: Main Chat and Settings Area ---
        chat_and_settings_widget = QWidget()
        right_panel_layout = QVBoxLayout(chat_and_settings_widget)

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

        api_layout.addWidget(QLabel("Botpress Base URL (leave empty for default cloud):"))
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.botpress.cloud/v1/")
        api_layout.addWidget(self.base_url_input)

        config_buttons_layout = QHBoxLayout()
        self.load_settings_button = QPushButton("Load Settings")
        self.load_settings_button.clicked.connect(self.load_settings)
        config_buttons_layout.addWidget(self.load_settings_button)

        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self.save_settings)
        config_buttons_layout.addWidget(self.save_settings_button)
        api_layout.addLayout(config_buttons_layout)

        api_group.setLayout(api_layout)
        right_panel_layout.addWidget(api_group)

        # Conversation Display (Refactored with QScrollArea)
        conversation_group = QGroupBox("Conversation")
        conversation_group_layout = QVBoxLayout(conversation_group) # Layout for the GroupBox

        self.conversation_scroll_area = QScrollArea()
        self.conversation_scroll_area.setWidgetResizable(True)

        self.conversation_widget = QWidget() # This widget will contain the messages
        self.conversation_layout = QVBoxLayout(self.conversation_widget) # Add messages to this layout
        self.conversation_layout.setAlignment(Qt.AlignTop) # Messages stack from top

        self.conversation_scroll_area.setWidget(self.conversation_widget)
        conversation_group_layout.addWidget(self.conversation_scroll_area)
        right_panel_layout.addWidget(conversation_group)

        # Message Input
        message_input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self.handle_send_message) # Send on Enter
        message_input_layout.addWidget(self.message_input)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send_message)
        message_input_layout.addWidget(self.send_button)
        right_panel_layout.addLayout(message_input_layout)

        # Prompts Management
        prompts_group = QGroupBox("Prompts Management")
        prompts_main_layout = QVBoxLayout()
        self.prompts_list_widget = QListWidget()
        self.prompts_list_widget.itemDoubleClicked.connect(self.edit_selected_prompt)
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
        right_panel_layout.addWidget(prompts_group)

        main_splitter.addWidget(chat_and_settings_widget)
        main_splitter.setStretchFactor(0, 1) # Conversation list less space
        main_splitter.setStretchFactor(1, 3) # Chat area more space

        top_level_layout.addWidget(main_splitter)
        # self.setLayout(top_level_layout) # Already set by QVBoxLayout(self)

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
                stored_base_url = settings.base_url
                self.base_url_input.setText(stored_base_url if stored_base_url else "https://api.botpress.cloud/v1/")
                self.current_settings_id = settings.id
                self.logger.info(f"Settings found for user {self.current_user_id}. Settings ID: {self.current_settings_id}, Base URL: {stored_base_url}")

                try:
                    api_url_to_use = stored_base_url if stored_base_url else "https://api.botpress.cloud/v1/"
                    self.botpress_client = BotpressClient(api_key=settings.api_key, bot_id=settings.bot_id, base_url=api_url_to_use)
                    self.clear_conversation_display()
                    self.add_message_to_display("system", f"API Client initialized (URL: {api_url_to_use}).", datetime.now())

                    # Determine a default/initial Botpress conversation ID.
                    initial_bp_conversation_id = f"{settings.bot_id}_main_chat"

                    db_conversation = get_or_create_conversation(
                        self.db_session,
                        botpress_conversation_id=initial_bp_conversation_id
                    )
                    self.current_db_conversation_id = db_conversation.id
                    self.current_botpress_conversation_id = db_conversation.botpress_conversation_id

                    self.logger.info(f"Default/Initial local DB conversation set: ID={self.current_db_conversation_id}, BP_ID='{self.current_botpress_conversation_id}'")
                    self.add_message_to_display("system", f"Default Botpress Conversation ID: {self.current_botpress_conversation_id}", datetime.now())

                    self.load_prompts()
                    self.load_and_display_recent_conversations() # This will also trigger selection and history load

                    self.notification_timer.start(15000) # Start polling
                    self.check_for_new_messages() # Initial check

                except SQLAlchemyError as dbe:
                    self.logger.error(f"Database error setting up conversation: {dbe}", exc_info=True)
                    QMessageBox.critical(self, "DB Conversation Error", f"Failed to setup local conversation: {dbe}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Botpress client or setup conversation: {e}", exc_info=True)
                    QMessageBox.critical(self, "API Client/Conversation Error", f"Failed to initialize Botpress client or setup conversation: {e}")
                    self.botpress_client = None
                    self.current_db_conversation_id = None
                    self.notification_timer.stop()
            else:
                self.logger.info(f"No settings found for user {self.current_user_id}. Clearing fields.")
                QMessageBox.information(self, "No Settings", "No API settings found for this user. Please configure.")
                self.api_key_input.clear()
                self.bot_id_input.clear()
                self.base_url_input.setText("https://api.botpress.cloud/v1/")
                self.botpress_client = None
                self.current_settings_id = None
                self.current_db_conversation_id = None
                self.current_botpress_conversation_id = "default"
                self.prompts_list_widget.clear()
                self.conversations_list_widget.clear()
                self.clear_conversation_display()
                self.notification_timer.stop()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error while loading settings for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Error loading settings: {e}. Check logs.")
            self.botpress_client = None
            self.current_db_conversation_id = None
            self.notification_timer.stop()
        except Exception as e:
            self.logger.error(f"Unexpected error while loading settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {e}. Check logs.")
            self.botpress_client = None
            self.current_db_conversation_id = None
            self.notification_timer.stop()


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
        input_base_url = self.base_url_input.text().strip()

        if not api_key or not bot_id:
            QMessageBox.warning(self, "Input Error", "API Key and Bot ID cannot be empty.")
            return

        base_url_to_save = input_base_url if input_base_url else None # Save None if field is empty

        self.logger.info(f"Saving settings for user_id: {self.current_user_id} with base_url: {base_url_to_save}")
        try:
            settings = create_or_update_botpress_settings(
                self.db_session,
                user_id=self.current_user_id,
                api_key=api_key,
                bot_id=bot_id,
                base_url=base_url_to_save
            )
            self.current_settings_id = settings.id

            api_url_to_use = input_base_url if input_base_url else "https://api.botpress.cloud/v1/"
            self.botpress_client = BotpressClient(api_key=api_key, bot_id=bot_id, base_url=api_url_to_use)

            QMessageBox.information(self, "Settings Saved", "API settings saved and client re-initialized.")
            self.add_message_to_display("system", f"API Client re-initialized (URL: {api_url_to_use}).", datetime.now())
            self.logger.info(f"Settings saved successfully for user {self.current_user_id}. Settings ID: {self.current_settings_id}, Base URL used: {api_url_to_use}")
            self.load_prompts()
            self.load_and_display_recent_conversations()
            self.notification_timer.start(15000) # Restart polling with new settings
            self.check_for_new_messages()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error saving settings for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to save settings due to database error: {e}. Check logs.")
            self.botpress_client = None
            self.notification_timer.stop()
        except Exception as e:
            self.logger.error(f"Error saving settings or initializing client for user {self.current_user_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}. Check logs.")
            self.botpress_client = None
            self.notification_timer.stop()


    def handle_send_message(self):
        self.logger.debug("handle_send_message called.")
        if not self.botpress_client or not self.db_session or not self.current_db_conversation_id:
            QMessageBox.warning(self, "Client/DB Not Ready",
                                "Botpress client, DB session, or active conversation not properly initialized. "
                                "Please check API settings and load them.")
            self.logger.warning(f"handle_send_message: Client/DB/Conversation not ready. Client: {self.botpress_client}, DB: {self.db_session}, DBConvID: {self.current_db_conversation_id}")
            return

        user_message_text = self.message_input.text().strip()
        if not user_message_text:
            return

        # 1. Save user message to local DB and display
        try:
            timestamp = datetime.now()
            # Don't save user message to DB yet, do it after successful API call or based on exact requirements
            # For now, display immediately, save after API success or if API fails but we still want to log user part.
            self.add_message_to_display(sender_type='user', text=user_message_text, timestamp=timestamp)
            self.logger.info(f"User attempting to send message: {user_message_text}")
        except Exception as e: # Should not happen with simple display, but good for robustness
            self.logger.error(f"Error displaying user message: {e}", exc_info=True)
            QMessageBox.critical(self, "Display Error", f"Failed to display your message: {e}")
            return

        # 2. Send message via API client
        try:
            # Save user message to DB before sending
            db_user_message = add_message(self.db_session,
                                          conversation_id=self.current_db_conversation_id,
                                          sender_type='user',
                                          content=user_message_text,
                                          timestamp=timestamp) # Use same timestamp as display
            self.logger.info(f"User message '{user_message_text}' saved to DB with ID {db_user_message.id}")

            response_data = self.botpress_client.send_message(user_message_text, conversation_id=self.current_botpress_conversation_id)
            self.logger.info(f"Botpress API response: {response_data}")

            bot_messages_in_response = []
            # Botpress might send an array of messages in response to one user message
            # Example: {"responses": [{"type": "text", "text": "Hi!", "suggestions": [...]}, {"type": "typing", "value": true}]}
            # We are interested in messages of type "text" or that have a "text" field.
            # The key might be "message", "messages", or "responses". Adjust based on actual API.
            # For this example, let's assume the structure from the task description for a single message:
            # response_data = {"id": "msg_api_123", "conversationId": "conv_xyz", "text": "...", "suggestions": [...]}
            # Or if it's a list under a key, e.g. response_data["messages"]

            potential_message_holders = []
            if isinstance(response_data, list): # If the root is a list of messages
                potential_message_holders = response_data
            elif isinstance(response_data, dict):
                if "message" in response_data and isinstance(response_data["message"], dict):
                    potential_message_holders.append(response_data["message"])
                elif "messages" in response_data and isinstance(response_data["messages"], list):
                    potential_message_holders.extend(response_data["messages"])
                elif "responses" in response_data and isinstance(response_data["responses"], list): # Another common pattern
                    potential_message_holders.extend(response_data["responses"])
                elif "text" in response_data : # If the root object is a single message
                     potential_message_holders.append(response_data)


            if not potential_message_holders:
                 self.logger.warning(f"No processable message objects found in Botpress response: {response_data}")
                 self.add_message_to_display("system", f"Bot response structure not recognized or empty: {str(response_data)[:100]}", datetime.now())

            for bot_msg_payload in potential_message_holders:
                # Skip if not a message type we can display (e.g. typing indicators)
                if bot_msg_payload.get("type") not in [None, "text", "message"] and not bot_msg_payload.get("text"):
                    self.logger.info(f"Skipping non-text/non-message payload: {bot_msg_payload.get('type')}")
                    continue

                bot_reply_text = bot_msg_payload.get("text", "Bot sent an empty message.")
                bot_message_api_id = bot_msg_payload.get("id")
                response_conversation_id = bot_msg_payload.get("conversationId")
                api_suggestions_list = bot_msg_payload.get("suggestions")
                suggestions_json_to_save = None
                if api_suggestions_list and isinstance(api_suggestions_list, list):
                    try:
                        suggestions_json_to_save = json.dumps(api_suggestions_list)
                    except TypeError:
                        self.logger.error("Failed to serialize suggestions to JSON.", exc_info=True)

                if response_conversation_id and response_conversation_id != self.current_botpress_conversation_id:
                    self.logger.info(f"Botpress conversation ID changed from '{self.current_botpress_conversation_id}' to '{response_conversation_id}'. Updating.")
                    self.current_botpress_conversation_id = response_conversation_id
                    try:
                        local_conv = self.db_session.query(Conversation).filter(Conversation.id == self.current_db_conversation_id).first()
                        if local_conv:
                            local_conv.botpress_conversation_id = response_conversation_id
                            self.db_session.commit()
                            self.logger.info(f"Updated local DB conversation {self.current_db_conversation_id} with new BP_ID {response_conversation_id}")
                    except SQLAlchemyError as e:
                        self.logger.error(f"DB error updating botpress_conversation_id for local conv {self.current_db_conversation_id}: {e}", exc_info=True)

                bot_timestamp = datetime.now()
                add_message(self.db_session,
                            conversation_id=self.current_db_conversation_id,
                            sender_type='bot',
                            content=bot_reply_text,
                            timestamp=bot_timestamp,
                            botpress_message_id=bot_message_api_id,
                            suggestions=suggestions_json_to_save)
                self.add_message_to_display(sender_type='bot', text=bot_reply_text, timestamp=bot_timestamp, suggestions=api_suggestions_list)
                self.logger.info(f"Bot reply '{bot_reply_text}' (API ID: {bot_message_api_id}) saved to DB for conv_id {self.current_db_conversation_id}")

        except BotpressAPIError as e:
            self.logger.error(f"Botpress API error: {e}", exc_info=True)
            QMessageBox.critical(self, "API Error", f"Botpress API error: {e}")
            self.add_message_to_display("system", f"API Error: {e}", datetime.now())
        except Exception as e:
            self.logger.error(f"Error sending/receiving: {e}", exc_info=True)
            QMessageBox.critical(self, "Processing Error", f"Error during send/receive: {e}")
            self.add_message_to_display("system", f"Processing Error: {e}", datetime.now())
        finally:
            self.message_input.clear()
            # Auto-scroll handled by add_message_to_display
            self.load_and_display_recent_conversations()
            self.restore_conversation_list_selection(self.current_db_conversation_id)


    def load_conversation_history(self):
        self.logger.debug(f"load_conversation_history for DB ID: {self.current_db_conversation_id}, BP ID: {self.current_botpress_conversation_id}")
        self.clear_conversation_display()
        if not self.db_session:
            self.logger.error("load_conversation_history: db_session is None.")
            self.add_message_to_display("system", "Database session not available.", datetime.now())
            return

        if not self.current_db_conversation_id:
            self.logger.info("load_conversation_history: No active local DB conversation.")
            self.add_message_to_display("system", "Select a conversation to view its history.", datetime.now())
            return

        self.add_message_to_display("system", f"Loading history for DB ID: {self.current_db_conversation_id} (BP ID: {self.current_botpress_conversation_id})...", datetime.now())
        try:
            messages = get_messages_for_conversation(self.db_session,
                                                     conversation_id=self.current_db_conversation_id,
                                                     limit=100)
            if not messages:
                self.add_message_to_display("system", "No messages in this conversation yet.", datetime.now())
            else:
                for msg in messages:
                    suggestions_list = None
                    if msg.suggestions:
                        try:
                            suggestions_list = json.loads(msg.suggestions)
                        except json.JSONDecodeError:
                            self.logger.error(f"Failed to parse suggestions from DB for msg ID {msg.id}: {msg.suggestions}", exc_info=True)
                    self.add_message_to_display(sender_type=msg.sender_type,
                                                text=msg.content,
                                                timestamp=msg.timestamp,
                                                suggestions=suggestions_list)
            self.logger.info(f"Loaded {len(messages)} messages for conv_id {self.current_db_conversation_id}")

        except SQLAlchemyError as e:
            self.logger.error(f"DB error loading history for conv_id {self.current_db_conversation_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "DB Error", f"Error loading history: {e}")
            self.add_message_to_display("system", f"DB Error: {e}", datetime.now())
        except Exception as e:
            self.logger.error(f"Unexpected error loading history: {e}", exc_info=True)
            QMessageBox.critical(self, "History Error", f"Failed to load history: {e}")
            self.add_message_to_display("system", f"Error: {e}", datetime.now())

        # Auto-scroll handled by add_message_to_display

    def load_and_display_recent_conversations(self):
        self.logger.debug("Loading and displaying recent conversations.")
        if not self.db_session:
            self.logger.error("load_and_display_recent_conversations: db_session is None.")
            return

        current_selection_db_id = self.current_db_conversation_id # Preserve current selection

        self.conversations_list_widget.clear()
        try:
            recent_convos = crud.get_recent_conversations(self.db_session, limit=25)
            if not recent_convos:
                self.conversations_list_widget.addItem("No recent conversations found.")
                self.logger.info("No recent conversations found in DB.")
            else:
                for convo in recent_convos:
                    last_msg_time_str = convo.last_message_timestamp.strftime('%Y-%m-%d %H:%M') if convo.last_message_timestamp else 'Never'
                    display_text = f"{convo.botpress_conversation_id[:20]}... (Last: {last_msg_time_str})"

                    item = QListWidgetItem() # Create item first
                    item.setData(CONVO_ID_ROLE, convo.id)
                    item.setData(BP_CONVO_ID_ROLE, convo.botpress_conversation_id)

                    is_unread = crud.has_unread_bot_messages(self.db_session, convo.id)
                    self.update_conversation_item_style(item, is_unread, base_text=display_text) # Use helper

                    item.setToolTip(f"DB ID: {convo.id}\nBotpress ID: {convo.botpress_conversation_id}\nChannel: {convo.channel_type or 'N/A'}\nUser: {convo.user_identifier_on_channel or 'N/A'}\nStatus: {convo.status}")
                    self.conversations_list_widget.addItem(item)
                self.logger.info(f"Displayed {len(recent_convos)} recent conversations.")

            if current_selection_db_id:
                self.restore_conversation_list_selection(current_selection_db_id)
            elif self.conversations_list_widget.count() > 0:
                first_item = self.conversations_list_widget.item(0)
                if first_item and first_item.data(CONVO_ID_ROLE) is not None:
                    self.conversations_list_widget.setCurrentItem(first_item)
                else:
                    self.handle_conversation_selected(None, None)

        except SQLAlchemyError as e:
            self.logger.error(f"DB error loading recent conversations: {e}", exc_info=True)
            QMessageBox.critical(self, "DB Error", f"Failed to load recent conversations: {e}")
            self.conversations_list_widget.addItem("Error loading conversations.")

    def update_conversation_item_style(self, item: QListWidgetItem, is_unread: bool, base_text: Optional[str] = None):
        if not item: return
        font = item.font()

        # If base_text is not provided, try to get current text and strip previous markers
        current_text = base_text
        unread_marker = "[UNREAD] "
        if current_text is None:
            current_text = item.text()
            if current_text.startswith(unread_marker):
                current_text = current_text[len(unread_marker):]

        if is_unread:
            font.setBold(True)
            if not current_text.startswith(unread_marker): # Avoid double marking
                 item.setText(unread_marker + current_text)
            else: # Already has marker, just ensure text is correct
                 item.setText(unread_marker + current_text) # Use current_text which is stripped
        else:
            font.setBold(False)
            if current_text.startswith(unread_marker): # Remove marker
                item.setText(current_text[len(unread_marker):])
            else:
                item.setText(current_text) # Ensure it's the base text

        item.setFont(font)
        item.setData(IS_UNREAD_ROLE, is_unread)


    def handle_conversation_selected(self, current_item, previous_item):
        if not current_item or current_item.data(CONVO_ID_ROLE) is None:
            self.current_db_conversation_id = None
            self.current_botpress_conversation_id = "default"
            self.clear_conversation_display()
            self.add_message_to_display("system", "No conversation selected or conversation is empty.", datetime.now())
            self.logger.info("No conversation selected or placeholder item selected.")
            self.message_input.setEnabled(False)
            self.send_button.setEnabled(False)
            return

        db_id = current_item.data(CONVO_ID_ROLE)
        bp_convo_id = current_item.data(BP_CONVO_ID_ROLE)

        self.current_db_conversation_id = db_id
        self.current_botpress_conversation_id = bp_convo_id

        self.logger.info(f"Switched to conversation DB ID: {db_id}, Botpress ID: {bp_convo_id}")
        self.message_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.load_conversation_history() # This will display messages

        # Mark messages as read for this conversation and update UI item
        if self.db_session and self.current_db_conversation_id is not None:
            try:
                updated_count = crud.mark_messages_as_read(self.db_session, conversation_id=self.current_db_conversation_id)
                if updated_count > 0:
                    self.logger.info(f"Marked {updated_count} messages as read in conversation {self.current_db_conversation_id}.")
                    self.update_conversation_item_style(current_item, False) # Update style to not bold
                    # Potentially trigger a global unread count check for notifications, though this is on selection.
                    self.check_for_new_messages()
            except SQLAlchemyError as e:
                self.logger.error(f"DB error marking messages as read for conv {self.current_db_conversation_id}: {e}", exc_info=True)


    def restore_conversation_list_selection(self, db_conv_id_to_select):
        if db_conv_id_to_select is None:
            if self.conversations_list_widget.count() > 0:
                first_item = self.conversations_list_widget.item(0)
                if first_item and first_item.data(CONVO_ID_ROLE) is not None:
                     self.conversations_list_widget.setCurrentItem(first_item)
                else:
                    self.handle_conversation_selected(None, None)
            return

        for i in range(self.conversations_list_widget.count()):
            item = self.conversations_list_widget.item(i)
            if item and item.data(CONVO_ID_ROLE) == db_conv_id_to_select:
                self.conversations_list_widget.setCurrentItem(item)
                self.logger.debug(f"Restored selection in list to conversation DB ID: {db_conv_id_to_select}")
                return
        self.logger.warning(f"Could not find conversation with DB ID {db_conv_id_to_select} in list to restore selection.")
        if self.conversations_list_widget.count() > 0:
            first_item = self.conversations_list_widget.item(0)
            if first_item and first_item.data(CONVO_ID_ROLE) is not None:
                self.conversations_list_widget.setCurrentItem(first_item)
            else:
                self.handle_conversation_selected(None, None)

    def add_message_to_display(self, sender_type: str, text: str, timestamp: datetime, suggestions: Optional[list] = None):
        """Adds a message widget to the conversation_layout with optional suggestion buttons."""

        message_widget_container = QWidget() # Main container for this message entry
        message_widget_layout = QVBoxLayout(message_widget_container)
        message_widget_layout.setContentsMargins(5, 5, 5, 5) # Small margins around each message entry

        # Create a QHBoxLayout to handle alignment (user right, bot left)
        row_layout = QHBoxLayout()

        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        # Using QLabel with RichText for basic formatting like bold.
        # For more complex styling (bubbles), custom painting or more complex HTML/CSS would be needed.
        if sender_type.lower() == "system":
             label_text = f"<i>System ({timestamp_str}): {text}</i>"
        else:
            label_text = f"<b>{sender_type.capitalize()}</b> ({timestamp_str}):<br>{text}"

        message_label = QLabel(label_text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setStyleSheet("QLabel { padding: 5px; }") # Basic padding

        if sender_type.lower() == 'user':
            message_label.setStyleSheet("QLabel { background-color: #DCF8C6; border-radius: 5px; padding: 5px; }")
            row_layout.addStretch()
            row_layout.addWidget(message_label)
        elif sender_type.lower() == 'bot':
            message_label.setStyleSheet("QLabel { background-color: #ECECEC; border-radius: 5px; padding: 5px; }")
            row_layout.addWidget(message_label)
            row_layout.addStretch()
        else: # System messages span full width or are left aligned
            row_layout.addWidget(message_label)
            # row_layout.addStretch() # Optional: if system messages should also be pushed left

        message_widget_layout.addLayout(row_layout)

        if suggestions and sender_type.lower() == 'bot': # Only show suggestions for bot messages
            suggestions_container = QWidget()
            suggestions_layout = QHBoxLayout(suggestions_container)
            suggestions_layout.setAlignment(Qt.AlignLeft)
            suggestions_layout.setContentsMargins(0, 5, 0, 0) # Margin above suggestions

            for sugg in suggestions:
                if isinstance(sugg, dict) and 'title' in sugg and 'payload' in sugg:
                    button = QPushButton(sugg['title'])
                    button.clicked.connect(lambda checked, p=sugg['payload'], mwc=message_widget_container: self.handle_suggestion_clicked(p, mwc))
                    button.setCursor(Qt.PointingHandCursor)
                    button.setStyleSheet("QPushButton { margin-right: 5px; }")
                    suggestions_layout.addWidget(button)
                else:
                    self.logger.warning(f"Malformed suggestion item: {sugg}")

            # Add a stretch to keep buttons packed left if there are few
            suggestions_layout.addStretch()
            message_widget_layout.addWidget(suggestions_container)

        self.conversation_layout.addWidget(message_widget_container)

        # Ensure scroll to bottom
        QTimer.singleShot(0, lambda: self.conversation_scroll_area.verticalScrollBar().setValue(self.conversation_scroll_area.verticalScrollBar().maximum()))

    def handle_suggestion_clicked(self, payload: str, message_widget_container_with_suggestions: QWidget):
        """Handles click on a suggestion button."""
        self.logger.info(f"Suggestion clicked with payload: '{payload}'")
        self.message_input.setText(payload)
        self.handle_send_message() # Auto-send the message

        # Optional: Remove suggestion buttons from the specific message widget after click
        # Find the suggestions_container within message_widget_container_with_suggestions and hide/delete it
        # This assumes suggestions_container is the last widget added to message_widget_layout
        message_widget_layout = message_widget_container_with_suggestions.layout()
        if message_widget_layout and message_widget_layout.count() > 1: # Check if there's more than just the text label's layout
            # Iterate backwards to find the suggestions_container, assuming it's the last one
            # This is a bit fragile; a more robust way would be to name the widget.
            potential_suggestions_widget = message_widget_layout.itemAt(message_widget_layout.count() -1).widget()
            if potential_suggestions_widget and isinstance(potential_suggestions_widget.layout(), QHBoxLayout): # Heuristic
                potential_suggestions_widget.hide() # Hide it
                # potential_suggestions_widget.deleteLater() # Or delete it
                self.logger.debug("Hid suggestion buttons after click.")


    def clear_conversation_display(self):
        """Clears all messages from the conversation display area."""
        self.logger.debug("Clearing conversation display.")
        while self.conversation_layout.count():
            child = self.conversation_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # Add a system message or leave blank
        # self.add_message_to_display("system", "Conversation cleared.", datetime.now())

    def check_for_new_messages(self):
        if not self.db_session or not self.botpress_client:
            return

        try:
            unread_count_globally = crud.count_unread_bot_messages(self.db_session)
            if unread_count_globally > 0:
                if not self.has_unread_bot_messages:
                    self.logger.info(f"Polling: Found {unread_count_globally} new unread messages from non-user senders globally.")
                    self.trigger_notifications(unread_count_globally)
                self.has_unread_bot_messages = True
                # Refresh conversation list to update bolding if any conversation's unread status changed
                # This is important if a message arrived in a non-active conversation
                self.load_and_display_recent_conversations()
            else:
                if self.has_unread_bot_messages:
                    self.logger.info("Polling: All bot messages now read globally.")
                    # Refresh list to remove any bolding if it was the last unread
                    self.load_and_display_recent_conversations()
                self.has_unread_bot_messages = False
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during new message check: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Unexpected error during new message check: {e}", exc_info=True)

    def trigger_notifications(self, count):
        """Placeholder for actual notification logic."""
        if not self.tray_icon.isVisible() and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show() # Attempt to show it if it was hidden or system tray just became available

        if self.tray_icon.isVisible(): # Only show message if tray icon is actually working
            title = "New Botpress Message" if count == 1 else f"{count} New Botpress Messages"
            message_body = f"You have {count} unread message(s) in the Botpress integration."
            self.tray_icon.showMessage(title, message_body, QSystemTrayIcon.Information, 5000) # Show for 5 seconds
            self.logger.info(f"Desktop notification shown for {count} messages.")

            # Optional Sound Play
            # if hasattr(self, 'notification_sound') and self.notification_sound.isLoaded():
            #     self.notification_sound.play()
            #     self.logger.info("Played notification sound.")
        else:
            self.logger.warning("Tried to trigger notification, but tray icon is not visible/available.")
            # Fallback: Maybe a less intrusive in-app notification if tray is not available
            # For example, update a status bar or add a message to the system messages area.
            # self.add_message_to_display("system", f"You have {count} new unread non-user message(s).", datetime.now())


    def handle_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: # Typically a left click
            self.logger.info("Tray icon activated by trigger (click). Attempting to show/activate window.")
            parent_window = self.window()
            if parent_window:
                if parent_window.isMinimized():
                    parent_window.showNormal()
                parent_window.raise_()
                parent_window.activateWindow()
        elif reason == QSystemTrayIcon.Context: # Right click, could show a context menu
            self.logger.info("Tray icon context menu requested (right-click). (Menu not implemented)")
            # Here you could implement self.tray_icon.setContextMenu(your_menu)


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
        """Ensure resources are cleaned up when the widget is closed."""
        if self.notification_timer:
            self.notification_timer.stop()
            self.logger.info("Notification timer stopped.")

        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.hide()
            self.logger.info("System tray icon hidden.")
            # For explicit cleanup if self is not its parent or to be very sure:
            # del self.tray_icon
            # self.tray_icon = None

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
