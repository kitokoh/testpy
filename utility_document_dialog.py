import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging # Added for logging

# Assuming db.py and app_config.py are in the same directory or accessible in PYTHONPATH
import db
from app_config import CONFIG # For CONFIG.get("templates_dir")

logger = logging.getLogger(__name__) # Added logger

# Placeholder for current_user_id. In a real app, this would come from an auth system.
CURRENT_USER_ID = None

class AddEditUtilityDocDialog(QDialog):
    def __init__(self, parent=None, template_data=None):
        super().__init__(parent)
        self.template_data = template_data # For pre-filling in edit mode
        self.source_file_path = None # To store selected file path

        self.setWindowTitle("Add/Edit Utility Document")
        self.setMinimumWidth(500)
        self.init_ui()
        if self.template_data:
            self.prefill_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.handle_browse)

        # Populate language combo
        # Using a fixed list for now, can be dynamic from CONFIG or db later
        available_langs = CONFIG.get("available_languages", ["en", "fr", "es", "ar", "pt", "tr"])
        for lang_code in available_langs:
            self.language_combo.addItem(lang_code.upper(), lang_code)
        default_lang = CONFIG.get("language", "en")
        if default_lang in available_langs:
            self.language_combo.setCurrentText(default_lang.upper())


        form_layout.addRow(QLabel("Document Name:"), self.name_edit)
        form_layout.addRow(QLabel("Language:"), self.language_combo)
        form_layout.addRow(QLabel("Description:"), self.description_edit)
        form_layout.addRow(QLabel("File:"), self.file_path_edit)
        form_layout.addRow("", self.browse_button)

        layout.addLayout(form_layout)

        # Dialog buttons
        self.buttons = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_data)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons.addStretch()
        self.buttons.addWidget(self.ok_button)
        self.buttons.addWidget(self.cancel_button)
        layout.addLayout(self.buttons)

    def prefill_data(self):
        if not self.template_data:
            return
        self.name_edit.setText(self.template_data.get('template_name', ''))
        self.description_edit.setPlainText(self.template_data.get('description', ''))

        lang_code = self.template_data.get('language_code', '')
        if lang_code:
            index = self.language_combo.findData(lang_code)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)

        # In edit mode, file path is usually not changed directly this way
        # but shown for reference. The actual file remains.
        self.file_path_edit.setText(self.template_data.get('base_file_name', ''))
        self.browse_button.setEnabled(False) # Disable browse in edit mode for metadata

    def handle_browse(self):
        # In add mode, allow selecting a file.
        # Filter for common document types.
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document File", "",
            "Documents (*.pdf *.docx *.xlsx *.doc *.xls *.txt);;All Files (*)"
        )
        if file_path:
            self.source_file_path = file_path
            self.file_path_edit.setText(os.path.basename(file_path))
            logger.info(f"User selected file for utility document: {file_path}")
        else:
            logger.info("File selection for utility document cancelled by user.")


    def accept_data(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Input Error", "Document name cannot be empty.")
            logger.warning("Add/Edit Utility Doc validation failed: Document name empty.")
            return
        if not self.language_combo.currentData():
            QMessageBox.warning(self, "Input Error", "Please select a language.")
            logger.warning("Add/Edit Utility Doc validation failed: No language selected.")
            return

        # In add mode, file path is required. In edit, it's not being changed by this dialog.
        if not self.template_data and not self.source_file_path:
            QMessageBox.warning(self, "Input Error", "Please select a document file.")
            logger.warning("Add Utility Doc validation failed: No document file selected.")
            return

        super().accept() # Proceed to accept the dialog

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "language_code": self.language_combo.currentData(),
            "description": self.description_edit.toPlainText().strip(),
            "source_file_path": self.source_file_path, # Path to the original file on user's system (for add)
            "base_file_name": os.path.basename(self.source_file_path) if self.source_file_path else (self.template_data.get('base_file_name') if self.template_data else None)
        }


class UtilityDocumentManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Utility Document Management")
        self.setMinimumSize(900, 600)
        self.init_ui()
        self.populate_docs_tree()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Tree widget for displaying documents
        self.docs_tree = QTreeWidget()
        self.docs_tree.setHeaderLabels(["Name", "Language", "File Name", "Description", "Type"])
        self.docs_tree.setColumnWidth(0, 200) # Name
        self.docs_tree.setColumnWidth(1, 80)  # Language
        self.docs_tree.setColumnWidth(2, 150) # File Name
        self.docs_tree.setColumnWidth(3, 250) # Description
        self.docs_tree.setColumnWidth(4, 100) # Type
        main_layout.addWidget(self.docs_tree)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New...")
        self.add_button.clicked.connect(self.handle_add_new)

        self.edit_button = QPushButton("Edit Info...")
        self.edit_button.clicked.connect(self.handle_edit_info)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.handle_delete)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: (logger.info("User triggered refresh of the utility document list."), self.populate_docs_tree())) # Added logging for refresh

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.close_button)
        main_layout.addLayout(buttons_layout)

    def populate_docs_tree(self):
        self.docs_tree.clear()
        try:
            # For now, load all languages. A language filter combo could be added.
            utility_docs = db.get_utility_documents()
            for doc in utility_docs:
                item = QTreeWidgetItem(self.docs_tree)
                item.setText(0, doc.get('template_name', 'N/A'))
                item.setText(1, doc.get('language_code', 'N/A'))
                item.setText(2, doc.get('base_file_name', 'N/A'))
                item.setText(3, doc.get('description', ''))
                item.setText(4, doc.get('template_type', 'N/A'))
                item.setData(0, Qt.UserRole, doc.get('template_id')) # Store template_id
                # Store other data needed for delete/edit if necessary
                item.setData(1, Qt.UserRole, doc.get('language_code'))
                item.setData(2, Qt.UserRole, doc.get('base_file_name'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load utility documents: {str(e)}")
            logger.error("Failed to populate utility documents tree.", exc_info=True)

    def handle_add_new(self):
        logger.info("Attempting to add new utility document.")
        dialog = AddEditUtilityDocDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()

            source_file_path = data['source_file_path']
            lang_code = data['language_code']
            doc_name_for_db = data['name']
            description_for_db = data['description']
            target_base_name = data['base_file_name'] # This is os.path.basename(source_file_path)

            if not target_base_name: # Should be caught by AddEditUtilityDocDialog, but double check
                QMessageBox.warning(self, "Input Error", "No file selected or file name is invalid.")
                logger.warning("Add new utility document failed: No file selected or file name invalid.")
                return

            document_type_subfolder = "utility_documents"

            # Construct potential target path and check for existence
            potential_target_path = os.path.join(
                CONFIG.get("templates_dir", "templates"),
                document_type_subfolder,
                lang_code,
                target_base_name
            )

            proceed_with_save = True
            if os.path.exists(potential_target_path):
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"A file named '{target_base_name}' already exists for language '{lang_code.upper()}'.\n\nOverwrite?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    proceed_with_save = False

            if proceed_with_save:
                saved_file_full_path = db.save_general_document_file(
                    source_file_path=source_file_path,
                    document_type_subfolder=document_type_subfolder,
                    language_code=lang_code,
                    target_base_name=target_base_name
                )

                if saved_file_full_path:
                    template_id = db.add_utility_document_template(
                        name=doc_name_for_db,
                        language_code=lang_code,
                        base_file_name=target_base_name,
                        description=description_for_db,
                        created_by_user_id=CURRENT_USER_ID
                    )
                    if template_id:
                        QMessageBox.information(self, "Success", "Utility document added successfully.")
                        logger.info(f"Successfully added utility document: {data['name']}")
                        self.populate_docs_tree()
                    else:
                        QMessageBox.warning(self, "DB Error", "Failed to add utility document metadata to database.")
                        logger.error(f"Failed to add utility document metadata to DB for: {data['name']}", exc_info=True)
                        # If DB entry fails after successful file save, attempt to delete the just-saved file
                        logger.info(f"Attempting to delete orphaned file: {target_base_name} in {lang_code}/{document_type_subfolder}")
                        db.delete_general_document_file(document_type_subfolder, lang_code, target_base_name)
                else:
                    QMessageBox.warning(self, "File Error", "Failed to save document file.")
                    logger.error(f"Failed to save utility document file: {target_base_name} to path {potential_target_path}", exc_info=True)
            else:
                QMessageBox.information(self, "Cancelled", "Add document operation cancelled by user.")
                logger.info("Add new utility document cancelled by user.")


    def handle_edit_info(self):
        selected_item = self.docs_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a document to edit.")
            logger.warning("Edit utility document attempt failed: No item selected.")
            return

        template_id = selected_item.data(0, Qt.UserRole)
        if template_id is None:
            QMessageBox.critical(self, "Error", "Invalid item selected (no template ID).")
            logger.error("Edit utility document failed: Invalid item selected (no template ID).")
            return

        logger.info(f"Attempting to edit utility document ID: {template_id}")
        current_template_data = db.get_template_by_id(template_id)
        if not current_template_data:
            QMessageBox.critical(self, "Error", f"Could not retrieve template data for ID: {template_id}")
            logger.error(f"Could not retrieve template data for ID: {template_id} for edit.", exc_info=True)
            return

        dialog = AddEditUtilityDocDialog(self, template_data=current_template_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()

            # For "edit info", we are not changing the file, only metadata.
            # Language change might imply file path change - for simplicity, this is not handled here.
            # User should delete and re-add if file or its direct path (lang folder) needs change.
            update_payload = {
                'template_name': data['name'],
                'description': data['description'],
                'language_code': data['language_code']
                # base_file_name and template_type are not changed in "edit info" mode
            }

            if db.update_template(template_id, update_payload):
                QMessageBox.information(self, "Success", "Document information updated.")
                logger.info(f"Successfully updated utility document ID: {template_id}")
                self.populate_docs_tree()
            else:
                QMessageBox.warning(self, "DB Error", "Failed to update document information.")
                logger.error(f"Failed to update utility document metadata in DB for ID: {template_id}", exc_info=True)
        else: # Dialog cancelled
            logger.info(f"Edit utility document ID: {template_id} cancelled by user.")


    def handle_delete(self):
        selected_item = self.docs_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a document to delete.")
            logger.warning("Delete utility document attempt failed: No item selected.")
            return

        template_id = selected_item.data(0, Qt.UserRole)
        lang_code = selected_item.data(1, Qt.UserRole) # Stored language
        base_name = selected_item.data(2, Qt.UserRole) # Stored base_file_name

        if template_id is None or lang_code is None or base_name is None:
            QMessageBox.critical(self, "Error", "Selected item data is incomplete.")
            logger.error("Selected utility document item data is incomplete for deletion.")
            return

        logger.info(f"Attempting to delete utility document ID: {template_id}, File: {base_name}, Lang: {lang_code}")
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete '{selected_item.text(0)}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            file_deleted = db.delete_general_document_file(
                document_type_subfolder="utility_documents",
                language_code=lang_code,
                base_file_name=base_name
            )

            if file_deleted:
                if db.delete_template(template_id):
                    QMessageBox.information(self, "Success", "Utility document and its file deleted.")
                    logger.info(f"Successfully deleted utility document ID: {template_id} (file and DB entry).")
                    self.populate_docs_tree()
                else:
                    QMessageBox.warning(self, "DB Error", "Failed to delete document metadata from database, but file may have been deleted.")
                    logger.error(f"Failed to delete utility document metadata from DB for ID: {template_id}", exc_info=True)
            else:
                QMessageBox.warning(self, "File Error", f"Failed to delete the document file '{base_name}'. Database record was not deleted.")
                logger.error(f"Failed to delete utility document file: {base_name} for lang {lang_code}", exc_info=True)
        else:
            logger.info(f"Delete utility document ID: {template_id} cancelled by user.")


if __name__ == "__main__":
    # Basic logging setup for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    app = QApplication(sys.argv)
    db.initialize_database()

    util_docs_en = db.get_utility_documents(language_code='en')
    if not util_docs_en:
        logger.info("Adding sample utility document for 'en' for testing dialog...")
        dummy_util_dir = os.path.join(CONFIG.get("templates_dir", "templates"), "utility_documents", "en")
        os.makedirs(dummy_util_dir, exist_ok=True)
        dummy_pdf_file = "sample_catalog_en.pdf"
        dummy_pdf_path = os.path.join(dummy_util_dir, dummy_pdf_file)
        try:
            if not os.path.exists(dummy_pdf_path):
                with open(dummy_pdf_path, "wb") as f:
                    f.write(b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

            db.add_utility_document_template(
                name="Sample Catalog EN", language_code="en", base_file_name=dummy_pdf_file,
                description="A sample product catalog in English.", created_by_user_id=CURRENT_USER_ID
            )
        except Exception as e:
            logger.error(f"Error adding sample utility document: {e}", exc_info=True)

    dialog = UtilityDocumentManagerDialog()
    dialog.show()
    sys.exit(app.exec_())
