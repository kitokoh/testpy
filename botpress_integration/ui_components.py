import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QGroupBox, QMessageBox, QListWidget, QInputDialog,
    QListWidgetItem, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QDialogButtonBox, QTextEdit as QTextEdit_Dialog, # Renamed to avoid conflict
    QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from datetime import datetime
import asyncio
from typing import Optional, Dict, Any, List

from .api_client import BotpressClient, BotpressAPIError
from .connectors.whatsapp_connector import WhatsAppConnector, WhatsAppConnectorConfig
from .crud import (
    get_botpress_settings, create_or_update_botpress_settings,
    get_prompts_for_user, create_user_prompt, update_user_prompt, delete_user_prompt, get_prompt_by_id,
    get_whatsapp_settings, create_or_update_whatsapp_settings
)
from .models import SessionLocal, create_db_and_tables, UserPrompt, WhatsAppConnectorSettings
from sqlalchemy.exc import SQLAlchemyError

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class PromptEditDialog(QDialog):
    def __init__(self, current_prompt_data: Optional[Dict] = None, parent=None, db_session=None, settings_id=None, editing_prompt_id=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Prompt")
        self.logger = logging.getLogger(__name__)
        self.current_prompt_data = current_prompt_data
        self.db_session = db_session
        self.settings_id = settings_id
        self.editing_prompt_id = editing_prompt_id

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Prompt Name:"))
        self.prompt_name_input = QLineEdit()
        if current_prompt_data: self.prompt_name_input.setText(current_prompt_data.get("name", ""))
        self.prompt_name_input.setToolTip("Unique name for this prompt.")
        layout.addWidget(self.prompt_name_input)

        layout.addWidget(QLabel("Prompt Text:"))
        self.prompt_text_input = QTextEdit_Dialog()
        if current_prompt_data: self.prompt_text_input.setPlainText(current_prompt_data.get("text", ""))
        self.prompt_text_input.setToolTip("The full text of the prompt. You can use placeholders like {variable_name}.")
        layout.addWidget(self.prompt_text_input)

        layout.addWidget(QLabel("Category (select existing or type new):"))
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(False)
        self.category_combo.setToolTip("Select an existing category.")
        self.category_line_edit = QLineEdit()
        self.category_line_edit.setToolTip("Or type a new category name here. Selected category will override typed text if different.")

        self._populate_categories_for_dialog()

        if current_prompt_data and current_prompt_data.get("category"):
            cat_text = current_prompt_data["category"]
            idx = self.category_combo.findText(cat_text, Qt.MatchFixedString) # Exact match
            if idx != -1:
                self.category_combo.setCurrentIndex(idx)
            self.category_line_edit.setText(cat_text)

        self.category_combo.currentIndexChanged.connect(self._category_combo_selected)
        category_layout.addWidget(self.category_combo)
        category_layout.addWidget(self.category_line_edit)
        layout.addLayout(category_layout)

        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        if current_prompt_data: self.tags_input.setText(current_prompt_data.get("tags", ""))
        self.tags_input.setToolTip("Enter comma-separated tags for easier searching.")
        layout.addWidget(self.tags_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setMinimumWidth(450)
        self.setMinimumHeight(400)

    def _populate_categories_for_dialog(self):
        self.category_combo.clear()
        self.category_combo.addItem("", "") # Add an empty item for "no category" or new
        if self.db_session and self.settings_id:
            try:
                distinct_categories = self.db_session.query(UserPrompt.category).\
                                      filter(UserPrompt.settings_id == self.settings_id, UserPrompt.category != None, UserPrompt.category != "").\
                                      distinct().order_by(UserPrompt.category).all()
                categories = [cat[0] for cat in distinct_categories if cat[0]]
                for cat_name in categories:
                    self.category_combo.addItem(cat_name, cat_name)
            except Exception as e:
                self.logger.error(f"Error populating categories in dialog: {e}", exc_info=True)

    def _category_combo_selected(self, index):
        selected_text = self.category_combo.itemText(index)
        self.category_line_edit.setText(selected_text)

    def validate_and_accept(self):
        name = self.prompt_name_input.text().strip()
        text = self.prompt_text_input.toPlainText().strip()

        if not name: QMessageBox.warning(self, "Input Error", "Prompt name cannot be empty."); return
        if not text: QMessageBox.warning(self, "Input Error", "Prompt text cannot be empty."); return

        if self.db_session and self.settings_id:
            query = self.db_session.query(UserPrompt.id).filter(
                UserPrompt.settings_id == self.settings_id,
                UserPrompt.prompt_name == name
            )
            if self.editing_prompt_id: query = query.filter(UserPrompt.id != self.editing_prompt_id)

            existing_prompt_id = query.scalar() # Use scalar to get a single value or None
            if existing_prompt_id is not None:
                QMessageBox.warning(self, "Input Error", f"A prompt with the name '{name}' already exists.")
                return
        super().accept()

    def get_data(self) -> Optional[Dict]:
        # Assumes validation has passed in accept_data
        name = self.prompt_name_input.text().strip()
        text = self.prompt_text_input.toPlainText().strip()
        category = self.category_line_edit.text().strip()
        tags = self.tags_input.text().strip()
        return {"name": name, "text": text, "category": category or None, "tags": tags or None}


class BotpressIntegrationUI(QWidget):
    def __init__(self, parent=None, current_user_id=None):
        super().__init__(parent)
        self.setWindowTitle('Botpress Integration & Connectors')
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing BotpressIntegrationUI for user_id: {current_user_id}")

        self.current_user_id = current_user_id
        if not self.current_user_id:
            self.logger.error("BotpressIntegrationUI initialized without a current_user_id!")

        self.botpress_client: Optional[BotpressClient] = None
        self.db_session = None
        self.current_settings_id: Optional[int] = None
        self.displayed_message_identifiers = set()

        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self.check_for_new_messages)
        self.polling_interval_ms = 15000

        self.whatsapp_connector: Optional[WhatsAppConnector] = None
        self.actual_whatsapp_api_token_loaded: Optional[str] = None
        self.whatsapp_api_token_is_hidden = True

        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.logger.info("No asyncio event loop in current thread, creating a new one.")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.whatsapp_status_label = QLabel("WhatsApp Status: Not Configured")
        self.general_status_label = QLabel("Status: Idle") # General status bar

        try:
            create_db_and_tables()
            self.db_session = SessionLocal()
            self.logger.info("Database session created and tables ensured.")
        except SQLAlchemyError as e:
            self.logger.critical(f"Failed to connect to database or create tables: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error",
                                 "Could not connect to the database. Module features will be severely limited. "
                                 "Please check logs for details.")

        self.init_ui()

        if self.db_session:
            self.load_settings()
        else:
            self.logger.warning("Skipping initial load_settings due to DB session failure.")
            if hasattr(self, 'save_settings_button'): self.save_settings_button.setEnabled(False)
            if hasattr(self, 'load_settings_button'): self.load_settings_button.setEnabled(False)
            if hasattr(self, 'add_prompt_button'): self.add_prompt_button.setEnabled(False)
            if hasattr(self, 'edit_prompt_button'): self.edit_prompt_button.setEnabled(False)
            if hasattr(self, 'delete_prompt_button'): self.delete_prompt_button.setEnabled(False)
            if hasattr(self, 'send_button'): self.send_button.setEnabled(False)
            if hasattr(self, 'message_input'): self.message_input.setEnabled(False)
            if hasattr(self, 'whatsapp_connector_group'): self.whatsapp_connector_group.setEnabled(False)
            if hasattr(self, 'prompts_group'): self.prompts_group.setEnabled(False)


    def init_ui(self):
        self.logger.debug("Initializing UI components.")
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget(); main_layout.addWidget(self.tabs)

        # --- Botpress Core Settings Tab ---
        self.botpress_core_tab = QWidget(); self.tabs.addTab(self.botpress_core_tab, "Botpress Core & Chat")
        core_tab_layout = QVBoxLayout(self.botpress_core_tab)

        # API Config Group
        api_group = QGroupBox("Botpress API Configuration"); api_layout = QVBoxLayout(api_group); core_tab_layout.addWidget(api_group)
        api_layout.addWidget(QLabel("API Key:")); self.api_key_input = QLineEdit(); self.api_key_input.setPlaceholderText("Enter new Botpress API Key"); self.api_key_input.setEchoMode(QLineEdit.Password); self.api_key_input_is_hidden = True; self.actual_api_key_loaded = None; api_layout.addWidget(self.api_key_input)
        api_key_controls_layout = QHBoxLayout(); self.toggle_api_key_button = QPushButton("Show API Key"); self.toggle_api_key_button.setCheckable(True); self.toggle_api_key_button.clicked.connect(self.toggle_api_key_visibility); self.toggle_api_key_button.setToolTip("Show/Hide the Botpress API Key."); api_key_controls_layout.addWidget(self.toggle_api_key_button)
        self.clear_api_key_button = QPushButton("Clear/Update API Key"); self.clear_api_key_button.clicked.connect(self.prepare_update_api_key); self.clear_api_key_button.setToolTip("Clear the field to enter a new API Key."); api_key_controls_layout.addWidget(self.clear_api_key_button); api_layout.addLayout(api_key_controls_layout)
        api_key_info_label = QLabel("<i>API Key is hidden. Click 'Clear/Update' to set a new key. Click 'Show' to temporarily view.</i>"); api_key_info_label.setWordWrap(True); api_layout.addWidget(api_key_info_label)
        api_layout.addWidget(QLabel("Bot ID:")); self.bot_id_input = QLineEdit(); self.bot_id_input.setPlaceholderText("Enter Botpress Bot ID"); self.bot_id_input.setToolTip("The ID of your Botpress bot."); api_layout.addWidget(self.bot_id_input)
        config_buttons_layout = QHBoxLayout(); self.load_settings_button = QPushButton("Load Settings"); self.load_settings_button.setToolTip("Load saved Botpress API settings."); self.load_settings_button.clicked.connect(self.load_settings); config_buttons_layout.addWidget(self.load_settings_button)
        self.save_settings_button = QPushButton("Save Settings"); self.save_settings_button.setToolTip("Save current Botpress API settings."); self.save_settings_button.clicked.connect(self.save_settings); config_buttons_layout.addWidget(self.save_settings_button); api_layout.addLayout(config_buttons_layout)

        # Conversation Display
        conversation_group = QGroupBox("Conversation with Botpress Bot"); conversation_layout = QVBoxLayout(conversation_group); self.conversation_display = QTextEdit(); self.conversation_display.setReadOnly(True); conversation_layout.addWidget(self.conversation_display); core_tab_layout.addWidget(conversation_group)

        # Message Input
        message_input_layout = QHBoxLayout(); self.message_input = QLineEdit(); self.message_input.setPlaceholderText("Type your message to Botpress..."); self.message_input.returnPressed.connect(self.initiate_send_message_from_ui); message_input_layout.addWidget(self.message_input)
        self.send_button = QPushButton("Send to Botpress"); self.send_button.setToolTip("Send the message to the configured Botpress bot."); self.send_button.clicked.connect(self.initiate_send_message_from_ui); message_input_layout.addWidget(self.send_button); core_tab_layout.addLayout(message_input_layout)

        # --- Prompts Tab ---
        self.prompts_tab = QWidget(); self.tabs.addTab(self.prompts_tab, "Prompt Management")
        prompts_page_layout = QVBoxLayout(self.prompts_tab)

        self.prompts_group = QGroupBox("User-Defined Prompts Management"); prompts_main_layout = QVBoxLayout(self.prompts_group); prompts_page_layout.addWidget(self.prompts_group)
        prompt_filter_layout = QHBoxLayout(); prompts_main_layout.addLayout(prompt_filter_layout)
        prompt_filter_layout.addWidget(QLabel("Search Prompts:")); self.prompt_search_input = QLineEdit(); self.prompt_search_input.setPlaceholderText("Search by name, category, tags, text..."); self.prompt_search_input.textChanged.connect(self.filter_prompts_display); self.prompt_search_input.setToolTip("Filter prompts based on any text match."); prompt_filter_layout.addWidget(self.prompt_search_input)
        prompt_filter_layout.addWidget(QLabel("Category:")); self.prompt_category_filter_combo = QComboBox(); self.prompt_category_filter_combo.addItem("All Categories", ""); self.prompt_category_filter_combo.currentIndexChanged.connect(self.filter_prompts_display); self.prompt_category_filter_combo.setToolTip("Filter prompts by category."); prompt_filter_layout.addWidget(self.prompt_category_filter_combo)

        self.prompts_table_widget = QTableWidget(); self.prompts_table_widget.setColumnCount(5); self.prompts_table_widget.setHorizontalHeaderLabels(["Name", "Category", "Tags", "Preview", "Last Updated"]); self.prompts_table_widget.setSelectionBehavior(QAbstractItemView.SelectRows); self.prompts_table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers); self.prompts_table_widget.doubleClicked.connect(self.edit_selected_prompt_from_table); self.prompts_table_widget.setToolTip("Double-click a prompt to edit.")
        header = self.prompts_table_widget.horizontalHeader(); header.setSectionResizeMode(0, QHeaderView.Interactive); header.setSectionResizeMode(1, QHeaderView.Interactive); header.setSectionResizeMode(2, QHeaderView.Interactive); header.setSectionResizeMode(3, QHeaderView.Stretch); header.setSectionResizeMode(4, QHeaderView.Interactive); header.resizeSection(0, 150); header.resizeSection(1, 100); header.resizeSection(2, 120); header.resizeSection(4, 120); prompts_main_layout.addWidget(self.prompts_table_widget)
        prompts_buttons_layout = QHBoxLayout(); self.add_prompt_button = QPushButton("Add New Prompt"); self.add_prompt_button.setToolTip("Add a new custom prompt."); self.add_prompt_button.clicked.connect(self.add_prompt); prompts_buttons_layout.addWidget(self.add_prompt_button)
        self.edit_prompt_button = QPushButton("Edit Selected Prompt"); self.edit_prompt_button.setToolTip("Edit the currently selected prompt in the table."); self.edit_prompt_button.clicked.connect(self.edit_selected_prompt_from_table); prompts_buttons_layout.addWidget(self.edit_prompt_button)
        self.delete_prompt_button = QPushButton("Delete Selected Prompt"); self.delete_prompt_button.setToolTip("Delete the currently selected prompt from the table."); self.delete_prompt_button.clicked.connect(self.delete_selected_prompt); prompts_buttons_layout.addWidget(self.delete_prompt_button); prompts_main_layout.addLayout(prompts_buttons_layout)

        # --- Platform Connectors Tab ---
        self.connectors_tab = QWidget(); self.tabs.addTab(self.connectors_tab, "Platform Connectors"); connectors_tab_layout = QVBoxLayout(self.connectors_tab)
        self.whatsapp_connector_group = QGroupBox("WhatsApp Connector Settings"); connectors_tab_layout.addWidget(self.whatsapp_connector_group); whatsapp_layout = QVBoxLayout(self.whatsapp_connector_group)
        self.enable_whatsapp_checkbox = QCheckBox("Enable WhatsApp Connector"); self.enable_whatsapp_checkbox.setToolTip("Enable or disable the WhatsApp integration."); whatsapp_layout.addWidget(self.enable_whatsapp_checkbox)
        whatsapp_layout.addWidget(QLabel("Phone Number ID:")); self.whatsapp_phone_number_id_input = QLineEdit(); self.whatsapp_phone_number_id_input.setPlaceholderText("Enter WhatsApp Phone Number ID"); self.whatsapp_phone_number_id_input.setToolTip("Your WhatsApp Business API Phone Number ID."); whatsapp_layout.addWidget(self.whatsapp_phone_number_id_input)
        whatsapp_layout.addWidget(QLabel("WhatsApp Business API Token:")); self.whatsapp_api_token_input = QLineEdit(); self.whatsapp_api_token_input.setPlaceholderText("Enter new WhatsApp API Token"); self.whatsapp_api_token_input.setEchoMode(QLineEdit.Password); whatsapp_layout.addWidget(self.whatsapp_api_token_input)
        wa_token_controls_layout = QHBoxLayout(); self.toggle_wa_token_button = QPushButton("Show API Token"); self.toggle_wa_token_button.setCheckable(True); self.toggle_wa_token_button.clicked.connect(self.toggle_whatsapp_token_visibility); self.toggle_wa_token_button.setToolTip("Show/Hide the WhatsApp API Token."); wa_token_controls_layout.addWidget(self.toggle_wa_token_button)
        self.clear_wa_token_button = QPushButton("Clear/Update API Token"); self.clear_wa_token_button.clicked.connect(self.prepare_update_whatsapp_token); self.clear_wa_token_button.setToolTip("Clear the field to enter a new WhatsApp API Token."); wa_token_controls_layout.addWidget(self.clear_wa_token_button); whatsapp_layout.addLayout(wa_token_controls_layout)
        whatsapp_layout.addWidget(QLabel("<i>API Token is hidden. Click 'Clear/Update' to set a new token. Click 'Show' to temporarily view.</i>"))
        self.save_whatsapp_settings_button = QPushButton("Save WhatsApp Settings"); self.save_whatsapp_settings_button.setToolTip("Save the current WhatsApp connector settings."); self.save_whatsapp_settings_button.clicked.connect(self.save_whatsapp_settings); whatsapp_layout.addWidget(self.save_whatsapp_settings_button)
        whatsapp_layout.addWidget(self.whatsapp_status_label); connectors_tab_layout.addStretch(1); self.whatsapp_connector_group.setEnabled(False)

        main_layout.addWidget(self.general_status_label) # Add general status label at the bottom
        self.general_status_label.setText("Status: Initialized. Load or save settings to begin.")

    def _update_general_status(self, message: str, is_error: bool = False, duration: int = 0):
        self.general_status_label.setText(f"Status: {message}")
        self.general_status_label.setStyleSheet("color: red;" if is_error else "color: green;")
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.general_status_label.setText("Status: Idle"))

    def _update_whatsapp_status_label(self, status: str, is_error: bool = False): # Combined with general status
        self.whatsapp_status_label.setText(f"WhatsApp Status: {status}")
        self.whatsapp_status_label.setStyleSheet("color: red;" if is_error else "") # Keep WA status specific color too
        self._update_general_status(f"WhatsApp: {status}", is_error)


    def load_whatsapp_settings_ui(self):
        # ... (implementation as before, but use _update_general_status for some messages) ...
        self.logger.debug(f"Loading WhatsApp settings UI for ubs_id: {self.current_settings_id}")
        if not self.current_settings_id: self.whatsapp_connector_group.setEnabled(False); self._update_whatsapp_status_label("Configure Botpress Core first"); return
        self.whatsapp_connector_group.setEnabled(True)
        try:
            wa_settings = get_whatsapp_settings(self.db_session, user_botpress_settings_id=self.current_settings_id)
            if wa_settings:
                self.enable_whatsapp_checkbox.setChecked(wa_settings.is_enabled)
                self.whatsapp_phone_number_id_input.setText(wa_settings.phone_number_id or "")
                if wa_settings.whatsapp_business_api_token:
                    self.actual_whatsapp_api_token_loaded = wa_settings.whatsapp_business_api_token
                    self.whatsapp_api_token_input.setText("********"); self.whatsapp_api_token_input.setEchoMode(QLineEdit.Password); self.whatsapp_api_token_is_hidden = True
                    self.toggle_wa_token_button.setText("Show API Token"); self.toggle_wa_token_button.setChecked(False)
                else: self._clear_whatsapp_ui_fields(is_loading=True, clear_checkbox=False)

                if wa_settings.is_enabled and self.actual_whatsapp_api_token_loaded and self.whatsapp_phone_number_id_input.text():
                    self._update_whatsapp_status_label("Enabled. Connecting...")
                    self._initiate_whatsapp_connection()
                elif wa_settings.is_enabled: self._update_whatsapp_status_label("Enabled but not fully configured", True)
                else: self._update_whatsapp_status_label("Disabled")
            else: self._clear_whatsapp_ui_fields(is_loading=True); self._update_whatsapp_status_label("Not Configured")
            for item in [self.enable_whatsapp_checkbox, self.whatsapp_phone_number_id_input, self.whatsapp_api_token_input, self.toggle_wa_token_button, self.clear_wa_token_button, self.save_whatsapp_settings_button]: item.setEnabled(True)
        except Exception as e: self.logger.error(f"Error loading WA settings: {e}", exc_info=True); QMessageBox.critical(self, "Error", f"Error loading WA settings: {e}"); self.whatsapp_connector_group.setEnabled(False); self._update_whatsapp_status_label("Error loading", True)


    def _clear_whatsapp_ui_fields(self, is_loading=False, clear_checkbox=True):
        if clear_checkbox: self.enable_whatsapp_checkbox.setChecked(False)
        self.whatsapp_phone_number_id_input.clear()
        self.whatsapp_api_token_input.clear()
        if not is_loading: self.whatsapp_api_token_input.setPlaceholderText("Enter new WhatsApp API Token")
        self.whatsapp_api_token_input.setEchoMode(QLineEdit.Normal)
        self.actual_whatsapp_api_token_loaded = None; self.whatsapp_api_token_is_hidden = False
        self.toggle_wa_token_button.setText("Hide API Token"); self.toggle_wa_token_button.setChecked(True)

    async def _connect_whatsapp_connector_async(self):
        if not self.whatsapp_connector: self._update_whatsapp_status_label("Error: Not initialized", True); return
        self._update_whatsapp_status_label("Connecting...")
        self.save_whatsapp_settings_button.setEnabled(False) # Disable save during connect
        try:
            if self.whatsapp_connector.is_connected: self._update_whatsapp_status_label("Already Connected"); return
            if await self.whatsapp_connector.connect():
                self._update_whatsapp_status_label("Connected")
                await self.whatsapp_connector.start_listening(self.handle_whatsapp_message)
            else: self._update_whatsapp_status_label("Connection Failed", True); self.enable_whatsapp_checkbox.setChecked(False)
        except Exception as e: self.logger.error(f"WA connect exc: {e}", exc_info=True); self._update_whatsapp_status_label(f"Error: {str(e)[:30]}...", True); self.enable_whatsapp_checkbox.setChecked(False)
        finally:
            self.save_whatsapp_settings_button.setEnabled(True)


    async def _disconnect_whatsapp_connector_async(self, clear_instance=True):
        connector = self.whatsapp_connector
        if clear_instance: self.whatsapp_connector = None
        if connector and connector.is_connected:
            self._update_whatsapp_status_label("Disconnecting...")
            try: await connector.stop_listening(); await connector.disconnect(); self._update_whatsapp_status_label("Disconnected")
            except Exception as e: self.logger.error(f"WA disconnect exc: {e}", exc_info=True); self._update_whatsapp_status_label(f"Error disconnecting: {str(e)[:30]}...", True)
        elif connector: self._update_whatsapp_status_label("Already Disconnected")
        else: self._update_whatsapp_status_label("Not Configured")
        if not clear_instance and connector and not connector.is_connected: self._update_whatsapp_status_label("Disconnected")


    def _initiate_whatsapp_connection(self):
        phone_id = self.whatsapp_phone_number_id_input.text().strip()
        token = self.actual_whatsapp_api_token_loaded
        if not (token and phone_id):
            self._update_whatsapp_status_label("Missing Token/Phone ID", True)
            if self.enable_whatsapp_checkbox.isChecked(): self.enable_whatsapp_checkbox.setChecked(False)
            return

        cfg: WhatsAppConnectorConfig = {"platform_name":"whatsapp", "is_enabled":True,
                                        "phone_number_id":phone_id, "whatsapp_business_api_token":token}

        should_reinitialize = False
        if self.whatsapp_connector:
            if (self.whatsapp_connector.phone_number_id != phone_id or \
                self.whatsapp_connector.api_token != token or \
                not self.whatsapp_connector.is_connected): # Also re-init if config is same but not connected
                should_reinitialize = True
                if self.whatsapp_connector.is_connected:
                    self.logger.info("WA config changed or not connected, scheduling disconnect of old instance first.")
                    # Schedule disconnect, but don't clear self.whatsapp_connector yet, new one will overwrite
                    asyncio.create_task(self._disconnect_whatsapp_connector_async(clear_instance=False))
        else: should_reinitialize = True

        if should_reinitialize:
            self.logger.info(f"Initializing/Re-initializing WhatsAppConnector instance for Phone ID: {phone_id}")
            self.whatsapp_connector = WhatsAppConnector(config=cfg)

        asyncio.create_task(self._connect_whatsapp_connector_async())


    def save_whatsapp_settings(self):
        if not self.db_session or not self.current_settings_id: QMessageBox.warning(self, "Core Settings Required", "Save main Botpress settings first."); return
        is_enabled = self.enable_whatsapp_checkbox.isChecked(); phone_id = self.whatsapp_phone_number_id_input.text().strip() or None
        token_input = self.whatsapp_api_token_input.text()
        token_to_save = self.actual_whatsapp_api_token_loaded if (self.whatsapp_api_token_is_hidden and token_input == "********") else (token_input.strip() or None)
        if token_to_save == "": token_to_save = None # Store NULL if user explicitly cleared it

        self.save_whatsapp_settings_button.setEnabled(False) # Disable button during save
        self._update_general_status("Saving WhatsApp settings...")
        try:
            create_or_update_whatsapp_settings(self.db_session, self.current_settings_id, is_enabled, phone_id, token_to_save)
            self.actual_whatsapp_api_token_loaded = token_to_save
            if self.actual_whatsapp_api_token_loaded: self.whatsapp_api_token_input.setText("********"); self.whatsapp_api_token_input.setEchoMode(QLineEdit.Password); self.whatsapp_api_token_is_hidden = True; self.toggle_wa_token_button.setChecked(False); self.toggle_wa_token_button.setText("Show API Token")
            else: self._clear_whatsapp_ui_fields(is_loading=True, clear_checkbox=False)
            QMessageBox.information(self, "Success", "WhatsApp settings saved."); self.logger.info("WhatsApp settings saved.")
            self._update_general_status("WhatsApp settings saved successfully.", duration=3000)
        except Exception as e: self.logger.error(f"Error saving WA settings: {e}", exc_info=True); QMessageBox.critical(self, "Error", f"Failed to save WA settings: {e}"); self._update_whatsapp_status_label("Error saving", True); self._update_general_status(f"Error saving WA settings: {e}", True, 5000); return
        finally:
            self.save_whatsapp_settings_button.setEnabled(True)

        if is_enabled and phone_id and self.actual_whatsapp_api_token_loaded: self._initiate_whatsapp_connection()
        elif not is_enabled: asyncio.create_task(self._disconnect_whatsapp_connector_async(clear_instance=True))
        else: self._update_whatsapp_status_label("Enabled but not fully configured", True); asyncio.create_task(self._disconnect_whatsapp_connector_async(clear_instance=True))

    def toggle_whatsapp_token_visibility(self):
        if not self.actual_whatsapp_api_token_loaded and self.whatsapp_api_token_input.text() == "********":
             QMessageBox.information(self, "Token", "No API Token set."); self.toggle_wa_token_button.setChecked(False); return
        if self.toggle_wa_token_button.isChecked():
            if self.actual_whatsapp_api_token_loaded: self.whatsapp_api_token_input.setText(self.actual_whatsapp_api_token_loaded)
            self.whatsapp_api_token_input.setEchoMode(QLineEdit.Normal); self.whatsapp_api_token_is_hidden = False; self.toggle_wa_token_button.setText("Hide API Token")
        else:
            if self.actual_whatsapp_api_token_loaded or self.whatsapp_api_token_input.text(): self.whatsapp_api_token_input.setText("********")
            self.whatsapp_api_token_input.setEchoMode(QLineEdit.Password); self.whatsapp_api_token_is_hidden = True; self.toggle_wa_token_button.setText("Show API Token")

    def prepare_update_whatsapp_token(self):
        self._clear_whatsapp_ui_fields(clear_checkbox=False)
        self.whatsapp_api_token_input.setPlaceholderText("Enter new WhatsApp API Token here")
        self.whatsapp_api_token_input.setFocus(); QMessageBox.information(self, "Update Token", "Field cleared. Enter new token and save.")

    def load_settings(self):
        if not self.db_session: QMessageBox.critical(self, "DB Error", "No DB Session."); self._update_general_status("DB Error", True); return
        if not self.current_user_id: QMessageBox.warning(self, "User Error", "No User ID."); self._update_general_status("User Error", True); return
        self.logger.info(f"Loading settings for user_id: {self.current_user_id}")
        self._update_general_status("Loading settings...")
        self.load_settings_button.setEnabled(False)
        try:
            settings = get_botpress_settings(self.db_session, user_id=self.current_user_id)
            if settings:
                self.actual_api_key_loaded = settings.api_key; self.api_key_input.setText("********"); self.api_key_input.setEchoMode(QLineEdit.Password); self.api_key_input_is_hidden = True; self.toggle_api_key_button.setChecked(False); self.toggle_api_key_button.setText("Show API Key")
                self.bot_id_input.setText(settings.bot_id); self.current_settings_id = settings.id
                self.logger.info(f"Botpress Core settings loaded for user {self.current_user_id}.")
                try:
                    self.botpress_client = BotpressClient(api_key=self.actual_api_key_loaded, bot_id=settings.bot_id)
                    self._append_html_message("System", "Botpress Client Initialized.", datetime.now().strftime("%H:%M:%S"))
                    self.load_conversation_history()
                    self.load_prompts()
                    if not self.polling_timer.isActive(): self.polling_timer.start(self.polling_interval_ms)
                    self._update_general_status("Botpress settings loaded.", duration=3000)
                except Exception as e: self.logger.error(f"Failed to init Botpress client: {e}", exc_info=True); self.botpress_client = None; self._append_html_message("System", f"Botpress Client init failed: {e}", datetime.now().strftime("%H:%M:%S"), True); self._update_general_status("Botpress client init failed.", True, 5000)
            else: self._clear_core_botpress_ui_fields(); self.current_settings_id = None; self._update_whatsapp_status_label("Configure Botpress Core first"); self.whatsapp_connector_group.setEnabled(False); self._update_general_status("No Botpress settings found.", True, 3000)
            if self.current_settings_id: self.load_whatsapp_settings_ui() # This will also attempt WA connect if enabled
            else: self._disable_whatsapp_ui()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}", exc_info=True); QMessageBox.critical(self, "Error", f"Failed to load settings: {e}"); self._update_general_status(f"Error loading settings: {e}", True, 5000)
            if self.polling_timer.isActive(): self.polling_timer.stop()
            self.current_settings_id = None; self._disable_whatsapp_ui()
        finally:
            self.load_settings_button.setEnabled(True)


    def _clear_core_botpress_ui_fields(self):
        self.api_key_input.clear(); self.actual_api_key_loaded = None; self.api_key_input.setPlaceholderText("Enter new Botpress API Key"); self.api_key_input.setEchoMode(QLineEdit.Normal); self.api_key_input_is_hidden = False; self.toggle_api_key_button.setChecked(True); self.toggle_api_key_button.setText("Hide API Key")
        self.bot_id_input.clear(); self.current_settings_id = None
        if hasattr(self, 'prompts_table_widget'): self.prompts_table_widget.setRowCount(0)
        self._update_general_status("Core settings cleared.", duration=3000)

    def _disable_whatsapp_ui(self):
        self.whatsapp_connector_group.setEnabled(False)
        self.enable_whatsapp_checkbox.setChecked(False)
        self.whatsapp_phone_number_id_input.clear()
        self.whatsapp_api_token_input.setText("********"); self.whatsapp_api_token_input.setEchoMode(QLineEdit.Password)
        self.actual_whatsapp_api_token_loaded = None; self.whatsapp_api_token_is_hidden = True
        self._update_whatsapp_status_label("Configure Botpress Core first")

    def save_settings(self): # Core Botpress settings
        if not self.db_session or not self.current_user_id: return
        self.save_settings_button.setEnabled(False)
        self._update_general_status("Saving Botpress settings...")
        bot_id = self.bot_id_input.text().strip()
        current_input_key = self.api_key_input.text()
        api_key_to_save = self.actual_api_key_loaded if (self.api_key_input_is_hidden and current_input_key == "********") else current_input_key.strip()
        if not (bot_id and api_key_to_save): QMessageBox.warning(self, "Input Error", "API Key and Bot ID required."); self.save_settings_button.setEnabled(True); self._update_general_status("Save failed: Input error.", True, 3000); return
        try:
            settings = create_or_update_botpress_settings(self.db_session, self.current_user_id, api_key_to_save, bot_id)
            self.current_settings_id = settings.id; self.actual_api_key_loaded = api_key_to_save
            self.api_key_input.setText("********"); self.api_key_input.setEchoMode(QLineEdit.Password); self.api_key_input_is_hidden = True; self.toggle_api_key_button.setChecked(False); self.toggle_api_key_button.setText("Show API Key")
            self.botpress_client = BotpressClient(api_key=self.actual_api_key_loaded, bot_id=bot_id)
            QMessageBox.information(self, "Settings Saved", "Botpress API settings saved.")
            self._append_html_message("System", "Botpress Client Re-initialized.", datetime.now().strftime("%H:%M:%S"))
            if not self.polling_timer.isActive() and self.botpress_client : self.polling_timer.start(self.polling_interval_ms)
            self.load_prompts()
            self.whatsapp_connector_group.setEnabled(True); self.load_whatsapp_settings_ui()
            self._update_general_status("Botpress settings saved.", duration=3000)
        except Exception as e: self.logger.error(f"Error saving core settings: {e}", exc_info=True); QMessageBox.critical(self, "Save Error", str(e)); self.polling_timer.stop(); self._update_general_status(f"Error saving: {e}", True, 5000)
        finally:
            self.save_settings_button.setEnabled(True)

    def toggle_api_key_visibility(self):
        if not self.actual_api_key_loaded and self.api_key_input.text() == "********": QMessageBox.information(self, "API Key", "No API Key set."); self.toggle_api_key_button.setChecked(False); return
        if self.toggle_api_key_button.isChecked():
            if self.actual_api_key_loaded: self.api_key_input.setText(self.actual_api_key_loaded)
            self.api_key_input.setEchoMode(QLineEdit.Normal); self.api_key_input_is_hidden = False; self.toggle_api_key_button.setText("Hide API Key")
        else:
            if self.actual_api_key_loaded or self.api_key_input.text(): self.api_key_input.setText("********")
            self.api_key_input.setEchoMode(QLineEdit.Password); self.api_key_input_is_hidden = True; self.toggle_api_key_button.setText("Show API Key")

    def prepare_update_api_key(self):
        self.api_key_input.clear(); self.api_key_input.setPlaceholderText("Enter new API Key here"); self.api_key_input.setEchoMode(QLineEdit.Normal); self.api_key_input_is_hidden = False; self.toggle_api_key_button.setText("Hide API Key"); self.toggle_api_key_button.setChecked(True); self.api_key_input.setFocus(); QMessageBox.information(self, "Update API Key", "Field cleared.")

    async def handle_send_message(self):
        # ... (Full implementation as before, ensure BotpressClient.send_message is awaited)
        self.logger.debug("handle_send_message called.")
        if not self.botpress_client: QMessageBox.warning(self, "Client Not Ready", "Botpress client not initialized."); return
        user_message_text = self.message_input.text().strip()
        if not user_message_text: return
        timestamp_str = datetime.now().strftime("%H:%M:%S"); ui_botpress_user_id = self.current_user_id
        self._append_html_message("You", user_message_text, timestamp_str); self.displayed_message_identifiers.add(f"You:{user_message_text}")
        self.logger.info(f"User sending message via UI to Botpress user_id '{ui_botpress_user_id}': {user_message_text}")
        try:
            bot_responses = await self.botpress_client.send_message(user_id=ui_botpress_user_id, message_text=user_message_text) # Assuming send_message is async
            if bot_responses:
                for resp in bot_responses:
                    if resp.get('type') == 'text' and resp.get('text'):
                        bot_text = resp['text']
                        self._append_html_message("Bot", bot_text, datetime.now().strftime("%H:%M:%S")); self.displayed_message_identifiers.add(f"Bot:{bot_text}")
                        self.logger.info(f"Bot response (to UI user '{ui_botpress_user_id}') displayed: {bot_text}")
                        if self.whatsapp_connector and self.whatsapp_connector.is_connected and ui_botpress_user_id and ui_botpress_user_id != "default_user": # Placeholder
                            self.logger.info(f"Forwarding Botpress reply to WA user '{ui_botpress_user_id}'")
                            asyncio.create_task(self.whatsapp_connector.send_message(ui_botpress_user_id, {'type':'text', 'text':bot_text}))
        except Exception as e: self.logger.error(f"Error in handle_send_message: {e}", exc_info=True); self._append_html_message("System", f"Error: {e}", datetime.now().strftime("%H:%M:%S"), is_error=True); QMessageBox.critical(self, "Error", f"Failed to send message: {e}")
        self.message_input.clear()


    def load_conversation_history(self):
        self.logger.debug("load_conversation_history called.")
        if not self.botpress_client: return
        self._append_html_message("System", "Loading conversation history...", datetime.now().strftime("%H:%M:%S"))
        try:
            # Assuming get_conversations is now async or needs to be run in executor
            # For now, direct call for simplicity, but this could block if not async
            # history = await self.botpress_client.get_conversations(user_id=self.current_user_id, limit=50) # If async
            history = self.botpress_client.get_conversations(user_id=self.current_user_id, limit=50) # If sync

            self.displayed_message_identifiers.clear()
            if not history: self._append_html_message("System", "No conversation history found.", datetime.now().strftime("%H:%M:%S")); return

            for message_data in history:
                payload = message_data.get('payload', {}); text_content = payload.get('text', '') or message_data.get('text', '')
                if not text_content: continue
                sender_display_name = "Bot"
                if message_data.get('direction') == 'outgoing' or (message_data.get('userId') and message_data.get('userId') == self.current_user_id) : sender_display_name = "You"
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if 'createdOn' in message_data:
                    try: ts_from_api = message_data['createdOn'].replace('Z', '+00:00'); dt_obj = datetime.fromisoformat(ts_from_api); timestamp_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                    except: pass # Keep default timestamp if parse fails
                self._append_html_message(sender_display_name, text_content, timestamp_str); self.displayed_message_identifiers.add(f"{sender_display_name}:{text_content}")
            self._append_html_message("System", "--- End of history ---", datetime.now().strftime("%H:%M:%S"))
        except Exception as e: self.logger.error(f"Error loading history: {e}", exc_info=True); self._append_html_message("System", f"Error loading history: {e}", datetime.now().strftime("%H:%M:%S"), is_error=True)

    def _format_message_as_html(self, sender: str, text: str, timestamp: str, is_error: bool = False) -> str:
        align = "right" if sender.lower() == "you" else "left"; sender_color = "#007bff" if sender.lower() == "you" else "#28a745"; text_color = "#212529"
        if "wa user" in sender.lower(): sender_color = "#17a2b8"
        if sender.lower() == "system" or is_error: sender_color = "#dc3545"; text_color = "#721c24"; align = "center"
        return f"""<div style='margin: 5px; text-align: {align};'><div style='display: inline-block; max-width: 75%; padding: 8px 12px; border-radius: 10px; background-color: #f1f0f0; text-align: left;'><span style='color: {sender_color}; font-weight: bold;'>{sender}</span> <span style='color: #6c757d; font-size: 0.8em;'> ({timestamp})</span><div style='color: {text_color}; margin-top: 3px;'>{text.replace("\\n", "<br>")}</div></div></div>"""

    def _append_html_message(self, sender: str, text: str, timestamp: str, is_error: bool = False):
        if not text: return
        self.conversation_display.append(self._format_message_as_html(sender, text, timestamp, is_error)); self.conversation_display.ensureCursorVisible()

    def check_for_new_messages(self):
        self.logger.debug(f"Polling: Checking for new messages for user {self.current_user_id}...")
        if not self.botpress_client or not self.current_user_id: return
        try:
            # Assuming get_conversations is sync for this example, if it were async:
            # all_messages = await self.botpress_client.get_conversations(user_id=self.current_user_id, limit=20)
            all_messages = self.botpress_client.get_conversations(user_id=self.current_user_id, limit=20)
            new_messages_to_display = []
            if all_messages:
                for message_data in all_messages:
                    payload = message_data.get('payload', {}); text_content = payload.get('text', '') or message_data.get('text', '')
                    if not text_content: continue
                    sender_display_name = "Bot"
                    if message_data.get('direction') == 'outgoing' or \
                       (message_data.get('userId') and message_data.get('userId') == self.current_user_id and \
                        not message_data.get('participantId') and not message_data.get('conversationId','').startswith('wa_')): # Heuristic
                        sender_display_name = "You"
                    msg_identifier = f"{sender_display_name}:{text_content}"
                    if msg_identifier not in self.displayed_message_identifiers:
                        new_messages_to_display.append({'sender': sender_display_name, 'text': text_content, 'timestamp': datetime.now().strftime("%H:%M:%S")})
                        self.displayed_message_identifiers.add(msg_identifier)
            if new_messages_to_display:
                for msg_detail in new_messages_to_display:
                    self._append_html_message(msg_detail['sender'], msg_detail['text'], msg_detail['timestamp'])
                    if msg_detail['sender'].lower() == "bot" and self.whatsapp_connector and self.whatsapp_connector.is_connected and self.current_user_id and self.current_user_id != "default_user": # Placeholder
                        self.logger.info(f"Forwarding polled Botpress reply for '{self.current_user_id}' to WA: {msg_detail['text']}")
                        asyncio.create_task(self.whatsapp_connector.send_message(self.current_user_id, {'type':'text', 'text':msg_detail['text']}))
        except Exception as e: self.logger.error(f"Error in check_for_new_messages: {e}", exc_info=True)

    async def handle_whatsapp_message(self, message_data: Dict[str, Any]):
        self.logger.info(f"UI received standardized message from WhatsApp: {message_data}")
        text_content = message_data.get('content', {}).get('text'); whatsapp_sender_id = message_data.get('sender_id')
        timestamp_from_msg = message_data.get('timestamp', datetime.now().isoformat())
        try: dt_obj = datetime.fromisoformat(timestamp_from_msg.replace('Z', '+00:00')); display_timestamp = dt_obj.strftime("%H:%M:%S")
        except ValueError: display_timestamp = datetime.now().strftime("%H:%M:%S")
        if text_content and whatsapp_sender_id:
            wa_display_sender = f"WA User ({whatsapp_sender_id[-4:]})" if len(whatsapp_sender_id) > 4 else f"WA User ({whatsapp_sender_id})"
            self._append_html_message(wa_display_sender, text_content, display_timestamp); self.displayed_message_identifiers.add(f"{wa_display_sender}:{text_content}")
        if not self.botpress_client or not text_content or not whatsapp_sender_id: return
        self.logger.info(f"Forwarding message from WA user {whatsapp_sender_id} to Botpress user_id: {whatsapp_sender_id}")
        try:
            # Assuming BotpressClient.send_message is async
            botpress_responses = await self.botpress_client.send_message(user_id=whatsapp_sender_id, message_text=text_content)
            if botpress_responses and self.whatsapp_connector and self.whatsapp_connector.is_connected:
                for bp_resp in botpress_responses:
                    if bp_resp.get('type') == 'text' and bp_resp.get('text'):
                        bp_text_to_wa = bp_resp['text']
                        asyncio.create_task(self.whatsapp_connector.send_message(whatsapp_sender_id, {'type':'text', 'text':bp_text_to_wa}))
                        display_sender_for_ui = f"Bot (to WA {whatsapp_sender_id[-4:]})" if len(whatsapp_sender_id) > 4 else f"Bot (to WA {whatsapp_sender_id})"
                        if self.current_user_id == whatsapp_sender_id: display_sender_for_ui = "Bot"
                        self._append_html_message(display_sender_for_ui, bp_text_to_wa, datetime.now().strftime("%H:%M:%S")); self.displayed_message_identifiers.add(f"{display_sender_for_ui}:{bp_text_to_wa}")
        except Exception as e: self.logger.error(f"Error processing WA message for Botpress: {e}", exc_info=True); self._append_html_message("System", f"Error processing WA message: {e}", datetime.now().strftime("%H:%M:%S"), is_error=True)

    def add_prompt(self):
        if not self.db_session or not self.current_settings_id: QMessageBox.warning(self, "Prerequisites Missing", "Ensure DB session and core Botpress settings are loaded."); return
        dialog = PromptEditDialog(parent=self, db_session=self.db_session, settings_id=self.current_settings_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                try: create_user_prompt(self.db_session, self.current_settings_id, data['name'], data['text'], data['category'], data['tags']); self.load_prompts()
                except Exception as e: QMessageBox.critical(self, "Error", str(e)); self.logger.error(f"Add prompt error: {e}", exc_info=True)

    def edit_selected_prompt_from_table(self): # Renamed and acts on table selection
        current_row = self.prompts_table_widget.currentRow()
        if current_row < 0: QMessageBox.warning(self, "Selection Error", "Please select a prompt to edit."); return
        name_item = self.prompts_table_widget.item(current_row, 0)
        if not name_item or name_item.data(Qt.UserRole) is None: QMessageBox.warning(self, "Selection Error", "No valid prompt selected."); return
        prompt_id = name_item.data(Qt.UserRole)
        self.edit_prompt(prompt_id)

    def edit_prompt(self, prompt_id: int): # Uses PromptEditDialog
        if not self.db_session: return
        prompt = get_prompt_by_id(self.db_session, prompt_id)
        if not prompt: QMessageBox.critical(self, "Error", "Prompt not found."); self.load_prompts(); return
        dialog = PromptEditDialog(current_prompt_data=prompt.as_dict() if hasattr(prompt, 'as_dict') else {"name":prompt.prompt_name, "text":prompt.prompt_text, "category":prompt.category or "", "tags":prompt.tags or ""}, parent=self, db_session=self.db_session, settings_id=self.current_settings_id, editing_prompt_id=prompt_id) # Pass existing data
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                try: update_user_prompt(self.db_session, prompt_id, data['name'], data['text'], data['category'], data['tags']); self.load_prompts()
                except Exception as e: QMessageBox.critical(self, "Error", str(e)); self.logger.error(f"Update prompt error: {e}", exc_info=True)

    def delete_selected_prompt(self): # Works with QTableWidget
        current_row = self.prompts_table_widget.currentRow()
        if current_row < 0: QMessageBox.warning(self, "Selection Error", "Please select a prompt."); return
        name_item = self.prompts_table_widget.item(current_row, 0)
        if not name_item or name_item.data(Qt.UserRole) is None: QMessageBox.critical(self, "Error", "Invalid selection."); return
        prompt_id = name_item.data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", f"Delete '{name_item.text()}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                if delete_user_prompt(self.db_session, prompt_id): self.load_prompts()
                else: QMessageBox.warning(self, "Delete Error", "Could not delete.")
            except Exception as e: QMessageBox.critical(self, "Delete Error", str(e)); self.logger.error(f"Delete prompt error: {e}", exc_info=True)

    def filter_prompts_display(self):
        search_term = self.prompt_search_input.text().lower()
        selected_category = self.prompt_category_filter_combo.currentData() # This is category string or None
        for row in range(self.prompts_table_widget.rowCount()):
            name_item = self.prompts_table_widget.item(row, 0)
            category_item = self.prompts_table_widget.item(row, 1)
            tags_item = self.prompts_table_widget.item(row, 2)
            preview_item = self.prompts_table_widget.item(row, 3)

            row_visible = True
            if selected_category and (not category_item or category_item.text() != selected_category):
                row_visible = False

            if row_visible and search_term: # Only apply search if row is not already hidden by category
                name_match = search_term in (name_item.text().lower() if name_item else "")
                cat_match = search_term in (category_item.text().lower() if category_item else "")
                tag_match = search_term in (tags_item.text().lower() if tags_item else "")
                prev_match = search_term in (preview_item.text().lower() if preview_item else "")
                if not (name_match or cat_match or tag_match or prev_match):
                    row_visible = False
            self.prompts_table_widget.setRowHidden(row, not row_visible)

    def _populate_category_filter(self):
        self.logger.debug("Populating category filter.")
        self.prompt_category_filter_combo.blockSignals(True)
        current_data = self.prompt_category_filter_combo.currentData()
        self.prompt_category_filter_combo.clear()
        self.prompt_category_filter_combo.addItem("All Categories", "") # Use empty string for "all"
        if self.db_session and self.current_settings_id:
            try:
                distinct_categories = self.db_session.query(UserPrompt.category).\
                                      filter(UserPrompt.settings_id == self.current_settings_id, UserPrompt.category != None, UserPrompt.category != "").\
                                      distinct().order_by(UserPrompt.category).all()
                categories = [cat[0] for cat in distinct_categories if cat[0]]
                for cat_name in categories: self.prompt_category_filter_combo.addItem(cat_name, cat_name)
                idx = self.prompt_category_filter_combo.findData(current_data)
                if idx != -1: self.prompt_category_filter_combo.setCurrentIndex(idx)
            except Exception as e: self.logger.error(f"Error populating categories: {e}", exc_info=True)
        self.prompt_category_filter_combo.blockSignals(False)

    def closeEvent(self, event):
        self.logger.info("BotpressIntegrationUI closeEvent triggered.")
        if self.polling_timer.isActive(): self.polling_timer.stop(); self.logger.info("Botpress Core Polling timer stopped.")
        if self.whatsapp_connector and self.whatsapp_connector.is_connected:
            self.logger.info("Disconnecting WhatsApp connector during closeEvent...")
            try:
                if self.loop and self.loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self._disconnect_whatsapp_connector_async(clear_instance=True), self.loop)
                    future.result(timeout=5)
                    self.logger.info("WhatsApp connector disconnect task completed.")
                else:
                    asyncio.run(self._disconnect_whatsapp_connector_async(clear_instance=True))
                    self.logger.info("WhatsApp connector disconnect process completed via asyncio.run().")
            except Exception as e: self.logger.error(f"Error during WA disconnect in closeEvent: {e}", exc_info=True)
        if self.db_session: self.db_session.close(); self.logger.info("Database session closed.")
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    test_user_id = "test_dev_user_001"
    main_window = QWidget()
    window = BotpressIntegrationUI(parent=main_window, current_user_id=test_user_id)
    window.setGeometry(100, 100, 700, 800); window.show()
    if app.applicationName() == '':
        try: sys.exit(app.exec_())
        except SystemExit:
            if hasattr(window, 'polling_timer') and window.polling_timer.isActive(): window.polling_timer.stop()
            if hasattr(window, 'whatsapp_connector') and window.whatsapp_connector and window.whatsapp_connector.is_connected:
                if window.loop and window.loop.is_running(): asyncio.run_coroutine_threadsafe(window._disconnect_whatsapp_connector_async(clear_instance=True), window.loop).result(timeout=2)
                else: asyncio.run(window._disconnect_whatsapp_connector_async(clear_instance=True))
            if hasattr(window, 'db_session') and window.db_session: window.db_session.close()
            window.logger.info("Test instance shutdown complete.")
