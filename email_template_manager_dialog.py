import sys
import os
import shutil # For shutil.copy

from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QTextEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging # Added for logging

# Assuming db.py and app_config.py are in the same directory or accessible in PYTHONPATH
import db
from app_config import CONFIG

logger = logging.getLogger(__name__) # Added logger

# Placeholder for current_user_id. In a real app, this would come from an auth system.
CURRENT_USER_ID = None

class AddEditEmailBodyTemplateDialog(QDialog):
    def __init__(self, mode="add", template_data=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.template_data = template_data # For pre-filling in edit mode
        self.selected_file_path = None # To store newly selected file path for add/replace

        if self.mode == "edit" and self.template_data:
            self.setWindowTitle("Edit Email Body Template")
        else:
            self.setWindowTitle("Add New Email Body Template")

        self.setMinimumWidth(550)
        self.init_ui()

        if self.mode == "edit" and self.template_data:
            self.prefill_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.type_combo = QComboBox()
        self.subject_template_edit = QLineEdit()
        self.variables_info_edit = QTextEdit()
        self.variables_info_edit.setFixedHeight(60) # Smaller height
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.handle_browse)

        # Populate language combo
        available_langs = CONFIG.get("available_languages", ["en", "fr", "es", "ar", "pt", "tr"])
        default_lang = CONFIG.get("language", "en")
        for lang_code in available_langs:
            self.language_combo.addItem(lang_code.upper(), lang_code)
            if lang_code == default_lang and self.mode == "add": # Set default only for add mode
                self.language_combo.setCurrentText(lang_code.upper())

        # Populate type combo
        self.type_combo.addItems(["HTML", "Text", "Word DOCX"])

        form_layout.addRow(QLabel("Template Name:"), self.name_edit)
        form_layout.addRow(QLabel("Language:"), self.language_combo)
        form_layout.addRow(QLabel("Template Type:"), self.type_combo)
        form_layout.addRow(QLabel("Subject Template:"), self.subject_template_edit)
        form_layout.addRow(QLabel("Variables Info (JSON/Text):"), self.variables_info_edit)
        form_layout.addRow(QLabel("Description:"), self.description_edit)
        form_layout.addRow(QLabel("File:"), self.file_path_edit)
        form_layout.addRow("", self.browse_button)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def prefill_data(self):
        if not self.template_data:
            return
        self.name_edit.setText(self.template_data.get('template_name', ''))
        self.subject_template_edit.setText(self.template_data.get('email_subject_template', ''))
        self.variables_info_edit.setPlainText(self.template_data.get('email_variables_info', ''))
        self.description_edit.setPlainText(self.template_data.get('description', ''))

        lang_code = self.template_data.get('language_code', '')
        if lang_code:
            index = self.language_combo.findData(lang_code)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)

        db_template_type = self.template_data.get('template_type', '')
        ui_type_text = self._get_ui_text_from_db_template_type(db_template_type)
        if ui_type_text:
            self.type_combo.setCurrentText(ui_type_text)

        self.file_path_edit.setText(self.template_data.get('base_file_name', ''))
        self.browse_button.setText("Replace File...") # Change button text for edit mode

    def handle_browse(self):
        file_filter = "All Files (*)"
        current_type = self.type_combo.currentText()
        if current_type == "HTML":
            file_filter = "HTML Files (*.html *.htm);;All Files (*)"
        elif current_type == "Text":
            file_filter = "Text Files (*.txt);;All Files (*)"
        elif current_type == "Word DOCX":
            file_filter = "Word Documents (*.docx);;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Template File", "", file_filter)
        if file_path:
            self.selected_file_path = file_path
            self.file_path_edit.setText(os.path.basename(file_path))
            logger.info(f"User selected file for email template: {file_path}")
        else:
            logger.info("File selection for email template cancelled by user.")


    def _get_db_template_type(self, type_combo_text: str) -> str:
        if type_combo_text == "HTML":
            return "email_body_html"
        elif type_combo_text == "Text":
            return "email_body_text"
        elif type_combo_text == "Word DOCX":
            return "email_body_word"
        return "" # Should not happen

    def _get_ui_text_from_db_template_type(self, db_type: str) -> str:
        if db_type == "email_body_html":
            return "HTML"
        elif db_type == "email_body_text":
            return "Text"
        elif db_type == "email_body_word":
            return "Word DOCX"
        return ""

    def accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Input Error", "Template name cannot be empty.")
            logger.warning("Add/Edit Email Template validation failed: Template name empty.")
            return
        if not self.language_combo.currentData():
            QMessageBox.warning(self, "Input Error", "Please select a language.")
            logger.warning("Add/Edit Email Template validation failed: No language selected.")
            return
        if not self.type_combo.currentText():
            QMessageBox.warning(self, "Input Error", "Please select a template type.")
            logger.warning("Add/Edit Email Template validation failed: No template type selected.")
            return

        if self.mode == "add" and not self.selected_file_path:
            QMessageBox.warning(self, "Input Error", "Please select a template file for a new template.")
            logger.warning("Add Email Template validation failed: No template file selected.")
            return
        # In edit mode, self.selected_file_path might be None if user doesn't change the file.
        # self.file_path_edit will hold the existing base_file_name.

        super().accept()

    def get_data(self) -> dict | None:
        name = self.name_edit.text().strip()
        language_code = self.language_combo.currentData()
        template_type_ui_text = self.type_combo.currentText()
        actual_db_template_type = self._get_db_template_type(template_type_ui_text)
        subject = self.subject_template_edit.text().strip()
        variables = self.variables_info_edit.toPlainText().strip()
        description = self.description_edit.toPlainText().strip()

        # Determine base_file_name and source_file_path
        # If a new file was selected (for add or replace in edit)
        if self.selected_file_path:
            base_file_name = os.path.basename(self.selected_file_path)
            source_file_path_for_saving = self.selected_file_path
        elif self.mode == "edit" and self.template_data: # Edit mode, no new file selected
            base_file_name = self.template_data.get('base_file_name')
            source_file_path_for_saving = None # No new file to save from source
        else: # Add mode, but no file selected (should be caught by accept validation)
            base_file_name = None
            source_file_path_for_saving = None

        return {
            "name": name,
            "language_code": language_code,
            "template_type_str": actual_db_template_type, # Storing the DB compatible type string
            "subject": subject,
            "variables": variables,
            "description": description,
            "source_file_path": source_file_path_for_saving,
            "base_file_name": base_file_name # This will be used for db storage
        }

class EmailBodyTemplateManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Body Template Management")
        self.setMinimumSize(1000, 700)
        self.init_ui()
        self.populate_templates_tree()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.templates_tree = QTreeWidget()
        self.templates_tree.setHeaderLabels(["ID", "Name", "Language", "Type", "Subject Template", "File Name"])
        self.templates_tree.setColumnHidden(0, True) # Hide ID column
        self.templates_tree.setColumnWidth(1, 200) # Name
        self.templates_tree.setColumnWidth(2, 80)  # Language
        self.templates_tree.setColumnWidth(3, 120) # Type
        self.templates_tree.setColumnWidth(4, 250) # Subject
        self.templates_tree.setColumnWidth(5, 150) # File Name
        main_layout.addWidget(self.templates_tree)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New...")
        self.add_button.clicked.connect(self.handle_add_new)

        self.edit_button = QPushButton("Edit Info...")
        self.edit_button.clicked.connect(self.handle_edit_selected)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.handle_delete_selected)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: (logger.info("User triggered refresh of the email template list."), self.populate_templates_tree()))

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.close_button)
        main_layout.addLayout(buttons_layout)

    def _get_ui_text_from_db_template_type(self, db_type: str) -> str:
        # Helper to convert DB type to UI display string, mirrors dialog's helper
        if db_type == "email_body_html": return "HTML"
        if db_type == "email_body_text": return "Text"
        if db_type == "email_body_word": return "Word DOCX"
        return db_type # Fallback

    def populate_templates_tree(self):
        self.templates_tree.clear()
        try:
            # Fetch all email body templates (HTML, Text, Word)
            all_email_templates = []
            available_langs = CONFIG.get("available_languages", ["en", "fr", "es", "ar", "pt", "tr"])

            for lang_code in available_langs:
                for type_filter in ["email_body_html", "email_body_text", "email_body_word"]:
                    templates_of_type = db.get_email_body_templates(language_code=lang_code, template_type_filter=type_filter)
                    if templates_of_type: # Check if None was returned or list is empty
                        all_email_templates.extend(templates_of_type)

            # Sort templates, e.g., by name then language, if desired
            all_email_templates.sort(key=lambda x: (x.get('template_name', '').lower(), x.get('language_code', '')))

            for template in all_email_templates:
                item = QTreeWidgetItem(self.templates_tree)
                item.setText(0, str(template.get('template_id', ''))) # Hidden ID
                item.setText(1, template.get('template_name', 'N/A'))
                item.setText(2, template.get('language_code', 'N/A').upper())
                item.setText(3, self._get_ui_text_from_db_template_type(template.get('template_type', 'N/A')))
                item.setText(4, template.get('email_subject_template', ''))
                item.setText(5, template.get('base_file_name', 'N/A'))

                item.setData(0, Qt.UserRole, template.get('template_id'))
                item.setData(1, Qt.UserRole, template.get('language_code'))
                item.setData(2, Qt.UserRole, template.get('base_file_name'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load email templates: {str(e)}")
            logger.error("Failed to populate email templates tree.", exc_info=True)

    def handle_add_new(self):
        logger.info("Attempting to add new email template.")
        dialog = AddEditEmailBodyTemplateDialog(mode="add", parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data or not data.get('source_file_path'):
                QMessageBox.warning(self, "Error", "No file was selected for the new template.")
                logger.warning("Add new email template failed: No file selected.")
                return

            target_base_name = data['base_file_name'] # Already os.path.basename from dialog

            # Save the physical file
            # save_general_document_file expects: source_path, subfolder, lang, target_name
            saved_file_full_path = db.save_general_document_file(
                source_file_path=data['source_file_path'],
                document_type_subfolder="email_bodies", # Correct subfolder
                language_code=data['language_code'],
                target_base_name=target_base_name
            )

            if saved_file_full_path:
                template_id = db.add_email_body_template(
                    name=data['name'],
                    template_type=data['template_type_str'], # DB compatible type from dialog
                    language_code=data['language_code'],
                    base_file_name=target_base_name,
                    description=data['description'],
                    email_subject_template=data['subject'],
                    email_variables_info=data['variables'],
                    created_by_user_id=CURRENT_USER_ID
                )
                if template_id:
                    QMessageBox.information(self, "Success", "Email body template added successfully.")
                        logger.info(f"Successfully added email template: {data['name']}")
                    self.populate_templates_tree()
                else:
                    QMessageBox.warning(self, "DB Error", "Failed to add template metadata to database.")
                        logger.error(f"Failed to add email template metadata to DB for: {data['name']}", exc_info=True)
                    # Attempt to delete the file if DB entry failed
                        logger.info(f"Attempting to delete orphaned file: {target_base_name} for email template.")
                    db.delete_general_document_file("email_bodies", data['language_code'], target_base_name)
            else:
                QMessageBox.warning(self, "File Error", "Failed to save template file.")
                    logger.error(f"Failed to save email template file: {target_base_name}", exc_info=True)
        else: # Dialog cancelled
            logger.info("Add new email template cancelled by user.")


    def handle_edit_selected(self):
        selected_item = self.templates_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a template to edit.")
            logger.warning("Edit email template attempt failed: No item selected.")
            return

        template_id = selected_item.data(0, Qt.UserRole)
        if template_id is None: return

        logger.info(f"Attempting to edit email template ID: {template_id}")
        current_template_data = db.get_template_by_id(template_id)
        if not current_template_data:
            QMessageBox.critical(self, "Error", f"Could not retrieve data for template ID: {template_id}")
            logger.error(f"Could not retrieve data for template ID: {template_id} for edit.", exc_info=True)
            return

        dialog = AddEditEmailBodyTemplateDialog(mode="edit", template_data=current_template_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()

            update_payload = {
                'template_name': new_data['name'],
                'language_code': new_data['language_code'], # Language might change
                'template_type': new_data['template_type_str'], # Type might change
                'email_subject_template': new_data['subject'],
                'email_variables_info': new_data['variables'],
                'description': new_data['description']
            }

            file_changed = False
            if new_data['source_file_path'] and new_data['base_file_name']: # A new file was selected
                # New file handling: delete old, save new, update base_file_name in payload
                old_lang = current_template_data.get('language_code')
                old_base_name = current_template_data.get('base_file_name')
                if old_lang and old_base_name:
                    db.delete_general_document_file("email_bodies", old_lang, old_base_name)

                new_base_name = new_data['base_file_name']
                saved_path = db.save_general_document_file(
                    new_data['source_file_path'],
                    "email_bodies",
                    new_data['language_code'], # Use new language for path
                    new_base_name
                )
                if saved_path:
                    update_payload['base_file_name'] = new_base_name
                    file_changed = True
                else:
                    QMessageBox.warning(self, "File Error", "Failed to save the replaced template file. Metadata not updated.")
                    logger.error(f"File operation failed during edit for template ID {template_id}.", exc_info=True)
                    return

            if not file_changed and new_data['language_code'] != current_template_data.get('language_code'):
                 QMessageBox.warning(self, "Warning", f"Template language changed, but the file was not replaced. The file remains in the old language ('{current_template_data.get('language_code')}') folder.")
                 logger.warning(f"Template language changed for ID {template_id} without file replacement. File system may be inconsistent.")

            if db.update_template(template_id, update_payload):
                QMessageBox.information(self, "Success", "Template information updated.")
                logger.info(f"Successfully updated email template ID: {template_id}")
                self.populate_templates_tree()
            else:
                QMessageBox.warning(self, "DB Error", "Failed to update template information.")
                logger.error(f"Failed to update email template metadata in DB for ID: {template_id}", exc_info=True)
        else: # Dialog cancelled
            logger.info(f"Edit email template ID: {template_id} cancelled by user.")


    def handle_delete_selected(self):
        selected_item = self.templates_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a template to delete.")
            logger.warning("Delete email template attempt failed: No item selected.")
            return

        template_id = selected_item.data(0, Qt.UserRole)
        lang_code = selected_item.data(1, Qt.UserRole)
        base_name = selected_item.data(2, Qt.UserRole)

        if template_id is None or lang_code is None or base_name is None:
            QMessageBox.critical(self, "Error", "Selected item data is incomplete for deletion.")
            logger.error("Selected email template item data is incomplete for deletion.")
            return

        logger.info(f"Attempting to delete email template ID: {template_id}, File: {base_name}, Lang: {lang_code}")
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete template '{selected_item.text(1)}' ({base_name})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            file_deleted_successfully = db.delete_general_document_file("email_bodies", lang_code, base_name)

            if file_deleted_successfully:
                if db.delete_template(template_id):
                    QMessageBox.information(self, "Success", "Email template and its file deleted.")
                    logger.info(f"Successfully deleted email template ID: {template_id} (file and DB entry).")
                    self.populate_templates_tree()
                else:
                    QMessageBox.warning(self, "DB Error", "Failed to delete template metadata from database, but file may have been deleted.")
                    logger.error(f"Failed to delete email template metadata from DB for ID: {template_id}", exc_info=True)
            else:
                QMessageBox.warning(self, "File Error", f"Error deleting template file '{base_name}'. Database record not deleted.")
                logger.error(f"Failed to delete email template file: {base_name} for lang {lang_code}", exc_info=True) # This log might be redundant if db.delete_general_document_file logs it already
        else:
            logger.info(f"Delete email template ID: {template_id} cancelled by user.")


if __name__ == "__main__":
    # Basic logging setup for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    app = QApplication(sys.argv)
    db.initialize_database()

    email_cat = db.get_template_category_by_name("Modèles Email")
    if not email_cat:
        db.add_template_category("Modèles Email", "Modèles pour les corps des emails et sujets.")
        logger.info("Manually created 'Modèles Email' category for test.")

    if not db.get_email_body_templates(language_code='en', template_type_filter='email_body_html'):
        logger.info("Adding sample HTML email template for 'en' for testing dialog...")
        email_bodies_dir = os.path.join(CONFIG.get("templates_dir", "templates"), "email_bodies", "en")
        os.makedirs(email_bodies_dir, exist_ok=True)
        dummy_html_file_name = "test_welcome_en.html"
        dummy_html_file_path = os.path.join(email_bodies_dir, dummy_html_file_name)

        if not os.path.exists(dummy_html_file_path):
            with open(dummy_html_file_path, "w", encoding="utf-8") as f:
                f.write("<h1>Welcome {{client.name}}!</h1><p>This is a test HTML template.</p>")

        db.add_email_body_template(
            name="Test Welcome HTML EN", template_type="email_body_html", language_code="en",
            base_file_name=dummy_html_file_name, description="A test welcome email in HTML for English.",
            email_subject_template="Welcome, {{client.name}}!",
            email_variables_info='{"client.name": "Client Full Name"}'
        )

    dialog = EmailBodyTemplateManagerDialog()
    dialog.show()
    sys.exit(app.exec_())
