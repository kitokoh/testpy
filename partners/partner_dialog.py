# partners/partner_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
                             QMessageBox, QDialogButtonBox, QGroupBox, QTableWidget,
                             QTableWidgetItem, QHBoxLayout, QTextEdit, QListWidget, QListWidgetItem) # Added QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt
import db.crud as db_manager

class PartnerDialog(QDialog):
    def __init__(self, partner_id=None, parent=None):
        super().__init__(parent)
        self.partner_id = partner_id
        self.setWindowTitle(f"{'Edit' if partner_id else 'Add'} Partner")
        self.setMinimumWidth(600) # Set a minimum width for the dialog

        self.original_contacts = [] # Store original contacts for diffing
        self.deleted_contact_ids = set() # Store IDs of contacts marked for deletion

        layout = QVBoxLayout(self)

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
        self.notes_input = QTextEdit() # Changed to QTextEdit
        self.notes_input.setFixedHeight(80) # Set a reasonable height
        form_layout.addRow("Notes:", self.notes_input)
        details_group.setLayout(form_layout)
        layout.addWidget(details_group)

        # Contacts Management
        contacts_group = QGroupBox("Contacts")
        contacts_layout = QVBoxLayout()
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(4) # Name, Email, Phone, Role
        self.contacts_table.setHorizontalHeaderLabels(["Name*", "Email", "Phone", "Role"])
        # Make table headers resize correctly
        self.contacts_table.horizontalHeader().setStretchLastSection(True)
        contacts_layout.addWidget(self.contacts_table)

        contacts_buttons_layout = QHBoxLayout()
        self.add_contact_button = QPushButton("Add Contact")
        self.remove_contact_button = QPushButton("Remove Selected Contact")
        contacts_buttons_layout.addWidget(self.add_contact_button)
        contacts_buttons_layout.addWidget(self.remove_contact_button)
        contacts_layout.addLayout(contacts_buttons_layout)

        contacts_group.setLayout(contacts_layout)
        layout.addWidget(contacts_group)

        # Categories Management
        categories_group = QGroupBox("Assign Categories")
        categories_layout = QVBoxLayout()
        self.categories_list_widget = QListWidget()
        # self.categories_list_widget.setSelectionMode(QAbstractItemView.MultiSelection) # Not needed for checkable
        categories_layout.addWidget(self.categories_list_widget)
        categories_group.setLayout(categories_layout)
        layout.addWidget(categories_group)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)

        # Connect signals
        self.button_box.accepted.connect(self.accept_dialog)
        self.button_box.rejected.connect(self.reject)
        self.add_contact_button.clicked.connect(self.add_contact_row)
        self.remove_contact_button.clicked.connect(self.remove_contact_row)

        if self.partner_id:
            self.load_partner_data()
            self.load_contacts()
        self.load_and_set_partner_categories() # Load for both add and edit mode

    def load_partner_data(self):
        if not self.partner_id: return
        partner = db_manager.get_partner_by_id(self.partner_id)
        if partner:
            self.name_input.setText(partner.get('name', ''))
            self.email_input.setText(partner.get('email', ''))
            self.phone_input.setText(partner.get('phone', ''))
            self.address_input.setText(partner.get('address', ''))
            self.location_input.setText(partner.get('location', ''))
            self.notes_input.setPlainText(partner.get('notes', '')) # Use setPlainText for QTextEdit

    def load_contacts(self):
        if not self.partner_id: return # Only load if editing existing partner with contacts
        self.original_contacts = db_manager.get_contacts_for_partner(self.partner_id)
        self.contacts_table.setRowCount(0) # Clear existing rows
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
                self.partner_id = new_partner_id # Important for saving new contacts
                success = True
            else:
                QMessageBox.critical(self, "Database Error", "Failed to add new partner.")
                return # Do not proceed to contacts if partner saving failed

        if not success and self.partner_id: # update failed
             QMessageBox.critical(self, "Database Error", f"Failed to update partner {self.partner_id}.")
             return


        # Save Contacts
        if self.partner_id: # Ensure partner_id is set (either existing or newly created)
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
