# partners/partner_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
                             QMessageBox, QDialogButtonBox, QGroupBox, QTableWidget,
                             QTableWidgetItem, QHBoxLayout, QTextEdit, QListWidget, QListWidgetItem,
                             QTabWidget, QHeaderView, QAbstractItemView, QFileDialog, QDesktopServices, QInputDialog, QWidget) # Added QTabWidget and other necessary widgets
from PyQt5.QtCore import Qt, QUrl
import db.crud as db_manager
import os
import shutil
from datetime import datetime

# Try to import db_config for PARTNERS_DOCUMENTS_DIR, use fallback if not found
try:
    import db_config
    PARTNERS_DOCUMENTS_BASE_DIR = db_config.PARTNERS_DOCUMENTS_DIR
except ImportError:
    PARTNERS_DOCUMENTS_BASE_DIR = 'partners_documents/' # Fallback directory
    if not os.path.exists(PARTNERS_DOCUMENTS_BASE_DIR):
        try:
            os.makedirs(PARTNERS_DOCUMENTS_BASE_DIR, exist_ok=True)
        except OSError as e:
            # This is a fallback, so print an error and continue.
            # The application might not function correctly for document storage.
            print(f"Error creating fallback documents directory: {e}")


class PartnerDialog(QDialog):
    def __init__(self, partner_id=None, parent=None):
        super().__init__(parent)
        self.partner_id = partner_id
        self.setWindowTitle(f"{'Edit' if partner_id else 'Add'} Partner")
        self.setMinimumWidth(700) # Increased width for tabs
        self.setMinimumHeight(500)

        self.original_contacts = []
        self.deleted_contact_ids = set()

        main_layout = QVBoxLayout(self)

        # Tab Widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Partner Details Tab ---
        details_tab_widget = QWidget() # Create a new widget for the first tab's content
        details_tab_layout = QVBoxLayout(details_tab_widget)

        # Partner Details Form
        details_group = QGroupBox("Partner Details")
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        form_layout.addRow("Name*:", self.name_input)
        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)
        self.phone_input = QLineEdit()
        form_layout.addRow("Phone:", self.phone_input)
        self.address_input = QLineEdit()
        form_layout.addRow("Address:", self.address_input)
        self.location_input = QLineEdit()
        form_layout.addRow("Location:", self.location_input)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        form_layout.addRow("Notes:", self.notes_input)
        details_group.setLayout(form_layout)
        details_tab_layout.addWidget(details_group)

        # Contacts Management
        contacts_group = QGroupBox("Contacts")
        contacts_layout = QVBoxLayout()
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(4)
        self.contacts_table.setHorizontalHeaderLabels(["Name*", "Email", "Phone", "Role"])
        self.contacts_table.horizontalHeader().setStretchLastSection(True)
        contacts_layout.addWidget(self.contacts_table)
        contacts_buttons_layout = QHBoxLayout()
        self.add_contact_button = QPushButton("Add Contact")
        self.remove_contact_button = QPushButton("Remove Selected Contact")
        contacts_buttons_layout.addWidget(self.add_contact_button)
        contacts_buttons_layout.addWidget(self.remove_contact_button)
        contacts_layout.addLayout(contacts_buttons_layout)
        contacts_group.setLayout(contacts_layout)
        details_tab_layout.addWidget(contacts_group)

        # Categories Management
        categories_group = QGroupBox("Assign Categories")
        categories_layout = QVBoxLayout()
        self.categories_list_widget = QListWidget()
        categories_layout.addWidget(self.categories_list_widget)
        categories_group.setLayout(categories_layout)
        details_tab_layout.addWidget(categories_group)

        details_tab_widget.setLayout(details_tab_layout) # Set the layout for the details tab widget
        self.tab_widget.addTab(details_tab_widget, "Partner Details")

        # --- Documents Tab ---
        documents_tab_widget = QWidget()
        documents_tab_layout = QVBoxLayout(documents_tab_widget)

        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(5) # document_id (hidden), Name, Type, Description, Date Added
        self.documents_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Description", "Date Added"])
        self.documents_table.setColumnHidden(0, True) # Hide document_id column
        self.documents_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name
        self.documents_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Type
        self.documents_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Description
        self.documents_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Date
        self.documents_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.documents_table.setSelectionMode(QAbstractItemView.SingleSelection)
        documents_tab_layout.addWidget(self.documents_table)

        doc_buttons_layout = QHBoxLayout()
        self.upload_doc_button = QPushButton("Upload Document")
        self.download_doc_button = QPushButton("Download Document")
        self.delete_doc_button = QPushButton("Delete Document")
        doc_buttons_layout.addWidget(self.upload_doc_button)
        doc_buttons_layout.addWidget(self.download_doc_button)
        doc_buttons_layout.addWidget(self.delete_doc_button)
        documents_tab_layout.addLayout(doc_buttons_layout)

        documents_tab_widget.setLayout(documents_tab_layout)
        self.tab_widget.addTab(documents_tab_widget, "Documents")

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        # Connect signals
        self.button_box.accepted.connect(self.accept_dialog)
        self.button_box.rejected.connect(self.reject)
        self.add_contact_button.clicked.connect(self.add_contact_row)
        self.remove_contact_button.clicked.connect(self.remove_contact_row)
        self.upload_doc_button.clicked.connect(self.handle_upload_document)
        self.download_doc_button.clicked.connect(self.handle_download_document)
        self.delete_doc_button.clicked.connect(self.handle_delete_document)

        if self.partner_id:
            self.load_partner_data() # This will also call load_partner_documents
            self.load_contacts()
        else:
            # New partner, disable document buttons until partner is saved
            self.upload_doc_button.setEnabled(False)
            self.download_doc_button.setEnabled(False)
            self.delete_doc_button.setEnabled(False)
            self.documents_table.setEnabled(False)

        self.load_and_set_partner_categories()

    def load_partner_data(self):
        if not self.partner_id:
            # Disable document buttons if it's a new partner (no ID yet)
            self.upload_doc_button.setEnabled(False)
            self.download_doc_button.setEnabled(False)
            self.delete_doc_button.setEnabled(False)
            self.documents_table.setEnabled(False)
            return

        partner = db_manager.get_partner_by_id(self.partner_id)
        if partner:
            self.name_input.setText(partner.get('name', ''))
            self.email_input.setText(partner.get('email', ''))
            self.phone_input.setText(partner.get('phone', ''))
            self.address_input.setText(partner.get('address', ''))
            self.location_input.setText(partner.get('location', ''))
            self.notes_input.setPlainText(partner.get('notes', ''))

            # Enable document buttons as partner exists
            self.upload_doc_button.setEnabled(True)
            self.download_doc_button.setEnabled(True)
            self.delete_doc_button.setEnabled(True)
            self.documents_table.setEnabled(True)
            self.load_partner_documents() # Load documents after partner data is loaded

    def load_partner_documents(self):
        if not self.partner_id:
            self.documents_table.setRowCount(0)
            return

        self.documents_table.setRowCount(0) # Clear existing rows
        documents = db_manager.get_documents_for_partner(self.partner_id)
        if documents:
            for doc in documents:
                row_position = self.documents_table.rowCount()
                self.documents_table.insertRow(row_position)

                doc_id_item = QTableWidgetItem(doc.get('document_id'))
                # Store file_path_relative in UserRole of the ID item for download/delete
                doc_id_item.setData(Qt.UserRole, doc.get('file_path_relative'))

                name_item = QTableWidgetItem(doc.get('document_name'))
                type_item = QTableWidgetItem(doc.get('document_type'))
                desc_item = QTableWidgetItem(doc.get('description'))

                created_at_str = doc.get('created_at', '')
                date_added_item = QTableWidgetItem(created_at_str)
                try: # Try to parse and format date nicely
                    dt_obj = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    date_added_item.setText(dt_obj.strftime('%Y-%m-%d %H:%M'))
                except ValueError:
                    pass # Keep original string if parsing fails

                self.documents_table.setItem(row_position, 0, doc_id_item)
                self.documents_table.setItem(row_position, 1, name_item)
                self.documents_table.setItem(row_position, 2, type_item)
                self.documents_table.setItem(row_position, 3, desc_item)
                self.documents_table.setItem(row_position, 4, date_added_item)

        # Enable/disable download/delete based on selection
        self.documents_table.itemSelectionChanged.connect(self.update_document_button_states)
        self.update_document_button_states()


    def update_document_button_states(self):
        has_selection = bool(self.documents_table.selectedItems())
        # Upload button enabled if partner exists (handled in load_partner_data)
        # self.upload_doc_button.setEnabled(bool(self.partner_id))
        self.download_doc_button.setEnabled(has_selection and bool(self.partner_id))
        self.delete_doc_button.setEnabled(has_selection and bool(self.partner_id))


    def handle_upload_document(self):
        if not self.partner_id:
            QMessageBox.warning(self, "Partner Not Saved", "Please save the partner before uploading documents.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Document to Upload")
        if not file_path:
            return

        original_filename = os.path.basename(file_path)

        doc_type, ok = QInputDialog.getText(self, "Document Type", "Enter document type (e.g., Contract, Invoice):")
        if not ok: # User cancelled
            return
        doc_type = doc_type.strip() if doc_type else "Other"


        description, ok = QInputDialog.getText(self, "Document Description", "Enter an optional description:")
        if not ok: # User cancelled
             description = "" # Allow empty description if user cancels this specific dialog but not the overall upload
        description = description.strip()


        target_partner_dir = os.path.join(PARTNERS_DOCUMENTS_BASE_DIR, self.partner_id)
        try:
            os.makedirs(target_partner_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Directory Error", f"Could not create directory: {target_partner_dir}\n{e}")
            return

        # Ensure unique filename in target directory (simple append counter if exists)
        # This is a basic approach. More robust would be UUID filenames or checking db for file_path_relative.
        target_filename = original_filename
        counter = 1
        while os.path.exists(os.path.join(target_partner_dir, target_filename)):
            name, ext = os.path.splitext(original_filename)
            target_filename = f"{name}_{counter}{ext}"
            counter += 1

        target_file_path_full = os.path.join(target_partner_dir, target_filename)
        file_path_relative_for_db = target_filename # Store only filename as relative path for this partner

        try:
            shutil.copy(file_path, target_file_path_full)
        except IOError as e:
            QMessageBox.critical(self, "File Error", f"Could not copy file: {e}")
            return

        doc_data = {
            'partner_id': self.partner_id,
            'document_name': original_filename, # Store original filename for display
            'file_path_relative': file_path_relative_for_db, # Store potentially modified name used on disk
            'document_type': doc_type,
            'description': description
        }

        new_doc_id = db_manager.add_partner_document(doc_data)
        if new_doc_id:
            QMessageBox.information(self, "Success", "Document uploaded successfully.")
            self.load_partner_documents()
        else:
            QMessageBox.critical(self, "Database Error", "Failed to record document in database.")
            # Clean up copied file if DB record failed
            if os.path.exists(target_file_path_full):
                try:
                    os.remove(target_file_path_full)
                except OSError as e_remove:
                    print(f"Error cleaning up file after DB failure: {e_remove}")


    def handle_download_document(self):
        selected_rows = self.documents_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Document Selected", "Please select a document to download.")
            return

        selected_row = selected_rows[0].row()
        doc_id_item = self.documents_table.item(selected_row, 0) # ID is in hidden column 0

        if not doc_id_item: return # Should not happen if row is selected

        file_path_relative = doc_id_item.data(Qt.UserRole)

        if not file_path_relative:
            QMessageBox.critical(self, "File Error", "File path not found for this document.")
            return

        full_path = os.path.join(PARTNERS_DOCUMENTS_BASE_DIR, self.partner_id, file_path_relative)

        if os.path.exists(full_path):
            # Ask user where to save the file
            save_file_name, _ = QFileDialog.getSaveFileName(self, "Save Document As...", os.path.basename(full_path))
            if save_file_name:
                try:
                    shutil.copy(full_path, save_file_name)
                    QMessageBox.information(self, "Download Complete", f"File saved to: {save_file_name}")
                    # Optionally open the folder containing the saved file
                    # QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(save_file_name)))
                except shutil.Error as e:
                    QMessageBox.critical(self, "Save Error", f"Could not save file: {e}")
            # else: User cancelled SaveAs dialog
        else:
            QMessageBox.critical(self, "File Not Found", f"The document file could not be found at: {full_path}")


    def handle_delete_document(self):
        selected_rows = self.documents_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Document Selected", "Please select a document to delete.")
            return

        selected_row = selected_rows[0].row()
        doc_id_item = self.documents_table.item(selected_row, 0) # ID is in hidden column 0
        doc_name_item = self.documents_table.item(selected_row, 1) # Name for confirmation

        if not doc_id_item or not doc_name_item: return

        document_id_to_delete = doc_id_item.text()
        file_path_relative = doc_id_item.data(Qt.UserRole)
        doc_name_for_confirm = doc_name_item.text()

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the document '{doc_name_for_confirm}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            full_file_path = os.path.join(PARTNERS_DOCUMENTS_BASE_DIR, self.partner_id, file_path_relative)

            file_deleted_ok = False
            if os.path.exists(full_file_path):
                try:
                    os.remove(full_file_path)
                    file_deleted_ok = True
                except OSError as e:
                    QMessageBox.warning(self, "File Deletion Error", f"Could not delete file: {full_file_path}\n{e}")
                    # Ask if user wants to proceed with DB deletion anyway
                    proceed_reply = QMessageBox.question(self, "Database Deletion",
                                                         "File deletion failed. Delete database record anyway?",
                                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if proceed_reply == QMessageBox.No:
                        return
            else:
                # File doesn't exist, maybe it was deleted manually. Still allow DB record deletion.
                print(f"File not found for deletion: {full_file_path}. Proceeding with DB record deletion.")
                file_deleted_ok = True # Consider it "ok" in terms of allowing DB delete

            if file_deleted_ok: # If file deletion was successful OR file was not found (allowing DB cleanup)
                if db_manager.delete_partner_document(document_id_to_delete):
                    QMessageBox.information(self, "Success", "Document deleted successfully.")
                    self.load_partner_documents()
                else:
                    QMessageBox.critical(self, "Database Error", "Failed to delete document record from database.")
                    # Potentially re-copy file if DB delete failed? Or leave as is.


    def load_contacts(self):
        if not self.partner_id: return
        self.original_contacts = db_manager.get_contacts_for_partner(self.partner_id)
        self.contacts_table.setRowCount(0)
        for contact in self.original_contacts:
            row_position = self.contacts_table.rowCount()
            self.contacts_table.insertRow(row_position)

            name_item = QTableWidgetItem(contact.get('name'))
            email_item = QTableWidgetItem(contact.get('email'))
            phone_item = QTableWidgetItem(contact.get('phone'))
            role_item = QTableWidgetItem(contact.get('role'))

            # Store contact_id with the name item for later retrieval
            name_item.setData(Qt.UserRole, contact.get('contact_id'))

            self.contacts_table.setItem(row_position, 0, name_item)
            self.contacts_table.setItem(row_position, 1, email_item)
            self.contacts_table.setItem(row_position, 2, phone_item)
            self.contacts_table.setItem(row_position, 3, role_item)

    def load_and_set_partner_categories(self):
        self.categories_list_widget.clear()
        all_categories = db_manager.get_all_partner_categories()
        linked_category_ids = set()

        if self.partner_id:
            linked_categories = db_manager.get_categories_for_partner(self.partner_id)
            if linked_categories:
                linked_category_ids = {cat['category_id'] for cat in linked_categories}

        if all_categories:
            for category in all_categories:
                item = QListWidgetItem(category['name'])
                item.setData(Qt.UserRole, category['category_id'])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if category['category_id'] in linked_category_ids:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.categories_list_widget.addItem(item)

    def add_contact_row(self):
        row_position = self.contacts_table.rowCount()
        self.contacts_table.insertRow(row_position)
        # Cells are editable by default. Add placeholder text or leave blank.
        # No contact_id is stored for new rows initially.

    def remove_contact_row(self):
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Remove Contact", "Please select a contact to remove.")
            return

        name_item = self.contacts_table.item(current_row, 0)
        if name_item: # Check if item exists
            contact_id = name_item.data(Qt.UserRole) # Get stored contact_id
            if contact_id is not None: # If it's an existing contact (not a freshly added unsaved row)
                self.deleted_contact_ids.add(contact_id)

        self.contacts_table.removeRow(current_row)

    def accept_dialog(self):
        partner_name = self.name_input.text().strip()
        if not partner_name:
            QMessageBox.warning(self, "Validation Error", "Partner name is required.")
            return

        partner_data = {
            'name': partner_name,
            'email': self.email_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'address': self.address_input.text().strip(),
            'location': self.location_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip() # Use toPlainText for QTextEdit
        }

        success = False
        if self.partner_id:
            success = db_manager.update_partner(self.partner_id, partner_data)
        else:
            new_partner_id = db_manager.add_partner(partner_data)
            if new_partner_id:
                self.partner_id = new_partner_id
                success = True
                # Now that partner is saved, enable document controls
                self.upload_doc_button.setEnabled(True)
                # self.download_doc_button.setEnabled(False) # Will be enabled on selection
                # self.delete_doc_button.setEnabled(False)  # Will be enabled on selection
                self.documents_table.setEnabled(True)
                self.load_partner_documents() # Load any (though unlikely) documents
            else:
                QMessageBox.critical(self, "Database Error", "Failed to add new partner.")
                return

        if not success and self.partner_id:
             QMessageBox.critical(self, "Database Error", f"Failed to update partner {self.partner_id}.")
             return

        # Save Contacts
        if self.partner_id:
            current_contact_ids_in_table = set()
            for row in range(self.contacts_table.rowCount()):
                name_item = self.contacts_table.item(row, 0)
                email_item = self.contacts_table.item(row, 1)
                phone_item = self.contacts_table.item(row, 2)
                role_item = self.contacts_table.item(row, 3)

                contact_name = name_item.text().strip() if name_item else ""
                if not contact_name: # Basic validation for contact name
                    # Optionally skip or warn, for now skip if name is empty
                    continue

                contact_id = name_item.data(Qt.UserRole) if name_item else None

                contact_details = {
                    'partner_id': self.partner_id,
                    'name': contact_name,
                    'email': email_item.text().strip() if email_item else "",
                    'phone': phone_item.text().strip() if phone_item else "",
                    'role': role_item.text().strip() if role_item else ""
                }

                if contact_id is not None: # Existing contact, check for updates
                    current_contact_ids_in_table.add(contact_id)
                    original_contact = next((c for c in self.original_contacts if c['contact_id'] == contact_id), None)
                    if original_contact:
                        # Simple check: if any value changed (excluding created_at/updated_at)
                        # A more robust check would compare each field specifically.
                        is_changed = (original_contact['name'] != contact_details['name'] or
                                      original_contact.get('email','') != contact_details['email'] or
                                      original_contact.get('phone','') != contact_details['phone'] or
                                      original_contact.get('role','') != contact_details['role'])
                        if is_changed:
                            db_manager.update_partner_contact(contact_id, contact_details)
                else: # New contact
                    db_manager.add_partner_contact(contact_details)

            # Process deletions for contacts that were in original_contacts but not in current table
            # or explicitly marked for deletion via remove_contact_row
            original_contact_ids = {c['contact_id'] for c in self.original_contacts}
            ids_to_delete_from_table_absence = original_contact_ids - current_contact_ids_in_table

            all_ids_to_delete = ids_to_delete_from_table_absence.union(self.deleted_contact_ids)

            for contact_id_to_delete in all_ids_to_delete:
                db_manager.delete_partner_contact(contact_id_to_delete)

        # Save Category Links
        if self.partner_id: # Ensure partner_id is set
            partner_id_to_use = self.partner_id
            selected_category_ids = set()
            for i in range(self.categories_list_widget.count()):
                item = self.categories_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_category_ids.add(item.data(Qt.UserRole))

            current_linked_categories_list = db_manager.get_categories_for_partner(partner_id_to_use)
            current_linked_ids = {cat['category_id'] for cat in current_linked_categories_list} if current_linked_categories_list else set()

            categories_to_link = selected_category_ids - current_linked_ids
            for cat_id in categories_to_link:
                db_manager.link_partner_to_category(partner_id_to_use, cat_id)

            categories_to_unlink = current_linked_ids - selected_category_ids
            for cat_id in categories_to_unlink:
                db_manager.unlink_partner_from_category(partner_id_to_use, cat_id)

        QMessageBox.information(self, "Success", "Partner data saved successfully.")
        self.accept()

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = PartnerDialog()
    dialog.show()
    sys.exit(app.exec_())
