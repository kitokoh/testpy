# partners/partner_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
                             QMessageBox, QDialogButtonBox, QGroupBox, QTableWidget,
                             QTableWidgetItem, QHBoxLayout, QTextEdit, QListWidget, QListWidgetItem,
                             QTabWidget, QHeaderView, QAbstractItemView, QFileDialog, QInputDialog, QWidget,
                             QCheckBox, QLabel, QScrollArea, QDateEdit, QComboBox) # Added QDateEdit, QComboBox
import logging
from PyQt5.QtCore import Qt, QUrl, QDate
from PyQt5.QtGui import QDesktopServices

from db import (
    get_partner_by_id, get_documents_for_partner, add_partner_document,
    delete_partner_document, get_contacts_for_partner, get_all_partner_categories,
    get_categories_for_partner, update_partner, add_partner,
    # CRUDs for contacts will be called by EditPartnerContactDialog
    # Make sure these are the updated CRUDs from previous steps
    add_partner_contact, update_partner_contact, delete_partner_contact,
    link_partner_to_category, unlink_partner_from_category,
    # PartnerInteractions CRUD
    add_partner_interaction, get_interactions_for_partner,
    update_partner_interaction, delete_partner_interaction
)
# No direct import of central_add_contact etc. here, they are used by partners_crud
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


class EditPartnerContactDialog(QDialog):
    def __init__(self, partner_id, partner_contact_id=None, existing_contact_data=None, parent=None):
        super().__init__(parent)
        self.partner_id = partner_id
        self.partner_contact_id = partner_contact_id
        self.existing_contact_data = existing_contact_data if existing_contact_data else {}

        self.setWindowTitle(f"{'Edit' if partner_contact_id else 'Add'} Partner Contact")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # Scroll Area for many fields
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)

        # --- Form Fields ---
        # Mandatory Link Fields (always visible)
        self.is_primary_checkbox = QCheckBox()
        form_layout.addRow("Is Primary Contact:", self.is_primary_checkbox)
        self.can_receive_docs_checkbox = QCheckBox()
        form_layout.addRow("Can Receive Documents:", self.can_receive_docs_checkbox)

        # Mandatory Contact Fields (always visible)
        self.displayName_input = QLineEdit() # Name to display (mandatory)
        form_layout.addRow("Display Name*:", self.displayName_input)

        # Optional Fields Toggle
        self.show_optional_checkbox = QCheckBox("Show Optional Fields")
        self.show_optional_checkbox.setChecked(False) # Default to hidden
        self.show_optional_checkbox.stateChanged.connect(self.toggle_optional_fields)
        form_layout.addRow(self.show_optional_checkbox)

        # --- Commonly Used Fields (Always Visible) ---
        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)
        self.email_type_input = QLineEdit() # Could be QComboBox if predefined types
        form_layout.addRow("Email Type:", self.email_type_input)

        self.phone_input = QLineEdit()
        form_layout.addRow("Phone:", self.phone_input)
        self.phone_type_input = QLineEdit() # Could be QComboBox
        form_layout.addRow("Phone Type:", self.phone_type_input)

        self.position_input = QLineEdit()
        form_layout.addRow("Position/Role:", self.position_input)

        # --- Optional Fields (Toggleable) ---
        self.optional_fields_widgets = [] # Keep track of widgets to toggle

        # Given Name
        self.givenName_label = QLabel("Given Name:")
        self.givenName_input = QLineEdit()
        form_layout.addRow(self.givenName_label, self.givenName_input)
        self.optional_fields_widgets.extend([self.givenName_label, self.givenName_input])

        # Family Name
        self.familyName_label = QLabel("Family Name:")
        self.familyName_input = QLineEdit()
        form_layout.addRow(self.familyName_label, self.familyName_input)
        self.optional_fields_widgets.extend([self.familyName_label, self.familyName_input])

        # Company Name (for the contact, if different from partner)
        self.contact_company_name_label = QLabel("Contact's Company Name:")
        self.contact_company_name_input = QLineEdit()
        form_layout.addRow(self.contact_company_name_label, self.contact_company_name_input)
        self.optional_fields_widgets.extend([self.contact_company_name_label, self.contact_company_name_input])

        # Notes (for the contact)
        self.contact_notes_label = QLabel("Contact Notes:")
        self.contact_notes_input = QTextEdit()
        self.contact_notes_input.setFixedHeight(60)
        form_layout.addRow(self.contact_notes_label, self.contact_notes_input)
        self.optional_fields_widgets.extend([self.contact_notes_label, self.contact_notes_input])

        # Address Fields
        self.address_street_label = QLabel("Street Address:")
        self.address_street_input = QLineEdit()
        form_layout.addRow(self.address_street_label, self.address_street_input)
        self.optional_fields_widgets.extend([self.address_street_label, self.address_street_input])

        self.address_city_label = QLabel("City:")
        self.address_city_input = QLineEdit()
        form_layout.addRow(self.address_city_label, self.address_city_input)
        self.optional_fields_widgets.extend([self.address_city_label, self.address_city_input])

        self.address_region_label = QLabel("Region/State:")
        self.address_region_input = QLineEdit()
        form_layout.addRow(self.address_region_label, self.address_region_input)
        self.optional_fields_widgets.extend([self.address_region_label, self.address_region_input])

        self.address_postalCode_label = QLabel("Postal Code:")
        self.address_postalCode_input = QLineEdit()
        form_layout.addRow(self.address_postalCode_label, self.address_postalCode_input)
        self.optional_fields_widgets.extend([self.address_postalCode_label, self.address_postalCode_input])

        self.address_country_label = QLabel("Country:")
        self.address_country_input = QLineEdit()
        form_layout.addRow(self.address_country_label, self.address_country_input)
        self.optional_fields_widgets.extend([self.address_country_label, self.address_country_input])

        # Organization Fields
        self.org_name_label = QLabel("Organization Name:")
        self.org_name_input = QLineEdit()
        form_layout.addRow(self.org_name_label, self.org_name_input)
        self.optional_fields_widgets.extend([self.org_name_label, self.org_name_input])

        self.org_title_label = QLabel("Organization Title:")
        self.org_title_input = QLineEdit()
        form_layout.addRow(self.org_title_label, self.org_title_input)
        self.optional_fields_widgets.extend([self.org_title_label, self.org_title_input])

        # Birthday
        self.birthday_label = QLabel("Birthday (YYYY-MM-DD):")
        self.birthday_input = QLineEdit()
        form_layout.addRow(self.birthday_label, self.birthday_input)
        self.optional_fields_widgets.extend([self.birthday_label, self.birthday_input])

        scroll_widget.setLayout(form_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Dialog Buttons
        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(self.dialog_buttons)

        self.populate_form()
        self.toggle_optional_fields() # Initial toggle based on checkbox state

    def toggle_optional_fields(self):
        visible = self.show_optional_checkbox.isChecked()
        for widget in self.optional_fields_widgets:
            widget.setVisible(visible)

    def populate_form(self):
        # Link-specific fields
        self.is_primary_checkbox.setChecked(self.existing_contact_data.get('is_primary', False))
        self.can_receive_docs_checkbox.setChecked(self.existing_contact_data.get('can_receive_documents', True))

        # Central contact fields
        self.displayName_input.setText(self.existing_contact_data.get('displayName', self.existing_contact_data.get('name', '')))
        self.givenName_input.setText(self.existing_contact_data.get('givenName', ''))
        self.familyName_input.setText(self.existing_contact_data.get('familyName', ''))
        self.email_input.setText(self.existing_contact_data.get('email', ''))
        self.email_type_input.setText(self.existing_contact_data.get('email_type', ''))
        self.phone_input.setText(self.existing_contact_data.get('phone', ''))
        self.phone_type_input.setText(self.existing_contact_data.get('phone_type', ''))
        self.position_input.setText(self.existing_contact_data.get('position', self.existing_contact_data.get('role', ''))) # Cater for 'role' from old data
        self.contact_company_name_input.setText(self.existing_contact_data.get('company_name', '')) # This is contact's own company
        self.contact_notes_input.setPlainText(self.existing_contact_data.get('notes', ''))
        self.address_street_input.setText(self.existing_contact_data.get('address_streetAddress', ''))
        self.address_city_input.setText(self.existing_contact_data.get('address_city', ''))
        self.address_region_input.setText(self.existing_contact_data.get('address_region', ''))
        self.address_postalCode_input.setText(self.existing_contact_data.get('address_postalCode', ''))
        self.address_country_input.setText(self.existing_contact_data.get('address_country', ''))
        self.org_name_input.setText(self.existing_contact_data.get('organization_name', ''))
        self.org_title_input.setText(self.existing_contact_data.get('organization_title', ''))
        self.birthday_input.setText(self.existing_contact_data.get('birthday_date', ''))


    def accept(self):
        display_name = self.displayName_input.text().strip()
        if not display_name:
            QMessageBox.warning(self, "Validation Error", "Display Name is required for a contact.")
            return

        contact_data = {
            'displayName': display_name,
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
            'birthday_date': self.birthday_input.text().strip(),
            # Link-specific data
            'is_primary': self.is_primary_checkbox.isChecked(),
            'can_receive_documents': self.can_receive_docs_checkbox.isChecked()
        }
        # Filter out empty strings for optional fields to avoid overwriting with empty if not touched
        # contact_data = {k: v for k, v in contact_data.items() if v or k in ['displayName', 'is_primary', 'can_receive_documents']}


        if self.partner_contact_id: # Editing existing link and central contact
            # The update_partner_contact CRUD expects all data in one dict
            # and internally splits it for central contact and link table.
            if update_partner_contact(self.partner_contact_id, contact_data):
                QMessageBox.information(self, "Success", "Contact updated successfully.")
                super().accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update contact.")
        else: # Adding new contact and link
            new_link_id = add_partner_contact(self.partner_id, contact_data)
            if new_link_id:
                QMessageBox.information(self, "Success", "Contact added successfully.")
                super().accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to add contact.")


class PartnerDialog(QDialog):
    def __init__(self, partner_id=None, parent=None):
        super().__init__(parent)
        self.partner_id = partner_id
        self.setWindowTitle(f"{'Edit' if partner_id else 'Add'} Partner")
        self.setMinimumWidth(700) # Increased width for tabs
        self.setMinimumHeight(500)

        # self.original_contacts = [] # No longer needed as EditPartnerContactDialog handles saves
        # self.deleted_contact_ids = set() # No longer needed

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

        # New fields
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive", "Prospect", "Onboarding", "Terminated"])
        form_layout.addRow("Status:", self.status_combo)

        self.website_input = QLineEdit()
        form_layout.addRow("Website URL:", self.website_input)

        self.partner_type_combo = QComboBox()
        self.partner_type_combo.addItems(["Supplier", "Reseller", "Service Provider", "Referral", "Other"])
        form_layout.addRow("Partner Type:", self.partner_type_combo)

        self.start_date_input = QDateEdit()
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setNullable(True)
        self.start_date_input.setDate(QDate()) # Set to null
        form_layout.addRow("Collaboration Start Date:", self.start_date_input)

        self.end_date_input = QDateEdit()
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setNullable(True)
        self.end_date_input.setDate(QDate()) # Set to null
        form_layout.addRow("Collaboration End Date:", self.end_date_input)

        details_group.setLayout(form_layout)
        details_tab_layout.addWidget(details_group)

        # Contacts Management
        contacts_group = QGroupBox("Contacts")
        contacts_layout = QVBoxLayout()
        self.contacts_table = QTableWidget()
        # Adjust columns for new summary: Name (Display Name), Position, Email, Phone, Is Primary
        self.contacts_table.setColumnCount(5)
        self.contacts_table.setHorizontalHeaderLabels(["Display Name", "Position", "Email", "Phone", "Primary?"])
        self.contacts_table.horizontalHeader().setStretchLastSection(False)
        self.contacts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.contacts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.contacts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.contacts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.contacts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Content managed by dialog
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

        # --- Interactions Tab ---
        interactions_tab_widget = QWidget()
        interactions_tab_layout = QVBoxLayout(interactions_tab_widget)

        self.interactions_table = QTableWidget()
        self.interactions_table.setColumnCount(5) # ID (hidden), Date, Type, Notes Summary, Created At
        self.interactions_table.setHorizontalHeaderLabels(["ID", "Date", "Type", "Notes Summary", "Logged At"])
        self.interactions_table.setColumnHidden(0, True)
        self.interactions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Date
        self.interactions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Type
        self.interactions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Notes Summary
        self.interactions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Logged At
        self.interactions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.interactions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.interactions_table.setSelectionMode(QAbstractItemView.SingleSelection)
        interactions_tab_layout.addWidget(self.interactions_table)

        interaction_buttons_layout = QHBoxLayout()
        self.add_interaction_button = QPushButton("Add Interaction")
        self.edit_interaction_button = QPushButton("Edit Interaction")
        self.delete_interaction_button = QPushButton("Delete Interaction")
        interaction_buttons_layout.addWidget(self.add_interaction_button)
        interaction_buttons_layout.addWidget(self.edit_interaction_button)
        interaction_buttons_layout.addWidget(self.delete_interaction_button)
        interactions_tab_layout.addLayout(interaction_buttons_layout)

        interactions_tab_widget.setLayout(interactions_tab_layout)
        self.tab_widget.addTab(interactions_tab_widget, "Interactions")

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        # Connect signals
        self.button_box.accepted.connect(self.accept_dialog)
        self.button_box.rejected.connect(self.reject)
        # Details Tab Buttons
        self.add_contact_button.clicked.connect(self.handle_add_contact_button_clicked)
        self.remove_contact_button.clicked.connect(self.handle_remove_contact_button_clicked)
        self.contacts_table.doubleClicked.connect(self.handle_edit_contact_table_item_activated) # edit on double click
        # Documents Tab Buttons
        self.upload_doc_button.clicked.connect(self.handle_upload_document)
        self.download_doc_button.clicked.connect(self.handle_download_document)
        self.delete_doc_button.clicked.connect(self.handle_delete_document)
        # Interactions Tab Buttons
        self.add_interaction_button.clicked.connect(self.handle_add_interaction)
        self.edit_interaction_button.clicked.connect(self.handle_edit_interaction)
        self.delete_interaction_button.clicked.connect(self.handle_delete_interaction)
        self.interactions_table.itemSelectionChanged.connect(self.update_interaction_button_states)
        self.interactions_table.doubleClicked.connect(self.handle_edit_interaction)


        if self.partner_id:
            self.load_partner_data() # This will call load_partner_interactions
            self.load_contacts()
        else:
            # New partner, disable document, contact, and interaction buttons until partner is saved
            self.add_contact_button.setEnabled(False)
            self.remove_contact_button.setEnabled(False)
            self.contacts_table.setEnabled(False)
            self.upload_doc_button.setEnabled(False)
            self.download_doc_button.setEnabled(False)
            self.delete_doc_button.setEnabled(False)
            self.documents_table.setEnabled(False)
            # Interactions Tab
            self.interactions_table.setEnabled(False)
            self.add_interaction_button.setEnabled(False)
            self.edit_interaction_button.setEnabled(False)
            self.delete_interaction_button.setEnabled(False)

        self.load_and_set_partner_categories()
        # Initial state for interaction buttons if partner_id exists but no selection yet
        if self.partner_id:
            self.update_interaction_button_states()


    def load_partner_data(self):
        if not self.partner_id:
            # Disable document, contact, and interaction features if it's a new partner
            self.upload_doc_button.setEnabled(False)
            self.download_doc_button.setEnabled(False)
            self.delete_doc_button.setEnabled(False)
            self.documents_table.setEnabled(False)
            self.add_contact_button.setEnabled(False)
            self.remove_contact_button.setEnabled(False)
            self.contacts_table.setEnabled(False)
            self.interactions_table.setEnabled(False)
            self.add_interaction_button.setEnabled(False)
            self.edit_interaction_button.setEnabled(False)
            self.delete_interaction_button.setEnabled(False)
            return

        partner = get_partner_by_id(self.partner_id)
        if partner:
            self.name_input.setText(partner.get('partner_name', partner.get('name', ''))) # Prefer partner_name if available from full partner object
            self.email_input.setText(partner.get('email', '')) # This is partner's main email
            self.phone_input.setText(partner.get('phone', '')) # Partner's main phone
            self.address_input.setText(partner.get('address', '')) # Partner's main address
            # self.location_input.setText(partner.get('location', '')) # No 'location' field in schema, use address
            self.notes_input.setPlainText(partner.get('notes', '')) # Partner's notes

            # Populate new fields
            status = partner.get('status', 'Active') # Default to 'Active' if not in DB
            status_index = self.status_combo.findText(status, Qt.MatchFixedString)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            else:
                self.status_combo.setCurrentIndex(self.status_combo.findText("Active")) # Default if not found
                logging.warning(f"Partner status '{status}' not in combo box. Defaulted to Active.")

            self.website_input.setText(partner.get('website_url', ''))

            partner_type = partner.get('partner_type', '')
            partner_type_index = self.partner_type_combo.findText(partner_type, Qt.MatchFixedString)
            if partner_type_index >= 0:
                self.partner_type_combo.setCurrentIndex(partner_type_index)
            elif partner_type: # If there was a value but not found, log warning
                logging.warning(f"Partner type '{partner_type}' not in combo box. Left as is or default.")
                # Optionally add it or select a default: self.partner_type_combo.setCurrentIndex(self.partner_type_combo.findText("Other"))


            start_date_str = partner.get('collaboration_start_date')
            if start_date_str:
                try:
                    q_start_date = QDate.fromString(start_date_str, "yyyy-MM-dd")
                    if q_start_date.isValid():
                        self.start_date_input.setDate(q_start_date)
                    else:
                        self.start_date_input.setDate(QDate()) # Set to null if parsing failed
                        logging.warning(f"Invalid start_date format: {start_date_str}")
                except ValueError as e:
                    self.start_date_input.setDate(QDate()) # Set to null on error
                    logging.error(f"Error parsing start_date '{start_date_str}': {e}")
            else:
                self.start_date_input.setDate(QDate()) # Set to null if no date string

            end_date_str = partner.get('collaboration_end_date')
            if end_date_str:
                try:
                    q_end_date = QDate.fromString(end_date_str, "yyyy-MM-dd")
                    if q_end_date.isValid():
                        self.end_date_input.setDate(q_end_date)
                    else:
                        self.end_date_input.setDate(QDate()) # Set to null
                        logging.warning(f"Invalid end_date format: {end_date_str}")
                except ValueError as e:
                    self.end_date_input.setDate(QDate()) # Set to null
                    logging.error(f"Error parsing end_date '{end_date_str}': {e}")
            else:
                self.end_date_input.setDate(QDate()) # Set to null

            # Enable document and contact buttons as partner exists
            self.upload_doc_button.setEnabled(True)
            self.download_doc_button.setEnabled(True)
            self.delete_doc_button.setEnabled(True)
            self.documents_table.setEnabled(True)
            self.load_partner_documents()

            self.add_contact_button.setEnabled(True)
            self.remove_contact_button.setEnabled(True)
            self.contacts_table.setEnabled(True)
            # Enable interactions tab elements
            self.interactions_table.setEnabled(True)
            self.add_interaction_button.setEnabled(True)
            self.load_partner_interactions() # Load interactions
            self.update_interaction_button_states() # Set initial button states for interactions

    def load_partner_interactions(self):
        if not self.partner_id:
            self.interactions_table.setRowCount(0)
            # self.update_interaction_button_states() # Call to ensure buttons are in correct state
            return

        self.interactions_table.setRowCount(0) # Clear existing rows
        try:
            interactions = get_interactions_for_partner(self.partner_id)
            if interactions:
                self.interactions_table.setSortingEnabled(False) # Disable sorting during population
                for interaction in interactions:
                    row_position = self.interactions_table.rowCount()
                    self.interactions_table.insertRow(row_position)

                    interaction_id_item = QTableWidgetItem(interaction.get('interaction_id'))
                    # Store the full interaction data in UserRole for easy access on edit/delete
                    interaction_id_item.setData(Qt.UserRole, interaction)
                    self.interactions_table.setItem(row_position, 0, interaction_id_item) # Hidden ID

                    date_str = interaction.get('interaction_date', '')
                    # Optional: Format date string if needed, though YYYY-MM-DD is usually fine
                    self.interactions_table.setItem(row_position, 1, QTableWidgetItem(date_str))

                    self.interactions_table.setItem(row_position, 2, QTableWidgetItem(interaction.get('interaction_type', '')))

                    notes = interaction.get('notes', '')
                    notes_summary = (notes[:75] + '...') if len(notes) > 75 else notes # Summary
                    notes_item = QTableWidgetItem(notes_summary)
                    self.interactions_table.setItem(row_position, 3, notes_item)

                    created_at_str = interaction.get('created_at', '')
                    # Optional: Format datetime string nicely
                    try:
                        dt_obj = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        created_at_display = dt_obj.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, TypeError):
                        created_at_display = created_at_str # Fallback to raw string
                    self.interactions_table.setItem(row_position, 4, QTableWidgetItem(created_at_display))
                self.interactions_table.setSortingEnabled(True) # Re-enable sorting

        except Exception as e:
            logging.error(f"Error loading partner interactions: {e}")
            QMessageBox.critical(self, "Load Error", f"Could not load partner interactions: {e}")
        finally:
            self.update_interaction_button_states() # Ensure buttons reflect table state

    def update_interaction_button_states(self):
        has_selection = bool(self.interactions_table.selectedItems())
        # Add button is enabled if partner_id exists (handled in load_partner_data and __init__)
        # self.add_interaction_button.setEnabled(bool(self.partner_id))
        self.edit_interaction_button.setEnabled(has_selection and bool(self.partner_id))
        self.delete_interaction_button.setEnabled(has_selection and bool(self.partner_id))

    def handle_add_interaction(self):
        if not self.partner_id:
            QMessageBox.warning(self, "Partner Not Available", "Please save the partner before adding interactions.")
            return

        dialog = InteractionEditDialog(partner_id=self.partner_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_partner_interactions()

    def handle_edit_interaction(self):
        if not self.partner_id: return # Should not happen if button is enabled

        selected_rows = self.interactions_table.selectionModel().selectedRows()
        if not selected_rows:
            # This can happen if double-click is on empty area or selection is cleared
            # Or if called directly without a selection
            # QMessageBox.warning(self, "Edit Interaction", "Please select an interaction to edit.")
            return

        selected_row_index = selected_rows[0] # QModelIndex
        id_item = self.interactions_table.item(selected_row_index.row(), 0) # Hidden ID item

        if not id_item:
            logging.error("Could not retrieve ID item from selected interaction row.")
            QMessageBox.critical(self, "Error", "Could not retrieve interaction data.")
            return

        interaction_data = id_item.data(Qt.UserRole) # Full interaction data
        if not interaction_data or 'interaction_id' not in interaction_data:
            logging.error(f"No interaction_id or full data found in UserRole for row {selected_row_index.row()}. Cannot edit.")
            QMessageBox.critical(self, "Error", "Interaction data is missing or corrupt.")
            return

        interaction_id = interaction_data['interaction_id']

        dialog = InteractionEditDialog(partner_id=self.partner_id,
                                       interaction_id=interaction_id,
                                       interaction_data=interaction_data,
                                       parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_partner_interactions()

    def handle_delete_interaction(self):
        if not self.partner_id: return

        selected_rows = self.interactions_table.selectionModel().selectedRows()
        if not selected_rows:
            # QMessageBox.warning(self, "Delete Interaction", "Please select an interaction to delete.")
            return

        id_item = self.interactions_table.item(selected_rows[0].row(), 0)
        if not id_item:
             QMessageBox.critical(self, "Error", "Cannot retrieve interaction ID.")
             return

        interaction_id = id_item.text() # Get interaction_id from the hidden cell's text
        interaction_data = id_item.data(Qt.UserRole)
        date_for_confirm = interaction_data.get('interaction_date', 'this interaction')
        type_for_confirm = interaction_data.get('interaction_type', '')


        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the interaction on {date_for_confirm} ({type_for_confirm})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if delete_partner_interaction(interaction_id):
                QMessageBox.information(self, "Success", "Interaction deleted successfully.")
                self.load_partner_interactions()
            else:
                QMessageBox.critical(self, "Database Error", "Failed to delete interaction from database.")


    def load_partner_documents(self):
        if not self.partner_id: # Should be redundant due to checks in load_partner_data
            self.documents_table.setRowCount(0)
            return

        self.documents_table.setRowCount(0) # Clear existing rows
        documents = get_documents_for_partner(self.partner_id)
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

        new_doc_id = add_partner_document(doc_data)
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
                if delete_partner_document(document_id_to_delete):
                    QMessageBox.information(self, "Success", "Document deleted successfully.")
                    self.load_partner_documents()
                else:
                    QMessageBox.critical(self, "Database Error", "Failed to delete document record from database.")
                    # Potentially re-copy file if DB delete failed? Or leave as is.


    def load_contacts(self):
        if not self.partner_id:
            self.contacts_table.setRowCount(0)
            return

        contacts_data = get_contacts_for_partner(self.partner_id)
        self.contacts_table.setRowCount(0) # Clear existing rows
        if contacts_data:
            for contact_item_data in contacts_data: # contact_item_data is a dict from the CRUD
                row_position = self.contacts_table.rowCount()
                self.contacts_table.insertRow(row_position)

                display_name = contact_item_data.get('displayName', contact_item_data.get('name', 'N/A'))
                name_cell_item = QTableWidgetItem(display_name)
                # Store all data needed for editing in UserRole of the first cell item
                name_cell_item.setData(Qt.UserRole, contact_item_data) # Store the whole dict

                position = contact_item_data.get('position', '')
                email = contact_item_data.get('email', '')
                phone = contact_item_data.get('phone', '')
                is_primary_text = "Yes" if contact_item_data.get('is_primary') else "No"

                self.contacts_table.setItem(row_position, 0, name_cell_item)
                self.contacts_table.setItem(row_position, 1, QTableWidgetItem(position))
                self.contacts_table.setItem(row_position, 2, QTableWidgetItem(email))
                self.contacts_table.setItem(row_position, 3, QTableWidgetItem(phone))
                self.contacts_table.setItem(row_position, 4, QTableWidgetItem(is_primary_text))
        self.contacts_table.resizeColumnsToContents()

    def load_and_set_partner_categories(self):
        self.categories_list_widget.clear()
        all_categories = get_all_partner_categories() # Ensure this returns list of dicts
        linked_category_ids = set()

        if self.partner_id:
            linked_categories = get_categories_for_partner(self.partner_id)
            if linked_categories:
                linked_category_ids = {cat['partner_category_id'] for cat in linked_categories}

        if all_categories:
            for category in all_categories:
                if 'category_id' not in category or category['category_id'] is None:
                    logging.warning(f"PartnerDialog: Category dictionary missing 'category_id' or it's None. Category data: {category}. Skipping this category.")
                    continue # Skip this category

                item = QListWidgetItem(category['category_name'])
                item.setData(Qt.UserRole, category['partner_category_id'])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if category['partner_category_id'] in linked_category_ids:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.categories_list_widget.addItem(item)

    def handle_add_contact_button_clicked(self):
        if not self.partner_id:
            QMessageBox.warning(self, "Partner Not Saved", "Please save the partner before adding contacts.")
            return

        dialog = EditPartnerContactDialog(partner_id=self.partner_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contacts() # Refresh the contacts list

    def handle_edit_contact_table_item_activated(self, item): # QModelIndex item
        # This is connected to doubleClicked, item is QModelIndex
        # Get the data from the first column's item for the clicked row
        name_cell_item = self.contacts_table.item(item.row(), 0) # item is QTableWidgetItem from doubleClicked signal

        if not name_cell_item:
            logging.warning("No data item found in the clicked row for editing contact.")
            return

        contact_full_data = name_cell_item.data(Qt.UserRole)
        if contact_full_data and 'partner_contact_id' in contact_full_data:
            partner_contact_id = contact_full_data['partner_contact_id']
            # No need to separately pass contact_id, it's in contact_full_data

            dialog = EditPartnerContactDialog(partner_id=self.partner_id,
                                              partner_contact_id=partner_contact_id,
                                              existing_contact_data=contact_full_data,
                                              parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_contacts() # Refresh table
        else:
            logging.warning(f"No partner_contact_id or full_data found in UserRole for row {item.row()}. Cannot edit.")


    def handle_remove_contact_button_clicked(self):
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Remove Contact", "Please select a contact to remove.")
            return

        name_cell_item = self.contacts_table.item(current_row, 0)
        if not name_cell_item:
            QMessageBox.warning(self, "Error", "Cannot retrieve contact data from selected row.")
            return

        contact_full_data = name_cell_item.data(Qt.UserRole)
        if contact_full_data and 'partner_contact_id' in contact_full_data:
            partner_contact_id_to_delete = contact_full_data['partner_contact_id']
            contact_display_name = contact_full_data.get('displayName', contact_full_data.get('name', 'this contact'))

            reply = QMessageBox.question(self, "Confirm Deletion",
                                         f"Are you sure you want to remove the contact link for '{contact_display_name}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if delete_partner_contact(partner_contact_id_to_delete):
                    QMessageBox.information(self, "Success", "Contact link removed successfully.")
                    self.load_contacts() # Refresh table
                else:
                    QMessageBox.critical(self, "Error", "Failed to remove contact link from database.")
        else:
            QMessageBox.warning(self, "Error", "Could not find contact link ID for the selected contact.")


    def accept_dialog(self):
        # Partner's main name is 'partner_name' in DB, but input is self.name_input
        partner_name_val = self.name_input.text().strip()
        if not partner_name_val:
            QMessageBox.warning(self, "Validation Error", "Partner name (Partner Details tab) is required.")
            return

        # partner_data = {
        #     return

        partner_data_for_db = {
            'partner_name': partner_name_val, # Schema uses partner_name
            'email': self.email_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'address': self.address_input.text().strip(),
            # 'location': self.location_input.text().strip(), # Not in schema, combined into address or notes
            'notes': self.notes_input.toPlainText().strip(),

            # New fields for DB
            'status': self.status_combo.currentText(),
            'website_url': self.website_input.text().strip(),
            'partner_type': self.partner_type_combo.currentText(),
            'collaboration_start_date': self.start_date_input.date().toString("yyyy-MM-dd") if not self.start_date_input.date().isNull() else None,
            'collaboration_end_date': self.end_date_input.date().toString("yyyy-MM-dd") if not self.end_date_input.date().isNull() else None,
        }

        # For now, this dialog only handles a subset of Partner fields.
        # The full partner object might have more fields like 'partner_category_id', 'status', etc.
        # If these are managed elsewhere or need to be preserved, fetch existing partner data first.

        db_op_success = False
        if self.partner_id:
            # If updating, we might want to preserve other fields not directly editable here.
            # For now, just update what's in the form.
            db_op_success = update_partner(self.partner_id, partner_data_for_db)
            if not db_op_success:
                QMessageBox.critical(self, "Database Error", f"Failed to update partner {self.partner_id}.")
                return # Stop if partner update fails
        else: # Adding new partner
            new_partner_id_from_db = add_partner(partner_data_for_db)
            if new_partner_id_from_db:
                self.partner_id = new_partner_id_from_db # Critical: update dialog's partner_id
                db_op_success = True
                # Enable controls that depend on partner_id
                self.upload_doc_button.setEnabled(True)
                self.documents_table.setEnabled(True)
                self.add_contact_button.setEnabled(True)
                self.remove_contact_button.setEnabled(True)
                self.contacts_table.setEnabled(True)
                # Enable interactions tab as well
                self.interactions_table.setEnabled(True)
                self.add_interaction_button.setEnabled(True)
                self.update_interaction_button_states() # Refresh states
                self.setWindowTitle(f"Edit Partner - {partner_name_val}") # Update window title
            else:
                QMessageBox.critical(self, "Database Error", "Failed to add new partner.")
                return # Stop if partner add fails

        if not db_op_success: # Should have been caught by specific messages above, but as a safeguard
            return

        # Contact saving is now handled by EditPartnerContactDialog.
        # PartnerDialog no longer directly iterates table rows to save contacts.
        # self.original_contacts and self.deleted_contact_ids are no longer used here.

        # Save Category Links (this part can remain similar)
        if self.partner_id:
            partner_id_to_use = self.partner_id # Use the now confirmed partner_id
            selected_category_ids = set()
            for i in range(self.categories_list_widget.count()):
                item = self.categories_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_category_ids.add(item.data(Qt.UserRole))

            current_linked_categories_list = get_categories_for_partner(partner_id_to_use)
            current_linked_ids = {cat['partner_category_id'] for cat in current_linked_categories_list} if current_linked_categories_list else set()

            categories_to_link = selected_category_ids - current_linked_ids
            for cat_id in categories_to_link:
                link_partner_to_category(partner_id_to_use, cat_id)

            categories_to_unlink = current_linked_ids - selected_category_ids
            for cat_id in categories_to_unlink:
                unlink_partner_from_category(partner_id_to_use, cat_id)

        QMessageBox.information(self, "Success", "Partner data saved successfully.")
        self.accept()

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = PartnerDialog()
    dialog.show()
    sys.exit(app.exec_())

class InteractionEditDialog(QDialog):
    def __init__(self, partner_id, interaction_id=None, interaction_data=None, parent=None):
        super().__init__(parent)
        self.partner_id = partner_id
        self.interaction_id = interaction_id
        self.interaction_data = interaction_data if interaction_data else {} # Full dict from UserRole

        self.setWindowTitle(f"{'Edit' if self.interaction_id else 'Add'} Partner Interaction")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.interaction_date_edit = QDateEdit(self)
        self.interaction_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.interaction_date_edit.setCalendarPopup(True)
        self.interaction_date_edit.setDate(QDate.currentDate()) # Default to today
        form_layout.addRow("Date*:", self.interaction_date_edit)

        self.interaction_type_combo = QComboBox(self)
        self.interaction_type_combo.addItems(["Call", "Meeting", "Email", "Note", "Other"])
        form_layout.addRow("Type*:", self.interaction_type_combo)

        self.notes_edit = QTextEdit(self)
        self.notes_edit.setPlaceholderText("Enter details about the interaction...")
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept_interaction_dialog)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if self.interaction_id and self.interaction_data:
            self.populate_form()

        logging.info(f"InteractionEditDialog initialized for partner {self.partner_id}, interaction ID: {self.interaction_id}")

    def populate_form(self):
        date_str = self.interaction_data.get('interaction_date')
        if date_str:
            q_date = QDate.fromString(date_str, "yyyy-MM-dd")
            if q_date.isValid():
                self.interaction_date_edit.setDate(q_date)
            else:
                logging.warning(f"Invalid date string '{date_str}' received for interaction {self.interaction_id}")

        type_str = self.interaction_data.get('interaction_type')
        if type_str:
            index = self.interaction_type_combo.findText(type_str, Qt.MatchFixedString)
            if index >= 0:
                self.interaction_type_combo.setCurrentIndex(index)
            else:
                # If type from DB is not in standard list, add it or select 'Other'
                # For simplicity, we'll select 'Other' or leave as is if not found
                logging.warning(f"Interaction type '{type_str}' not in default list for interaction {self.interaction_id}.")
                other_index = self.interaction_type_combo.findText("Other")
                if other_index >=0 : self.interaction_type_combo.setCurrentIndex(other_index)


        self.notes_edit.setPlainText(self.interaction_data.get('notes', ''))
        logging.info(f"Form populated for interaction ID: {self.interaction_id}")

    def accept_interaction_dialog(self):
        interaction_date_str = self.interaction_date_edit.date().toString("yyyy-MM-dd")
        interaction_type_str = self.interaction_type_combo.currentText()
        notes_str = self.notes_edit.toPlainText().strip()

        if not interaction_date_str: # Should always have a value from QDateEdit
            QMessageBox.warning(self, "Validation Error", "Interaction date cannot be empty.")
            return
        if not interaction_type_str: # Should always have a value from QComboBox
            QMessageBox.warning(self, "Validation Error", "Interaction type cannot be empty.")
            return

        data_to_save = {
            'partner_id': self.partner_id,
            'interaction_date': interaction_date_str,
            'interaction_type': interaction_type_str,
            'notes': notes_str
        }

        success = False
        action = "add"
        if self.interaction_id: # Edit mode
            action = "update"
            success = update_partner_interaction(self.interaction_id, data_to_save)
        else: # Add mode
            new_id = add_partner_interaction(data_to_save)
            if new_id:
                self.interaction_id = new_id # Store new ID in case needed (though dialog closes)
                success = True

        if success:
            QMessageBox.information(self, "Success", f"Partner interaction {action}ed successfully.")
            super().accept() # Close dialog
        else:
            QMessageBox.critical(self, "Database Error", f"Failed to {action} partner interaction.")
