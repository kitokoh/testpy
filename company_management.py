import sys
import os
import shutil # For file operations
import uuid # For unique filenames
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox, QComboBox, QFileDialog, QStackedWidget,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QTabWidget,
    QCheckBox, QLabel, QScrollArea # Added for EditPersonnelContactDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QGridLayout
from contact_manager.sync_service import handle_contact_change_from_platform # For Google Sync
import logging # Added for logging

# Adjust path to import db_manager from the parent directory / current dir
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path: # for running directly if db.py is alongside
    sys.path.insert(0, current_dir)

from db.cruds.companies_crud import add_company, get_all_companies, update_company, delete_company, set_default_company, get_company_by_id
from db.cruds.company_personnel_crud import get_contacts_for_personnel, add_personnel_contact, update_personnel_contact_link, unlink_contact_from_personnel
# Keep other db imports for now, will be refactored incrementally
try:
    from db import (
        # Company functions handled by companies_crud_instance:
        # add_company, get_company_by_id, get_all_companies,
        # update_company, delete_company, set_default_company, get_default_company
        add_company_personnel,
        get_personnel_for_company,
        update_company_personnel,
        delete_company_personnel,
        initialize_database
    )
    db_available = True # This flag might become less relevant with direct instance usage
    print("Specific db functions (excluding company) imported successfully.")
except ImportError as e:
    print(f"Error importing specific db functions: {e}")
    db_available = False
    # Fallbacks for functions not yet moved to CRUD instances if any.
    # companies_crud_instance itself would be unavailable if its import failed,
    # leading to a NameError, which is an acceptable failure mode.
    # So, no need for MockCompaniesCRUD here anymore.

    # Fallbacks for other functions if their direct imports fail
    def add_company_personnel(*args, **kwargs): print("DB function add_company_personnel unavailable"); return None
    def get_personnel_for_company(*args, **kwargs): print("DB function get_personnel_for_company unavailable"); return []
    def update_company_personnel(*args, **kwargs): print("DB function update_company_personnel unavailable"); return False
    def delete_company_personnel(*args, **kwargs): print("DB function delete_company_personnel unavailable"); return False
    def initialize_database(*args, **kwargs): print("DB function initialize_database unavailable"); pass

    print("Failed to import some db functions. Some features may not work.")

# Define APP_ROOT_DIR
APP_ROOT_DIR = parent_dir
logger = logging.getLogger(__name__) # Setup logger for this module


class EditPersonnelContactDialog(QDialog):
    def __init__(self, personnel_id, company_personnel_contact_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.personnel_id = personnel_id
        self.company_personnel_contact_id = company_personnel_contact_id
        self.existing_contact_data = contact_data if contact_data else {}

        self.setWindowTitle(self.tr("Edit Contact") if company_personnel_contact_id else self.tr("Add Contact"))
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)

        # --- Form Fields ---
        # Link Specific
        self.is_primary_checkbox = QCheckBox(self.tr("Is Primary Contact"))
        form_layout.addRow(self.is_primary_checkbox)
        self.can_receive_docs_checkbox = QCheckBox(self.tr("Can Receive Documents"))
        form_layout.addRow(self.can_receive_docs_checkbox)

        # Mandatory Contact
        self.displayName_input = QLineEdit()
        form_layout.addRow(self.tr("Display Name*:"), self.displayName_input)

        self.show_optional_checkbox = QCheckBox(self.tr("Show Optional Fields"))
        self.show_optional_checkbox.setChecked(False)
        self.show_optional_checkbox.stateChanged.connect(self.toggle_optional_fields_visibility)
        form_layout.addRow(self.show_optional_checkbox)

        self.optional_fields_widgets = []

        def add_optional_field(label_text, widget):
            label = QLabel(label_text)
            form_layout.addRow(label, widget)
            self.optional_fields_widgets.extend([label, widget])

        self.givenName_input = QLineEdit()
        add_optional_field(self.tr("Given Name:"), self.givenName_input)
        self.familyName_input = QLineEdit()
        add_optional_field(self.tr("Family Name:"), self.familyName_input)
        self.email_input = QLineEdit()
        add_optional_field(self.tr("Email:"), self.email_input)
        self.email_type_input = QLineEdit()
        add_optional_field(self.tr("Email Type:"), self.email_type_input)
        self.phone_input = QLineEdit()
        add_optional_field(self.tr("Phone:"), self.phone_input)
        self.phone_type_input = QLineEdit()
        add_optional_field(self.tr("Phone Type:"), self.phone_type_input)
        self.position_input = QLineEdit() # Formerly role for personnel contact
        add_optional_field(self.tr("Position:"), self.position_input)
        self.contact_company_name_input = QLineEdit()
        add_optional_field(self.tr("Contact's Company:"), self.contact_company_name_input)
        self.contact_notes_input = QTextEdit()
        self.contact_notes_input.setFixedHeight(60)
        add_optional_field(self.tr("Notes:"), self.contact_notes_input)
        self.address_street_input = QLineEdit()
        add_optional_field(self.tr("Street:"), self.address_street_input)
        self.address_city_input = QLineEdit()
        add_optional_field(self.tr("City:"), self.address_city_input)
        self.address_region_input = QLineEdit()
        add_optional_field(self.tr("Region/State:"), self.address_region_input)
        self.address_postalCode_input = QLineEdit()
        add_optional_field(self.tr("Postal Code:"), self.address_postalCode_input)
        self.address_country_input = QLineEdit()
        add_optional_field(self.tr("Country:"), self.address_country_input)
        self.org_name_input = QLineEdit()
        add_optional_field(self.tr("Organization Name:"), self.org_name_input)
        self.org_title_input = QLineEdit()
        add_optional_field(self.tr("Organization Title:"), self.org_title_input)
        self.birthday_input = QLineEdit() # Consider QDateEdit
        add_optional_field(self.tr("Birthday (YYYY-MM-DD):"), self.birthday_input)

        scroll_widget.setLayout(form_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.dialog_buttons.accepted.connect(self.accept_contact_dialog) # Renamed to avoid clash
        self.dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(self.dialog_buttons)

        self.populate_contact_form()
        self.toggle_optional_fields_visibility()


    def toggle_optional_fields_visibility(self):
        visible = self.show_optional_checkbox.isChecked()
        for widget in self.optional_fields_widgets:
            widget.setVisible(visible)

    def populate_contact_form(self):
        self.is_primary_checkbox.setChecked(self.existing_contact_data.get('is_primary', False))
        self.can_receive_docs_checkbox.setChecked(self.existing_contact_data.get('can_receive_documents', True))
        self.displayName_input.setText(self.existing_contact_data.get('displayName', self.existing_contact_data.get('name', '')))
        # Populate optional fields
        self.givenName_input.setText(self.existing_contact_data.get('givenName', ''))
        self.familyName_input.setText(self.existing_contact_data.get('familyName', ''))
        self.email_input.setText(self.existing_contact_data.get('email', ''))
        self.email_type_input.setText(self.existing_contact_data.get('email_type', ''))
        self.phone_input.setText(self.existing_contact_data.get('phone', ''))
        self.phone_type_input.setText(self.existing_contact_data.get('phone_type', ''))
        self.position_input.setText(self.existing_contact_data.get('position', ''))
        self.contact_company_name_input.setText(self.existing_contact_data.get('company_name', ''))
        self.contact_notes_input.setPlainText(self.existing_contact_data.get('notes', ''))
        self.address_street_input.setText(self.existing_contact_data.get('address_streetAddress', ''))
        self.address_city_input.setText(self.existing_contact_data.get('address_city', ''))
        self.address_region_input.setText(self.existing_contact_data.get('address_region', ''))
        self.address_postalCode_input.setText(self.existing_contact_data.get('address_postalCode', ''))
        self.address_country_input.setText(self.existing_contact_data.get('address_country', ''))
        self.org_name_input.setText(self.existing_contact_data.get('organization_name', ''))
        self.org_title_input.setText(self.existing_contact_data.get('organization_title', ''))
        self.birthday_input.setText(self.existing_contact_data.get('birthday_date', ''))

    def accept_contact_dialog(self): # Renamed from accept
        display_name = self.displayName_input.text().strip()
        if not display_name:
            QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Display Name is required."))
            return

        contact_payload = {
            'displayName': display_name,
            'is_primary': self.is_primary_checkbox.isChecked(),
            'can_receive_documents': self.can_receive_docs_checkbox.isChecked(),
            'givenName': self.givenName_input.text().strip(),
            'familyName': self.familyName_input.text().strip(),
            'email': self.email_input.text().strip(),
            'email_type': self.email_type_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'phone_type': self.phone_type_input.text().strip(),
            'position': self.position_input.text().strip(),
            'company_name': self.contact_company_name_input.text().strip(),
            'notes': self.contact_notes_input.toPlainText().strip(),
            'address_streetAddress': self.address_street_input.text().strip(),
            'address_city': self.address_city_input.text().strip(),
            'address_region': self.address_region_input.text().strip(),
            'address_postalCode': self.address_postalCode_input.text().strip(),
            'address_country': self.address_country_input.text().strip(),
            'organization_name': self.org_name_input.text().strip(),
            'organization_title': self.org_title_input.text().strip(),
            'birthday_date': self.birthday_input.text().strip()
        }

        # For updates, separate link_data and contact_details_data
        link_data_for_update = {
            'is_primary': contact_payload['is_primary'],
            'can_receive_documents': contact_payload['can_receive_documents']
        }
        # contact_details_for_update will be everything else from contact_payload
        contact_details_for_update = {k: v for k, v in contact_payload.items() if k not in ['is_primary', 'can_receive_documents']}


        if self.company_personnel_contact_id: # Editing
            if update_personnel_contact_link(self.company_personnel_contact_id, link_data=link_data_for_update, contact_details_data=contact_details_for_update):
                QMessageBox.information(self, self.tr("Success"), self.tr("Contact updated successfully."))
                super().accept() # Use super().accept() to close dialog
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update contact."))
        else: # Adding
            new_link_id = add_personnel_contact(self.personnel_id, contact_payload) # add_personnel_contact takes the full payload
            if new_link_id:
                QMessageBox.information(self, self.tr("Success"), self.tr("Contact added successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add contact."))


LOGO_SUBDIR = "company_logos"
DEFAULT_LOGO_SIZE = 128

ICON_PATH = os.path.join(APP_ROOT_DIR, "icons")
APP_STYLESHEET_PATH = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss")


class CompanyDialog(QDialog):
    def __init__(self, company_data=None, parent=None, app_root_dir=None):
        super().__init__(parent)
        self.company_data = company_data
        self.company_id = None
        self.logo_path_selected_for_upload = None
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR

        self.setWindowTitle(self.tr("Edit Company") if company_data else self.tr("Add Company"))
        self.setMinimumWidth(450)
        # ... (rest of CompanyDialog UI setup as before) ...
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.company_name_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setFixedHeight(60)
        self.payment_info_edit = QTextEdit()
        self.payment_info_edit.setFixedHeight(60)
        self.other_info_edit = QTextEdit()
        self.other_info_edit.setFixedHeight(60)

        self.logo_preview_label = QLabel(self.tr("No logo selected."))
        self.logo_preview_label.setFixedSize(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE)
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setObjectName("logoPreviewLabel")
        self.upload_logo_button = QPushButton(self.tr("Upload Logo"))
        self.upload_logo_button.setIcon(QIcon.fromTheme("document-open", QIcon(os.path.join(ICON_PATH, "eye.svg"))))
        self.upload_logo_button.clicked.connect(self.handle_upload_logo)

        layout.addRow(self.tr("Company Name:"), self.company_name_edit)
        layout.addRow(self.tr("Address:"), self.address_edit)
        layout.addRow(self.tr("Payment Info:"), self.payment_info_edit)
        layout.addRow(self.tr("Other Info:"), self.other_info_edit)

        logo_layout = QVBoxLayout()
        logo_layout.addWidget(self.logo_preview_label)
        logo_layout.addWidget(self.upload_logo_button)
        layout.addRow(self.tr("Logo:"), logo_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        if self.company_data:
            self.company_id = self.company_data.get('company_id')
            self.load_company_data()

    def load_company_data(self):
        # ... (load_company_data implementation as before) ...
        self.company_name_edit.setText(self.company_data.get('company_name', ''))
        self.address_edit.setPlainText(self.company_data.get('address', ''))
        self.payment_info_edit.setPlainText(self.company_data.get('payment_info', ''))
        self.other_info_edit.setPlainText(self.company_data.get('other_info', ''))
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path):
                pixmap = QPixmap(full_logo_path)
                self.logo_preview_label.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.logo_preview_label.setText(self.tr("Logo not found"))
        else:
            self.logo_preview_label.setText(self.tr("No logo"))


    def handle_upload_logo(self):
        # ... (handle_upload_logo implementation as before) ...
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Logo"), "", self.tr("Images (*.png *.jpg *.jpeg *.bmp)"))
        if file_path:
            self.logo_path_selected_for_upload = file_path
            pixmap = QPixmap(file_path)
            self.logo_preview_label.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self):
        # ... (accept implementation for CompanyDialog as before) ...
        # if not db_available: # Assuming instances are available if imports succeed
        #     QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))
        #     return
        company_name = self.company_name_edit.text().strip()
        if not company_name:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Company name cannot be empty."))
            return
        data = {
            "company_name": company_name,
            "address": self.address_edit.toPlainText().strip(),
            "payment_info": self.payment_info_edit.toPlainText().strip(),
            "other_info": self.other_info_edit.toPlainText().strip(),
        }
        final_logo_rel_path = self.company_data.get('logo_path') if self.company_data else None
        if self.logo_path_selected_for_upload:
            logo_dir_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR)
            os.makedirs(logo_dir_full_path, exist_ok=True)
            _, ext = os.path.splitext(self.logo_path_selected_for_upload)
            identifier_for_filename = self.company_id if self.company_id else str(uuid.uuid4())
            unique_logo_filename = f"{identifier_for_filename}{ext}"
            target_logo_full_path = os.path.join(logo_dir_full_path, unique_logo_filename)
            try:
                shutil.copy(self.logo_path_selected_for_upload, target_logo_full_path)
                final_logo_rel_path = unique_logo_filename
            except Exception as e:
                QMessageBox.critical(self, self.tr("Logo Error"), self.tr("Could not save logo: {0}").format(str(e)))
                return
        data['logo_path'] = final_logo_rel_path
        if self.company_id:
            success_update = update_company(self.company_id, data)
            if success_update: # update_company returns bool
                QMessageBox.information(self, self.tr("Success"), self.tr("Company updated successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update company."))
        else:
            # add_company returns new_company_id (str) or None
            new_company_id_result = add_company(data)
            if new_company_id_result:
                self.company_id = new_company_id_result # Set company_id for the dialog instance
                if self.logo_path_selected_for_upload: # Logo was uploaded for a new company
                    temp_logo_filename = data.get('logo_path') # This is the UUID-based name
                    if temp_logo_filename:
                        try:
                            is_uuid_filename = str(uuid.UUID(os.path.splitext(temp_logo_filename)[0])) == os.path.splitext(temp_logo_filename)[0]
                        except ValueError:
                            is_uuid_filename = False

                        if is_uuid_filename:
                            new_proper_filename = f"{self.company_id}{os.path.splitext(temp_logo_filename)[1]}"
                            old_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, temp_logo_filename)
                            new_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, new_proper_filename)
                            if os.path.exists(old_full_path):
                                try:
                                    os.rename(old_full_path, new_full_path)
                                    update_company(self.company_id, {'logo_path': new_proper_filename})
                                    print(f"Renamed logo from {temp_logo_filename} to {new_proper_filename}")
                                except Exception as e_rename:
                                    print(f"Error renaming logo after company creation: {e_rename}")
                QMessageBox.information(self, self.tr("Success"), self.tr("Company added successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add company."))


class PersonnelDialog(QDialog):
    def __init__(self, company_id, personnel_data=None, role_default="seller", parent=None, current_user_id=None): # Added current_user_id
        super().__init__(parent)
        self.company_id = company_id
        self.personnel_data = personnel_data
        self.personnel_id = None
        self.current_user_id = current_user_id

        self.setWindowTitle(self.tr("Edit Personnel") if personnel_data else self.tr("Add Personnel"))
        self.setMinimumWidth(450) # Increased width for contacts table

        main_layout = QVBoxLayout(self) # Main layout for the dialog

        # Personnel Details Form
        details_group = QGroupBox(self.tr("Personnel Details"))
        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        form_layout.addRow(self.tr("Name*:"), self.name_edit)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["seller", "technical_manager", "other"])
        self.role_combo.setEditable(True)
        self.role_combo.setCurrentText(role_default)
        form_layout.addRow(self.tr("Role*:"), self.role_combo)
        details_group.setLayout(form_layout)
        main_layout.addWidget(details_group)

        # Contacts Management
        contacts_group = QGroupBox(self.tr("Associated Contacts"))
        contacts_layout_v = QVBoxLayout()
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(5) # Display Name, Position, Email, Phone, Primary?
        self.contacts_table.setHorizontalHeaderLabels([self.tr("Display Name"), self.tr("Position"), self.tr("Email"), self.tr("Phone"), self.tr("Primary?")])
        self.contacts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.contacts_table.doubleClicked.connect(self.handle_edit_personnel_contact) # Edit on double click
        contacts_layout_v.addWidget(self.contacts_table)

        contact_buttons_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("Add Contact"))
        self.edit_contact_btn = QPushButton(self.tr("Edit Selected Contact"))
        self.remove_contact_btn = QPushButton(self.tr("Remove Selected Contact Link"))
        contact_buttons_layout.addWidget(self.add_contact_btn)
        contact_buttons_layout.addWidget(self.edit_contact_btn)
        contact_buttons_layout.addWidget(self.remove_contact_btn)
        contacts_layout_v.addLayout(contact_buttons_layout)
        contacts_group.setLayout(contacts_layout_v)
        main_layout.addWidget(contacts_group)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        # Connect signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.add_contact_btn.clicked.connect(self.handle_add_personnel_contact)
        self.edit_contact_btn.clicked.connect(self.handle_edit_personnel_contact) # Explicit edit button
        self.remove_contact_btn.clicked.connect(self.handle_remove_personnel_contact_link)


        if self.personnel_data:
            self.personnel_id = self.personnel_data.get('personnel_id')
            self.load_personnel_data() # This will also load contacts
        else: # New personnel, disable contact buttons until personnel is saved (or enable if we allow adding contacts before first save)
            self.add_contact_btn.setEnabled(False)
            self.edit_contact_btn.setEnabled(False)
            self.remove_contact_btn.setEnabled(False)
            self.contacts_table.setEnabled(False)


    def load_personnel_data(self):
        self.name_edit.setText(self.personnel_data.get('name', ''))
        role = self.personnel_data.get('role', '')
        if role in ["seller", "technical_manager", "other"]:
            self.role_combo.setCurrentText(role)
        else:
            self.role_combo.setCurrentText("other")
            self.role_combo.lineEdit().setText(role)

        if self.personnel_id: # Existing personnel, load their contacts
            self.load_associated_contacts()
            self.add_contact_btn.setEnabled(True)
            self.edit_contact_btn.setEnabled(True)
            self.remove_contact_btn.setEnabled(True)
            self.contacts_table.setEnabled(True)

    def load_associated_contacts(self):
        if not self.personnel_id:
            self.contacts_table.setRowCount(0)
            return

        contacts = get_contacts_for_personnel(self.personnel_id)
        self.contacts_table.setRowCount(0)
        for contact_data in contacts:
            row_pos = self.contacts_table.rowCount()
            self.contacts_table.insertRow(row_pos)

            name_item = QTableWidgetItem(contact_data.get('displayName', contact_data.get('name', 'N/A')))
            name_item.setData(Qt.UserRole, contact_data) # Store full contact data for editing

            self.contacts_table.setItem(row_pos, 0, name_item)
            self.contacts_table.setItem(row_pos, 1, QTableWidgetItem(contact_data.get('position', '')))
            self.contacts_table.setItem(row_pos, 2, QTableWidgetItem(contact_data.get('email', '')))
            self.contacts_table.setItem(row_pos, 3, QTableWidgetItem(contact_data.get('phone', '')))
            self.contacts_table.setItem(row_pos, 4, QTableWidgetItem("Yes" if contact_data.get('is_primary') else "No"))
        self.contacts_table.resizeColumnsToContents()


    def handle_add_personnel_contact(self):
        if not self.personnel_id:
            QMessageBox.warning(self, self.tr("Save Personnel First"), self.tr("Please save the personnel before adding contacts."))
            return
        dialog = EditPersonnelContactDialog(personnel_id=self.personnel_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_associated_contacts()

    def handle_edit_personnel_contact(self):
        selected_row = self.contacts_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, self.tr("Edit Contact"), self.tr("Please select a contact to edit."))
            return

        item_data = self.contacts_table.item(selected_row, 0).data(Qt.UserRole)
        if not item_data or 'company_personnel_contact_id' not in item_data:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not retrieve contact link details."))
            return

        dialog = EditPersonnelContactDialog(
            personnel_id=self.personnel_id,
            company_personnel_contact_id=item_data['company_personnel_contact_id'],
            contact_data=item_data, # Pass the full dict
            parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_associated_contacts()

    def handle_remove_personnel_contact_link(self):
        selected_row = self.contacts_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, self.tr("Remove Contact Link"), self.tr("Please select a contact link to remove."))
            return

        item_data = self.contacts_table.item(selected_row, 0).data(Qt.UserRole)
        if not item_data or 'company_personnel_contact_id' not in item_data:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not retrieve contact link ID."))
            return

        company_personnel_contact_id = item_data['company_personnel_contact_id']
        contact_name = item_data.get('displayName', item_data.get('name', 'this contact'))

        reply = QMessageBox.question(self, self.tr("Confirm Removal"),
                                     self.tr(f"Are you sure you want to remove the link to contact '{contact_name}'? This will not delete the central contact record."),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if unlink_contact_from_personnel(company_personnel_contact_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Contact link removed successfully."))
                self.load_associated_contacts()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to remove contact link."))


    def accept(self):
        if not db_available:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))
            return

        name = self.name_edit.text().strip()
        role = self.role_combo.currentText().strip()
        # Email and phone are no longer part of CompanyPersonnel direct fields
        # email = self.email_edit.text().strip()
        # phone = self.phone_edit.text().strip()

        if not name or not role:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Name and role cannot be empty."))
            return

        # Data for CompanyPersonnel table (excluding direct email/phone)
        data = {"company_id": self.company_id, "name": name, "role": role}

        if self.personnel_id: # Editing existing personnel
            success = update_company_personnel(self.personnel_id, data) # This CRUD should only update CompanyPersonnel fields
            if success:
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel updated successfully."))
                # Sync hooks for personnel's own record (name, role) change can remain if needed,
                # but not for email/phone as they are removed.
                # The prompt mentioned adjusting/removing sync hooks for direct email/phone fields.
                # If other CompanyPersonnel fields (name, role) are synced, that logic would be here.
                # For now, assume sync is primarily for contact details which are handled separately.
                # Example of removed sync hook:
                # if hasattr(self, 'current_user_id') and self.current_user_id:
                #     handle_contact_change_from_platform(...) for personnel's direct fields
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update personnel."))
        else: # Adding new personnel
            new_personnel_id = add_company_personnel(data) # This CRUD adds to CompanyPersonnel table
            if new_personnel_id:
                self.personnel_id = new_personnel_id # Important to set this for the dialog instance
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel added successfully. You can now add contacts to this person."))
                # Enable contact management now that personnel is saved
                self.add_contact_btn.setEnabled(True)
                self.edit_contact_btn.setEnabled(True)
                self.remove_contact_btn.setEnabled(True)
                self.contacts_table.setEnabled(True)
                # Sync for the creation of the personnel record itself (not its contacts yet)
                # if hasattr(self, 'current_user_id') and self.current_user_id:
                #    handle_contact_change_from_platform(...) for new personnel record
                super().accept() # Close dialog after successful add
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add personnel."))
        # Contact saving is now handled by EditPersonnelContactDialog


class CompanyDetailsViewWidget(QWidget):
    # ... (CompanyDetailsViewWidget implementation as before, no changes needed for this subtask) ...
    def __init__(self, company_data, app_root_dir, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.app_root_dir = app_root_dir
        self.init_ui()
    def init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10,10,10,10); layout.setSpacing(8)
        self.name_label = QLabel(self.company_data.get('company_name', self.tr('N/A')))
        self.address_label = QLabel(self.company_data.get('address', self.tr('N/A')))
        self.payment_info_label = QLabel(self.company_data.get('payment_info', self.tr('N/A')))
        self.other_info_label = QLabel(self.company_data.get('other_info', self.tr('N/A')))
        self.logo_display = QLabel(); self.logo_display.setFixedSize(DEFAULT_LOGO_SIZE + 20, DEFAULT_LOGO_SIZE + 20)
        self.logo_display.setAlignment(Qt.AlignCenter); self.logo_display.setObjectName("logoDisplayLabel")
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path): self.logo_display.setPixmap(QPixmap(full_logo_path).scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else: self.logo_display.setText(self.tr("Logo not found"))
        else: self.logo_display.setText(self.tr("No Logo"))
        layout.addRow(self.tr("Name:"), self.name_label); layout.addRow(self.tr("Address:"), self.address_label)
        layout.addRow(self.tr("Payment Info:"), self.payment_info_label); layout.addRow(self.tr("Other Info:"), self.other_info_label)
        layout.addRow(self.tr("Logo:"), self.logo_display)
    def update_details(self, new_company_data):
        self.company_data = new_company_data
        self.name_label.setText(self.company_data.get('company_name', self.tr('N/A')))
        self.address_label.setText(self.company_data.get('address', self.tr('N/A')))
        self.payment_info_label.setText(self.company_data.get('payment_info', self.tr('N/A')))
        self.other_info_label.setText(self.company_data.get('other_info', self.tr('N/A')))
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path): self.logo_display.setPixmap(QPixmap(full_logo_path).scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else: self.logo_display.setText(self.tr("Logo not found"))
        else: self.logo_display.setText(self.tr("No Logo"))


class CompanyTabWidget(QWidget):
    def __init__(self, parent=None, app_root_dir=None, current_user_id=None): # Added current_user_id
        super().__init__(parent)
        self.current_selected_company_id = None
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR
        self.current_user_id = current_user_id # Store user_id for sync hooks

        main_layout = QHBoxLayout(self)
        # ... (rest of CompanyTabWidget UI setup as before) ...
        left_panel_layout = QVBoxLayout()
        self.company_list_widget = QListWidget(); self.company_list_widget.itemClicked.connect(self.on_company_selected)
        self.add_company_button = QPushButton(self.tr("Add Company")); self.add_company_button.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_company_button.clicked.connect(self.handle_add_company)
        self.edit_company_button = QPushButton(self.tr("Edit Company")); self.edit_company_button.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_company_button.clicked.connect(self.handle_edit_company); self.edit_company_button.setEnabled(False)
        self.delete_company_button = QPushButton(self.tr("Delete Company")); self.delete_company_button.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_company_button.setObjectName("dangerButton"); self.delete_company_button.clicked.connect(self.handle_delete_company); self.delete_company_button.setEnabled(False)
        self.set_default_button = QPushButton(self.tr("Set as Default")); self.set_default_button.setIcon(QIcon.fromTheme("object-select", QIcon(os.path.join(ICON_PATH,"check.svg")))); self.set_default_button.clicked.connect(self.handle_set_default); self.set_default_button.setEnabled(False)
        left_panel_layout.addWidget(QLabel(self.tr("Companies:"))); left_panel_layout.addWidget(self.company_list_widget)
        company_button_grid = QGridLayout(); company_button_grid.addWidget(self.add_company_button, 0, 0); company_button_grid.addWidget(self.edit_company_button, 0, 1); company_button_grid.addWidget(self.delete_company_button, 1, 0); company_button_grid.addWidget(self.set_default_button, 1, 1)
        left_panel_layout.addLayout(company_button_grid)
        self.details_tabs = QTabWidget(); self.company_info_tab = QWidget(); self.company_info_layout = QVBoxLayout(self.company_info_tab); self.company_details_view = None; self.details_tabs.addTab(self.company_info_tab, self.tr("Company Info"))

        # Sellers Tab
        sellers_tab = QWidget(); sellers_layout = QVBoxLayout(sellers_tab)
        self.sellers_table = QTableWidget()
        self.sellers_table.setColumnCount(4) # Name, Role, Primary Email, Primary Phone
        self.sellers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Role"), self.tr("Primary Email"), self.tr("Primary Phone")])
        self.sellers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sellers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.sellers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.sellers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.sellers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sellers_table.setSelectionBehavior(QAbstractItemView.SelectRows) # Select whole rows
        sellers_layout.addWidget(self.sellers_table)
        seller_btn_layout = QHBoxLayout(); self.add_seller_btn = QPushButton(self.tr("Add Seller")); self.add_seller_btn.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_seller_btn.clicked.connect(lambda: self.handle_add_personnel('seller')); self.edit_seller_btn = QPushButton(self.tr("Edit Seller")); self.edit_seller_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_seller_btn.clicked.connect(lambda: self.handle_edit_personnel('seller')); self.delete_seller_btn = QPushButton(self.tr("Delete Seller")); self.delete_seller_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_seller_btn.setObjectName("dangerButton"); self.delete_seller_btn.clicked.connect(lambda: self.handle_delete_personnel('seller'))
        seller_btn_layout.addWidget(self.add_seller_btn); seller_btn_layout.addWidget(self.edit_seller_btn); seller_btn_layout.addWidget(self.delete_seller_btn); sellers_layout.addLayout(seller_btn_layout); self.details_tabs.addTab(sellers_tab, self.tr("Sellers"))

        # Technical Managers Tab
        tech_managers_tab = QWidget(); tech_managers_layout = QVBoxLayout(tech_managers_tab)
        self.tech_managers_table = QTableWidget()
        self.tech_managers_table.setColumnCount(4) # Name, Role, Primary Email, Primary Phone
        self.tech_managers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Role"), self.tr("Primary Email"), self.tr("Primary Phone")])
        self.tech_managers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tech_managers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tech_managers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tech_managers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tech_managers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tech_managers_table.setSelectionBehavior(QAbstractItemView.SelectRows) # Select whole rows
        tech_managers_layout.addWidget(self.tech_managers_table)
        tech_btn_layout = QHBoxLayout(); self.add_tech_btn = QPushButton(self.tr("Add Manager")); self.add_tech_btn.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_tech_btn.clicked.connect(lambda: self.handle_add_personnel('technical_manager')); self.edit_tech_btn = QPushButton(self.tr("Edit Manager")); self.edit_tech_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_tech_btn.clicked.connect(lambda: self.handle_edit_personnel('technical_manager')); self.delete_tech_btn = QPushButton(self.tr("Delete Manager")); self.delete_tech_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_tech_btn.setObjectName("dangerButton"); self.delete_tech_btn.clicked.connect(lambda: self.handle_delete_personnel('technical_manager'))
        tech_btn_layout.addWidget(self.add_tech_btn); tech_btn_layout.addWidget(self.edit_tech_btn); tech_btn_layout.addWidget(self.delete_tech_btn); tech_managers_layout.addLayout(tech_btn_layout); self.details_tabs.addTab(tech_managers_tab, self.tr("Technical Managers"))

        main_layout.addLayout(left_panel_layout, 1); main_layout.addWidget(self.details_tabs, 2)
        self.load_companies(); self.update_personnel_button_states(False)

    def load_companies(self):
        # ... (load_companies implementation as before) ...
        self.company_list_widget.clear()
        if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater(); self.company_details_view = None
        self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0); self.current_selected_company_id = None
        # if not db_available: self.company_list_widget.addItem(QListWidgetItem(self.tr("Error: DB functions not available."))); return
        try:
            companies = get_all_companies() # Changed to use instance
            if not companies: self.company_list_widget.addItem(QListWidgetItem(self.tr("No companies found.")))
            for company in companies:
                item_text = company['company_name']
                if company.get('is_default'): item_text += self.tr(" (Default)")
                list_item = QListWidgetItem(item_text); list_item.setData(Qt.UserRole, company); self.company_list_widget.addItem(list_item)
        except Exception as e: self.company_list_widget.addItem(QListWidgetItem(self.tr("Error loading companies: {0}").format(str(e)))); print(f"Error in load_companies: {e}")
        self.update_company_button_states(); self.update_personnel_button_states(False)


    def on_company_selected(self, item):
        # ... (on_company_selected implementation as before) ...
        company_data = item.data(Qt.UserRole)
        if company_data:
            self.current_selected_company_id = company_data.get('company_id')
            if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater()
            self.company_details_view = CompanyDetailsViewWidget(company_data, self.app_root_dir); self.company_info_layout.addWidget(self.company_details_view)
            self.load_personnel(self.current_selected_company_id)
        else:
            self.current_selected_company_id = None
            if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater(); self.company_details_view = None
            self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0)
        self.update_company_button_states(); self.update_personnel_button_states(self.current_selected_company_id is not None)


    def handle_add_company(self):
        # ... (handle_add_company implementation as before) ...
        # if not db_available: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available.")); return # Assuming instance available
        dialog = CompanyDialog(parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted: self.load_companies()

    def handle_edit_company(self):
        # ... (handle_edit_company implementation as before) ...
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Edit Company"), self.tr("Please select a company to edit.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole);
        if not company_data: return
        dialog = CompanyDialog(company_data=company_data, parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted:
            self.load_companies()
            for i in range(self.company_list_widget.count()): # Reselect
                list_item = self.company_list_widget.item(i); item_data = list_item.data(Qt.UserRole)
                if item_data and item_data.get('company_id') == self.current_selected_company_id:
                    self.company_list_widget.setCurrentItem(list_item); self.on_company_selected(list_item); break

    def handle_delete_company(self):
        # ... (handle_delete_company implementation as before) ...
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Delete Company"), self.tr("Please select a company to delete.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole)
        confirm = QMessageBox.warning(self, self.tr("Confirm Delete"), self.tr("Are you sure you want to delete {0}? This will also delete all associated personnel.").format(company_data.get('company_name')), QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if db_available:
                logo_rel_path = company_data.get('logo_path')
                if logo_rel_path:
                    full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
                    if os.path.exists(full_logo_path):
                        try: os.remove(full_logo_path); print(f"Deleted logo: {full_logo_path}")
                        except Exception as e_logo_del: QMessageBox.warning(self, self.tr("Logo Deletion Error"), self.tr("Could not delete logo file: {0}.\nPlease remove it manually.").format(str(e_logo_del)))
                # delete_company returns bool
                if delete_company(self.current_selected_company_id):
                    QMessageBox.information(self, self.tr("Success"), self.tr("Company deleted successfully."))
                    self.load_companies()
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete company from database."))
            # else: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available.")) # Assuming instance available

    def handle_set_default(self):
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Set Default"), self.tr("Please select a company to set as default.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole)
        # if db_available: # Assuming instance available
        # set_default_company returns bool
        if set_default_company(self.current_selected_company_id):
            QMessageBox.information(self, self.tr("Success"), self.tr("'{0}' is now the default company.").format(company_data.get('company_name')))
            current_selection_row = self.company_list_widget.currentRow(); self.load_companies()
            if current_selection_row >=0 and current_selection_row < self.company_list_widget.count(): self.company_list_widget.setCurrentRow(current_selection_row); self.on_company_selected(self.company_list_widget.currentItem())
        else: QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to set default company."))
        # else: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))

    def update_company_button_states(self):
        # ... (update_company_button_states implementation as before) ...
        has_selection = self.current_selected_company_id is not None
        self.edit_company_button.setEnabled(has_selection); self.delete_company_button.setEnabled(has_selection); self.set_default_button.setEnabled(has_selection)
        if has_selection:
            item = self.company_list_widget.currentItem()
            if item: company_data = item.data(Qt.UserRole)
            if company_data and company_data.get('is_default'): self.set_default_button.setEnabled(False)

    def update_personnel_button_states(self, company_selected: bool):
        # ... (update_personnel_button_states implementation as before) ...
        self.add_seller_btn.setEnabled(company_selected); self.add_tech_btn.setEnabled(company_selected)
        if not company_selected: self.edit_seller_btn.setEnabled(False); self.delete_seller_btn.setEnabled(False); self.edit_tech_btn.setEnabled(False); self.delete_tech_btn.setEnabled(False)

    def load_personnel(self, company_id):
        # ... (load_personnel implementation as before) ...
        self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0)
        if not db_available or not company_id: return
        try:
            sellers = get_personnel_for_company(company_id, role='seller'); self._populate_personnel_table(self.sellers_table, sellers)
            tech_managers = get_personnel_for_company(company_id, role='technical_manager'); self._populate_personnel_table(self.tech_managers_table, tech_managers)
            others_sellers = get_personnel_for_company(company_id, role='other_seller'); self._populate_personnel_table(self.sellers_table, others_sellers, append=True) # Example custom roles
            others_tech = get_personnel_for_company(company_id, role='other_technical_manager'); self._populate_personnel_table(self.tech_managers_table, others_tech, append=True)
        except Exception as e: QMessageBox.warning(self, self.tr("Personnel Error"), self.tr("Error loading personnel: {0}").format(str(e)))


    def _populate_personnel_table(self, table: QTableWidget, personnel_list: list, append=False):
        if not append:
            table.setRowCount(0)

        for personnel_record in personnel_list: # personnel_record is from CompanyPersonnel table
            current_row = table.rowCount()
            table.insertRow(current_row)

            personnel_id = personnel_record.get('personnel_id')
            name_item = QTableWidgetItem(personnel_record.get('name'))
            name_item.setData(Qt.UserRole, personnel_record) # Store full personnel record for edit/delete
            table.setItem(current_row, 0, name_item)
            table.setItem(current_row, 1, QTableWidgetItem(personnel_record.get('role', 'N/A')))

            primary_email = self.tr("N/A")
            primary_phone = self.tr("N/A")

            if personnel_id:
                # Fetch associated contacts for this personnel
                contacts = get_contacts_for_personnel(personnel_id)
                if contacts:
                    primary_contact = next((c for c in contacts if c.get('is_primary')), None)
                    if primary_contact:
                        primary_email = primary_contact.get('email', self.tr("N/A"))
                        primary_phone = primary_contact.get('phone', self.tr("N/A"))
                    elif contacts: # No primary, take first contact's details if available
                        first_contact = contacts[0]
                        primary_email = first_contact.get('email', self.tr("N/A"))
                        primary_phone = first_contact.get('phone', self.tr("N/A"))

            table.setItem(current_row, 2, QTableWidgetItem(primary_email))
            table.setItem(current_row, 3, QTableWidgetItem(primary_phone))

            # Actions column (Edit/Delete for the personnel record itself) is removed from table display
            # Actions are now handled by buttons below the table (edit_seller_btn, delete_seller_btn etc.)
            # If row-specific actions were needed, they would be added here.

        table.resizeColumnsToContents()


    def handle_add_personnel(self, role_type: str):
        if not self.current_selected_company_id:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a company first."))
            return
        default_role = "seller" if role_type == 'seller' else "technical_manager"
        dialog = PersonnelDialog(
            company_id=self.current_selected_company_id,
            role_default=default_role,
            parent=self,
            current_user_id=getattr(self, 'current_user_id', None) # Pass current_user_id
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_personnel(self.current_selected_company_id)

    def handle_edit_personnel(self, role_type: str):
        table = self.sellers_table if role_type == 'seller' else self.tech_managers_table
        selected_row = table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a person to edit."))
            return
        item = table.item(selected_row, 0)
        if not item: return
        personnel_data = item.data(Qt.UserRole)
        dialog = PersonnelDialog(
            company_id=self.current_selected_company_id,
            personnel_data=personnel_data,
            parent=self,
            current_user_id=getattr(self, 'current_user_id', None) # Pass current_user_id
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_personnel(self.current_selected_company_id)

    def handle_delete_personnel(self, role_type: str):
        table = self.sellers_table if role_type == 'seller' else self.tech_managers_table
        selected_row = table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a person to delete."))
            return
        item = table.item(selected_row, 0)
        if not item: return
        personnel_data = item.data(Qt.UserRole)
        personnel_id = personnel_data.get('personnel_id')

        confirm = QMessageBox.warning(self, self.tr("Confirm Delete"),
                                      self.tr("Are you sure you want to delete {0}?").format(personnel_data.get('name')),
                                      QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            current_user_id_val = getattr(self, 'current_user_id', None)
            if current_user_id_val and personnel_id:
                try:
                    handle_contact_change_from_platform(
                        user_id=str(current_user_id_val),
                        local_contact_id=str(personnel_id),
                        local_contact_type='company_personnel',
                        change_type='delete'
                    )
                    print(f"Sync triggered for deleting personnel: {personnel_id}")
                except Exception as e:
                    print(f"Error triggering sync for deleting personnel: {e}")
            else:
                print("Warning: current_user_id or personnel_id not available in CompanyTabWidget for delete sync trigger.")

            if db_available and delete_company_personnel(personnel_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel deleted successfully."))
                self.load_personnel(self.current_selected_company_id)
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete personnel from database."))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # ... (stylesheet and db init as before) ...
    stylesheet_path_to_try = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss")
    try:
        if os.path.exists(stylesheet_path_to_try):
            with open(stylesheet_path_to_try, "r") as f: app.setStyleSheet(f.read())
        else: print(f"Stylesheet not found at {stylesheet_path_to_try}. Using default style.")
    except Exception as e: print(f"Error loading stylesheet: {e}")

    # if db_available: # Assuming initialize_database is correctly imported and db_available might be true
    try: initialize_database(); print("Database initialized by company_management.py (for testing if run directly).")
    except Exception as e: print(f"Error initializing database from company_management.py: {e}")
    # else: print("db functions not available, skipping database initialization in company_management.py.") # This else might not be reachable if db_available is always True

    os.makedirs(os.path.join(APP_ROOT_DIR, LOGO_SUBDIR), exist_ok=True)

    # Example: Pass a mock current_user_id for testing CompanyTabWidget
    # main_window = CompanyTabWidget(app_root_dir=APP_ROOT_DIR, current_user_id="test_user_company_widget")
    main_window = CompanyTabWidget(app_root_dir=APP_ROOT_DIR) # Or without for basic UI
    main_window.setWindowTitle("Company Management")
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()
    sys.exit(app.exec_())
