import sys
import os
import json # Not immediately used, but good for future enhancements

from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QListWidget,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QGroupBox, QTabWidget,
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging # Added for logging

# Assuming db.py and app_config.py are in the same directory or accessible in PYTHONPATH
import db
from app_config import CONFIG

logger = logging.getLogger(__name__) # Added logger

# For reading .docx template content for preview (if template type is word)
try:
    import docx
except ImportError:
    logger.warning("python-docx is not installed. Word template preview will not work.")
    docx = None

# Import QThread for background email sending
from PyQt5.QtCore import QThread

# Import the service
from email_service import EmailSenderService


class EmailWorker(QObject):
    """
    Worker object to handle email sending in a separate thread.
    """
    email_sent_signal = pyqtSignal(bool, str) # success, message
    finished_signal = pyqtSignal() # To signal the thread to quit

    def __init__(self, client_id, recipients, subject, body_html, attachments,
                 template_language_code, project_id, smtp_config_id=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.recipients = recipients
        self.subject = subject
        self.body_html = body_html
        self.attachments = attachments
        self.template_language_code = template_language_code
        self.project_id = project_id
        self.smtp_config_id = smtp_config_id

    def send(self):
        """
        Performs the email sending operation.
        """
        try:
            email_service = EmailSenderService(smtp_config_id=self.smtp_config_id)
            if not email_service.smtp_config:
                logger.error("EmailWorker: SMTP configuration not loaded or invalid.")
                self.email_sent_signal.emit(False, "SMTP configuration not loaded or invalid.")
                self.finished_signal.emit()
                return

            success, message = email_service.send_email(
                client_id=self.client_id,
                recipients=self.recipients,
                subject_template=self.subject, # Subject is already personalized or a template
                body_html_template=self.body_html, # Body is already personalized or a template
                attachments=self.attachments,
                template_language_code=self.template_language_code,
                project_id=self.project_id
            )
            self.email_sent_signal.emit(success, message)
        except Exception as e:
            logger.error(f"An unexpected error occurred in EmailWorker: {str(e)}", exc_info=True)
            self.email_sent_signal.emit(False, f"An unexpected error occurred in EmailWorker: {str(e)}")
        finally:
            self.finished_signal.emit()


class EmailSendingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Email")
        self.setMinimumSize(800, 700) # Adjusted size

        # Member variables
        self.selected_client_id = None
        self.selected_language_code = None
        self.selected_email_template_id = None
        # self.selected_attachments = [] # Will be populated by selection logic

        self.init_ui()
        try:
            self._initial_population()
        except Exception as e:
            logger.error("Failed during initial population of EmailSendingDialog.", exc_info=True)
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize dialog components: {e}")


    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Client and Recipients Section ---
        client_recipient_group = QGroupBox("Recipient Information")
        client_recipient_layout = QHBoxLayout(client_recipient_group) # Use QHBoxLayout for side-by-side

        # Client Selection
        client_form_layout = QFormLayout()
        self.client_combo = QComboBox()
        self.client_combo.setPlaceholderText("Select a client...")
        self.client_combo.currentIndexChanged.connect(self.on_client_selected)
        client_form_layout.addRow(QLabel("Client:"), self.client_combo)

        client_widget = QWidget()
        client_widget.setLayout(client_form_layout)
        client_recipient_layout.addWidget(client_widget, 1) # Takes 1/3 space

        # Recipients Display
        recipients_layout = QVBoxLayout()
        recipients_layout.addWidget(QLabel("Recipients (auto-populated):"))
        self.recipients_list = QListWidget()
        self.recipients_list.setSelectionMode(QListWidget.MultiSelection) # Allow selecting multiple for info, though sending typically uses all
        recipients_layout.addWidget(self.recipients_list)

        recipients_widget = QWidget()
        recipients_widget.setLayout(recipients_layout)
        client_recipient_layout.addWidget(recipients_widget, 2) # Takes 2/3 space

        main_layout.addWidget(client_recipient_group)

        # --- Email Template and Content Section ---
        email_content_group = QGroupBox("Email Content")
        email_content_layout = QVBoxLayout(email_content_group)

        # Language and Template Selection
        lang_template_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.currentIndexChanged.connect(self.populate_email_templates_combo)
        lang_template_layout.addWidget(QLabel("Email Language:"))
        lang_template_layout.addWidget(self.language_combo)

        self.email_template_combo = QComboBox()
        self.email_template_combo.setPlaceholderText("Select an email template...")
        self.email_template_combo.currentIndexChanged.connect(self.on_email_template_selected)
        lang_template_layout.addWidget(QLabel("Email Template:"))
        lang_template_layout.addWidget(self.email_template_combo)
        lang_template_layout.addStretch()
        email_content_layout.addLayout(lang_template_layout)

        # Subject and Body Editing
        email_details_layout = QFormLayout()
        self.subject_edit = QLineEdit()
        email_details_layout.addRow(QLabel("Subject:"), self.subject_edit)

        # Splitter for Body and Preview
        body_preview_splitter = QHBoxLayout()

        body_section_layout = QVBoxLayout()
        body_section_layout.addWidget(QLabel("Body:"))
        self.body_edit = QTextEdit() # Allows rich text
        self.body_edit.setAcceptRichText(True)
        body_section_layout.addWidget(self.body_edit)
        body_preview_splitter.addLayout(body_section_layout, 2) # Body takes more space

        preview_section_layout = QVBoxLayout()
        preview_section_layout.addWidget(QLabel("Template Preview:"))
        self.template_preview_area = QTextEdit()
        self.template_preview_area.setReadOnly(True)
        preview_section_layout.addWidget(self.template_preview_area)
        body_preview_splitter.addLayout(preview_section_layout, 1) # Preview takes less space

        email_details_layout.addRow(body_preview_splitter) # Add splitter to form layout
        email_content_layout.addLayout(email_details_layout)
        main_layout.addWidget(email_content_group)

        # --- Attachments Section ---
        attachment_group = QGroupBox("Attachments")
        attachment_main_layout = QVBoxLayout(attachment_group)
        self.attachment_tabs = QTabWidget()

        # Client Documents Tab
        client_docs_widget = QWidget()
        client_docs_layout = QVBoxLayout(client_docs_widget)
        self.client_doc_filter_combo = QComboBox()
        self.client_doc_filter_combo.addItems(["All", "PDF", "Word", "Excel"])
        self.client_doc_filter_combo.currentIndexChanged.connect(self.populate_client_documents_tree)
        client_docs_layout.addWidget(self.client_doc_filter_combo)
        self.client_docs_tree = QTreeWidget()
        self.client_docs_tree.setHeaderLabels(["Select", "Name", "Type", "Path/Source"]) # Simplified "Size" for now
        self.client_docs_tree.setColumnWidth(0, 50) # For checkbox
        self.client_docs_tree.setColumnWidth(1, 250) # Name
        client_docs_layout.addWidget(self.client_docs_tree)
        self.attachment_tabs.addTab(client_docs_widget, "Client Documents")

        # Utility Documents Tab
        utility_docs_widget = QWidget()
        utility_docs_layout = QVBoxLayout(utility_docs_widget)
        self.utility_docs_tree = QTreeWidget()
        self.utility_docs_tree.setHeaderLabels(["Select", "Name", "Type", "Language"]) # Simplified
        self.utility_docs_tree.setColumnWidth(0, 50)
        self.utility_docs_tree.setColumnWidth(1, 250)
        utility_docs_layout.addWidget(self.utility_docs_tree)
        self.attachment_tabs.addTab(utility_docs_widget, "Utility Documents")

        attachment_main_layout.addWidget(self.attachment_tabs)
        main_layout.addWidget(attachment_group)

        # --- Action Buttons ---
        action_buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Send Email")
        self.send_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.send_button.clicked.connect(self.handle_send_email) # Changed from self.accept

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        action_buttons_layout.addStretch()
        action_buttons_layout.addWidget(self.send_button)
        action_buttons_layout.addWidget(self.cancel_button)

        # Status Label for feedback
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label) # Add status label at the bottom
        main_layout.addLayout(action_buttons_layout)

        # Threading members
        self.email_thread = None
        self.email_worker = None


    def _initial_population(self):
        self.populate_clients_combo()
        self.populate_languages_combo()
        # Other population methods are triggered by selections

    def handle_send_email(self):
        # 1. Gather data from UI
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Input Error", "Please select a client.")
            logger.warning("Send email attempt failed: No client selected.")
            return

        recipients = self.get_selected_recipients()
        if not recipients:
            QMessageBox.warning(self, "Input Error", "No recipients specified or found for the client.")
            logger.warning("Send email attempt failed: No recipients for selected client.")
            return

        subject = self.get_selected_subject()
        if not subject.strip():
            QMessageBox.warning(self, "Input Error", "Subject cannot be empty.")
            logger.warning("Send email attempt failed: Subject is empty.")
            return

        body_html = self.get_selected_body() # This is already personalized by template selection
        if not body_html.strip(): # Basic check for empty body
            QMessageBox.warning(self, "Input Error", "Email body cannot be empty.")
            logger.warning("Send email attempt failed: Body is empty.")
            return

        attachments = self.get_selected_attachments()
        template_language_code = self.language_combo.currentData()

        # TODO: Get project_id if applicable (e.g., from another combo or context)
        project_id = None # Placeholder for now

        # TODO: Allow selection of SMTP config if multiple exist, for now uses default or first.
        smtp_config_id = None # Pass None to use default in EmailSenderService

        # 2. Disable UI and show busy indicator
        self.send_button.setEnabled(False)
        self.cancel_button.setEnabled(False) # Optionally disable cancel during send
        self.status_label.setText("Sending email, please wait...")
        QApplication.processEvents() # Ensure UI updates

        logger.info(f"Starting email worker thread for client ID {client_id}, recipients: {recipients}")
        # 3. Setup and start QThread
        self.email_thread = QThread()
        self.email_worker = EmailWorker(
            client_id, recipients, subject, body_html, attachments,
            template_language_code, project_id, smtp_config_id
        )
        self.email_worker.moveToThread(self.email_thread)

        # Connect signals
        self.email_thread.started.connect(self.email_worker.send) # Worker's main method
        self.email_worker.email_sent_signal.connect(self.on_email_sent)
        self.email_worker.finished_signal.connect(self.email_thread.quit)
        self.email_worker.finished_signal.connect(self.email_worker.deleteLater)
        self.email_thread.finished.connect(self.email_thread.deleteLater)

        self.email_thread.start()

    def on_email_sent(self, success: bool, message: str):
        self.status_label.setText(message) # Update status label first
        self.send_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        if success:
            QMessageBox.information(self, "Email Sent", message)
            logger.info(f"Email sending status from worker: {message}")
            # super().accept() # Optionally close dialog on success
        else:
            QMessageBox.warning(self, "Email Send Error", message)
            logger.error(f"Email sending status from worker: {message}")

        # Clean up references, thread should have cleaned itself up via deleteLater
        self.email_thread = None
        self.email_worker = None


    def populate_clients_combo(self):
        self.client_combo.clear()
        self.client_combo.addItem("Select a client...", None)
        try:
            clients = db.get_all_clients()
            for client in clients:
                display_name = f"{client.get('client_name', 'N/A')} ({client.get('company_name', 'N/A')})"
                self.client_combo.addItem(display_name, client.get('client_id'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load clients: {str(e)}")
            logger.error("Failed to populate initial client combo box.", exc_info=True)

    def on_client_selected(self):
        self.selected_client_id = self.client_combo.currentData()
        if self.selected_client_id:
            logger.info(f"Client selected: ID {self.selected_client_id}")
            try:
                self.populate_recipients_list()
                self.populate_client_documents_tree()
                # TODO: Potentially update default language based on client's language preference if stored
            except Exception as e:
                logger.error(f"Failed to populate recipients or documents for client ID {self.selected_client_id} after selection.", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to load data for client {self.selected_client_id}: {e}")
        else:
            self.recipients_list.clear()
            self.client_docs_tree.clear()

    def populate_recipients_list(self):
        self.recipients_list.clear()
        if not self.selected_client_id:
            return
        try:
            contacts = db.get_contacts_for_client(self.selected_client_id)
            added_emails = set()
            for contact in contacts:
                if contact.get('can_receive_documents') and contact.get('email'):
                    if contact['email'] not in added_emails:
                        item = QListWidgetItem(f"{contact.get('name', '')} <{contact['email']}>")
                        # item.setCheckState(Qt.Checked) # Decide if recipients are auto-selected
                        self.recipients_list.addItem(item)
                        added_emails.add(contact['email'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load client contacts: {str(e)}")
            logger.error(f"Error populating recipients for client ID {self.selected_client_id}: {e}", exc_info=True)

    def populate_languages_combo(self):
        self.language_combo.clear()
        # Assuming languages are defined in CONFIG or detected
        # For now, using a fixed list plus default from CONFIG
        available_langs = CONFIG.get("available_languages", ["en", "fr", "es"]) # Example
        default_lang = CONFIG.get("language", "en")

        for lang_code in available_langs:
            self.language_combo.addItem(lang_code.upper(), lang_code)
            if lang_code == default_lang:
                self.language_combo.setCurrentText(lang_code.upper())

        # Trigger initial template population for the default/selected language
        self.populate_email_templates_combo()


    def populate_email_templates_combo(self):
        self.email_template_combo.clear()
        self.email_template_combo.addItem("Select an email template...", None)
        self.selected_language_code = self.language_combo.currentData() # Get selected lang code

        if not self.selected_language_code:
            return
        try:
            # Fetch HTML and Text email body templates for the selected language
            templates = db.get_email_body_templates(language_code=self.selected_language_code, template_type_filter='email_body_html')
            templates.extend(db.get_email_body_templates(language_code=self.selected_language_code, template_type_filter='email_body_text'))
            # Could also fetch 'email_body_word' if preview logic supports it well.

            for template in templates:
                display_name = f"{template.get('template_name', 'N/A')} ({template.get('template_type')})"
                self.email_template_combo.addItem(display_name, template.get('template_id'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load email templates: {str(e)}")
            logger.error(f"Error populating email templates for lang {self.selected_language_code}: {e}", exc_info=True)

        self.on_email_template_selected() # Clear preview if no template or lang

    def on_email_template_selected(self):
        self.selected_email_template_id = self.email_template_combo.currentData()
        self.template_preview_area.clear()
        self.subject_edit.clear()
        # self.body_edit.clear() # User might have started typing, so be careful here. Maybe only set if auto-fill is desired.

        if not self.selected_email_template_id:
            return

        logger.info(f"Email template selected: ID {self.selected_email_template_id}")
        try:
            template_details = db.get_template_by_id(self.selected_email_template_id)
            if template_details:
                self.subject_edit.setText(template_details.get('email_subject_template', ''))

                # Fetch and display content for preview
                content = db.get_email_body_template_content(self.selected_email_template_id)
                template_type = template_details.get('template_type')

                if content:
                    if content.strip().startswith("[Error:") or (template_type == 'email_body_word' and content.strip().startswith("[Plain Text Preview (")):
                        logger.warning(f"Could not load full content or fallback used for template ID {self.selected_email_template_id}. Returned content: {content}")

                    is_html_like_content = content.strip().startswith('<') and not content.strip().startswith('[')

                    if template_type in ('email_body_html', 'email_body_word') and is_html_like_content:
                        self.template_preview_area.setHtml(content)
                        self.body_edit.setHtml(content)
                    else:
                        self.template_preview_area.setPlainText(content)
                        if template_type == 'email_body_text' or (template_type == 'email_body_word' and not content.strip().startswith('[')):
                             self.body_edit.setPlainText(content)
                        elif template_type == 'email_body_word' and content.strip().startswith('[Plain Text Preview ('):
                            actual_text_content = content.split('\n\n', 1)[-1] if '\n\n' in content else content
                            self.body_edit.setPlainText(actual_text_content)
                else:
                    self.template_preview_area.setPlaceholderText("Could not load template content.")
                    self.body_edit.clear() # Clear body if no content
                    logger.warning(f"Could not load content for template ID {self.selected_email_template_id}. Content was None.")
            else:
                self.template_preview_area.setPlaceholderText("Template details not found.")
                self.body_edit.clear()
                logger.warning(f"Template details not found for ID {self.selected_email_template_id}.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load email template content: {str(e)}")
            logger.error(f"Failed to load email template content for ID {self.selected_email_template_id}: {e}", exc_info=True)

    def populate_client_documents_tree(self):
        self.client_docs_tree.clear()
        if not self.selected_client_id:
            return

        try:
            client_info = db.get_client_by_id(self.selected_client_id)
            if not client_info or not client_info.get('default_base_folder_path'):
                # Add a placeholder item indicating no folder path
                placeholder_item = QTreeWidgetItem(self.client_docs_tree, ["", "Client base folder not set.", "", ""])
                placeholder_item.setDisabled(True)
                return

            base_folder_path = client_info['default_base_folder_path']

            # Fetch documents from ClientDocuments table
            client_db_docs = db.get_documents_for_client(self.selected_client_id)

            filter_text = self.client_doc_filter_combo.currentText().lower()

            for doc_meta in client_db_docs:
                doc_name = doc_meta.get('document_name', 'Unknown Document')
                doc_type_generated = doc_meta.get('document_type_generated', 'N/A')
                file_name_on_disk = doc_meta.get('file_name_on_disk', '')
                relative_path = doc_meta.get('file_path_relative', file_name_on_disk)
                full_path = os.path.join(base_folder_path, relative_path)

                # Apply filter
                passes_filter = False
                if filter_text == "all":
                    passes_filter = True
                elif filter_text == "pdf" and file_name_on_disk.lower().endswith(".pdf"):
                    passes_filter = True
                elif filter_text == "word" and (file_name_on_disk.lower().endswith(".doc") or file_name_on_disk.lower().endswith(".docx")):
                    passes_filter = True
                elif filter_text == "excel" and (file_name_on_disk.lower().endswith(".xls") or file_name_on_disk.lower().endswith(".xlsx")):
                    passes_filter = True

                if not passes_filter:
                    continue

                item = QTreeWidgetItem(self.client_docs_tree)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(1, doc_name) # User-friendly name
                item.setText(2, doc_type_generated) # Type from DB
                item.setText(3, full_path) # Store full path for later use
                item.setData(3, Qt.UserRole, full_path) # Store full path in data role too

                # Prioritize PDFs by checking them by default (example logic)
                if file_name_on_disk.lower().endswith(".pdf"):
                     item.setCheckState(0, Qt.Checked)


        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load client documents: {str(e)}")
            logger.error(f"Error populating client documents for client ID {self.selected_client_id}: {e}", exc_info=True)


    def populate_utility_documents_tree(self):
        self.utility_docs_tree.clear()
        selected_lang = self.language_combo.currentData()
        if not selected_lang:
            placeholder_item = QTreeWidgetItem(self.utility_docs_tree, ["", "Select a language to see utility documents.", "", ""])
            placeholder_item.setDisabled(True)
            return

        try:
            utility_docs = db.get_utility_documents(language_code=selected_lang)

            if not utility_docs:
                placeholder_item = QTreeWidgetItem(self.utility_docs_tree, ["", "No utility documents found for the selected language.", "", ""])
                placeholder_item.setDisabled(True)
                return

            for doc_meta in utility_docs:
                item = QTreeWidgetItem(self.utility_docs_tree)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(1, doc_meta.get('template_name', 'N/A'))
                item.setText(2, doc_meta.get('template_type', 'N/A'))
                item.setText(3, doc_meta.get('language_code', 'N/A'))

                file_path = os.path.join(
                    CONFIG.get("templates_dir", "templates"),
                    "utility_documents",
                    selected_lang,
                    doc_meta.get('base_file_name', '')
                )
                item.setData(1, Qt.UserRole, file_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load utility documents: {str(e)}")
            logger.error(f"Error populating utility documents for lang {selected_lang}: {e}", exc_info=True)


    # Methods to Get Selected Data
    def get_selected_recipients(self) -> list[str]:
        recipients = []
        for i in range(self.recipients_list.count()):
            item = self.recipients_list.item(i)
            # Assuming format "Name <email@example.com>"
            text = item.text()
            if '<' in text and '>' in text:
                email = text[text.find('<') + 1 : text.find('>')]
                recipients.append(email)
            else: # Fallback if format is just email
                recipients.append(text)
        return recipients

    def get_selected_subject(self) -> str:
        return self.subject_edit.text()

    def get_selected_body(self) -> str:
        # Return HTML content if rich text editor, could also check a flag for plain text mode
        return self.body_edit.toHtml()

    def get_selected_attachments(self) -> list[str]:
        attachments = []
        # Client Documents
        root_client = self.client_docs_tree.invisibleRootItem()
        for i in range(root_client.childCount()):
            item = root_client.child(i)
            if item.checkState(0) == Qt.Checked:
                file_path = item.data(3, Qt.UserRole) # Path stored in column 3's UserRole
                if file_path and os.path.exists(file_path):
                    attachments.append(file_path)
                else:
                    logger.warning(f"Client attachment file path not found or invalid: {file_path if file_path else item.text(3)}")


        # Utility Documents
        root_utility = self.utility_docs_tree.invisibleRootItem()
        for i in range(root_utility.childCount()):
            item = root_utility.child(i)
            if item.checkState(0) == Qt.Checked:
                file_path = item.data(1, Qt.UserRole) # Path stored in name column's UserRole
                if file_path and os.path.exists(file_path):
                    attachments.append(file_path)
                else:
                     logger.warning(f"Utility attachment file path not found or invalid: {file_path if file_path else item.text(1)}")
        return attachments

    def accept(self):
        # Placeholder for actual send logic
        logger.info("Send button clicked (Placeholder)")
        logger.info(f"Recipients: {self.get_selected_recipients()}")
        logger.info(f"Subject: {self.get_selected_subject()}")
        # logger.debug(f"Body (HTML): {self.get_selected_body()}") # Can be very long
        logger.info(f"Attachments: {self.get_selected_attachments()}")

        # Basic validation before "sending"
        if not self.get_selected_recipients():
            QMessageBox.warning(self, "Validation Error", "Please select or verify recipients.")
            return
        if not self.get_selected_subject():
            QMessageBox.warning(self, "Validation Error", "Subject cannot be empty.")
            return
        if not self.get_selected_body().strip(): # Check if body is empty or just whitespace
             QMessageBox.warning(self, "Validation Error", "Email body cannot be empty.")
             return

        # If all good, then proceed (actual sending will be in another subtask)
        super().accept()


if __name__ == "__main__":
    # Basic logging for standalone script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')

    # Ensure DB is initialized for testing
    logger.info("Initializing database for EmailSendingDialog test...")
    db.initialize_database()
    logger.info("Database initialized.")

    # Add some sample data if it doesn't exist, for testing the dialog
    if not db.get_all_clients():
        logger.info("Adding sample client for testing...")
        db.add_client({
            'client_name': 'Test Client Co.', 'company_name': 'Test Client Company LLC',
            'project_identifier': 'TC-001', 'default_base_folder_path': './clients/test_client_co_12345',
            'created_by_user_id': 'system'
        })
        os.makedirs('./clients/test_client_co_12345', exist_ok=True)

    if db.get_all_clients() and not db.get_contacts_for_client(db.get_all_clients()[0]['client_id']):
         logger.info("Adding sample contact for testing...")
         client_id_for_contact = db.get_all_clients()[0]['client_id']
         contact_id = db.add_contact({'name': 'John Doe', 'email': 'john.doe@example.com', 'can_receive_documents': True})
         if contact_id:
             db.link_contact_to_client(client_id_for_contact, contact_id, is_primary=True, can_receive_documents=True)

    util_cat_name = "Document Utilitaires"
    if not db.get_template_category_by_name(util_cat_name):
        db.add_template_category(util_cat_name, "Utility document templates")

    if not db.get_email_body_templates(language_code='en', template_type_filter='email_body_html'):
        logger.info("Adding sample email template for 'en'...")
        email_template_dir = os.path.join(CONFIG.get("templates_dir", "templates"), "email_bodies", "en")
        os.makedirs(email_template_dir, exist_ok=True)
        dummy_html_content = "<p>Hello {{client.contact_person_name}},</p><p>This is a test email.</p>" # Changed placeholder
        dummy_html_file = "welcome_en.html"
        with open(os.path.join(email_template_dir, dummy_html_file), "w") as f:
            f.write(dummy_html_content)

        db.add_email_body_template(
            name="Welcome Email EN", template_type="email_body_html", language_code="en",
            base_file_name=dummy_html_file, description="Standard welcome email.",
            email_subject_template="Welcome to Our Service, {{client.contact_person_name}}!", # Changed placeholder
            email_variables_info='{"client.contact_person_name": "Client Contact Person Name"}'
        )

    util_cat = db.get_template_category_by_name(util_cat_name)
    if util_cat and not db.get_templates_by_category_id(util_cat['category_id']):
        logger.info("Adding sample utility document template for 'en'...")
        dummy_util_dir = os.path.join(CONFIG.get("templates_dir", "templates"), "utility_documents", "en") # Corrected subfolder
        os.makedirs(dummy_util_dir, exist_ok=True)
        dummy_util_file = "utility_catalog_en.pdf"
        try:
            if not os.path.exists(os.path.join(dummy_util_dir, dummy_util_file)):
                with open(os.path.join(dummy_util_dir, dummy_util_file), "wb") as f:
                    f.write(b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")
        except Exception as e_util_file:
            logger.error(f"Could not create dummy utility file: {e_util_file}", exc_info=True)

        db.add_utility_document_template( # Changed to use correct function
            name="Product Catalog EN",
            'template_type': "document_pdf", # Example type
            'language_code': "en",
            'base_file_name': dummy_util_file,
            'category_id': util_cat['category_id'],
            'description': "Company's product catalog."
        })


    app = QApplication(sys.argv)
    dialog = EmailSendingDialog()

    # Example of how to pass an initial client ID to the dialog if needed
    # all_clients = db.get_all_clients()
    # if all_clients:
    #     dialog.client_combo.setCurrentText(f"{all_clients[0].get('client_name', 'N/A')} ({all_clients[0].get('company_name', 'N/A')})")
        # dialog.selected_client_id = all_clients[0]['client_id']
        # dialog.on_client_selected() # Manually trigger if needed, or ensure combo's signal does it.

    dialog.show()
    sys.exit(app.exec_())
