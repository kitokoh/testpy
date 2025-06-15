# PyQt5 widget for displaying and managing a unified list of contacts.
# This includes contacts from the platform (clients, partners, etc.) and Google Contacts.

import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QLineEdit, QPushButton, QComboBox, QLabel, QHeaderView, QAbstractItemView,
                             QApplication, QMessageBox) # Added QMessageBox and QApplication
from PyQt5.QtCore import Qt, pyqtSignal

# --- Database and Service Imports ---
try:
    from ..db import crud as db_manager
    # from . import sync_service # For manual sync actions
except (ImportError, ValueError) as e:
    # Fallback for running script standalone or if path issues occur
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root_dir = os.path.dirname(current_dir) # Moves up to /app
    if app_root_dir not in sys.path:
        sys.path.append(app_root_dir)
    try:
        from db import crud as db_manager
        # import sync_service # from contact_manager.sync_service
    except ImportError as final_e:
        db_manager = None
        # sync_service = None
        print(f"Warning: Could not import db_manager or sync_service for ContactListWidget: {final_e}. Some features may be disabled.")

class ContactListWidget(QWidget):
    # Signals can be added here if needed, e.g., to notify other parts of the UI about actions.
    # contact_selected_signal = pyqtSignal(dict) # Example: emits contact details

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unified Contact List")
        self.current_selected_contact_info = None # To store details of the selected row

        # --- Main Layout ---
        self.main_layout = QVBoxLayout(self)

        # --- Filter Controls ---
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search contacts (Name, Email, Company)...")
        self.search_input.textChanged.connect(self.filter_contacts)
        filter_layout.addWidget(self.search_input)

        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["All", "Client Contacts", "Partner Contacts", "Company Personnel", "Google Synced Only"])
        self.type_filter_combo.currentIndexChanged.connect(self.filter_contacts)
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.type_filter_combo)

        # TODO: Add more filters like "Sync Status" if applicable

        self.main_layout.addLayout(filter_layout)

        # --- Action Buttons ---
        actions_layout = QHBoxLayout()
        self.view_details_button = QPushButton("View/Edit Details")
        self.view_details_button.setEnabled(False)
        self.view_details_button.clicked.connect(self.handle_view_details)
        actions_layout.addWidget(self.view_details_button)

        self.assign_role_button = QPushButton("Link to Platform Role")
        self.assign_role_button.setToolTip("For Google-originated contacts, link them as a new Client, Partner, etc.")
        self.assign_role_button.setEnabled(False)
        self.assign_role_button.clicked.connect(self.handle_assign_role)
        actions_layout.addWidget(self.assign_role_button)

        self.manual_sync_button = QPushButton("Manual Sync")
        self.manual_sync_button.setToolTip("Manually synchronize this contact with Google.")
        self.manual_sync_button.setEnabled(False) # Enable based on selection and sync status
        self.manual_sync_button.clicked.connect(self.handle_manual_sync)
        actions_layout.addWidget(self.manual_sync_button)

        actions_layout.addStretch() # Push buttons to the left

        self.main_layout.addLayout(actions_layout)

        # --- Contacts Table ---
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(7) # Adjust as needed
        self.contacts_table.setHorizontalHeaderLabels([
            "Name", "Email", "Phone", "Source", "Company", "Role/Title", "Sync Status"
        ])
        self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Read-only table
        self.contacts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Stretch columns
        self.contacts_table.verticalHeader().setVisible(False) # Hide vertical row numbers
        self.contacts_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        # self.contacts_table.doubleClicked.connect(self.handle_view_details) # Optional double-click to view

        self.main_layout.addWidget(self.contacts_table)

        # --- Initial Load ---
        self.load_contacts()

    def load_contacts(self):
        """
        Loads contacts from various sources (platform DB, Google sync logs)
        and populates the table.
        """
        print("Placeholder: Loading contacts...")
        if not db_manager:
            self.contacts_table.setRowCount(1)
            self.contacts_table.setItem(0, 0, QTableWidgetItem("Error: DB Manager not available."))
            return

        self.contacts_table.setRowCount(0) # Clear existing rows

        # --- Placeholder Data ---
        # --- Actual Data Fetching ---

        # 1. Fetch Client Contacts
        try:
            clients = db_manager.clients_crud.get_all_clients()
            if clients:
                for client in clients:
                    client_id = client.get('client_id')
                    client_company_name = client.get('company_name', client.get('client_name', 'N/A'))
                    # get_contacts_for_client is expected to return full contact details from Contacts table
                    client_contacts = db_manager.contacts_crud.get_contacts_for_client(client_id)
                    for contact in client_contacts:
                        row_position = self.contacts_table.rowCount()
                        self.contacts_table.insertRow(row_position)
                        name_item = QTableWidgetItem(contact.get('displayName', contact.get('name', 'N/A')))
                        item_data = {
                            'id': contact.get('contact_id'),
                            'type': 'client_contact',
                            'source': 'platform',
                            'client_id': client_id,
                            'link_id': contact.get('client_contact_id'), # ID from ClientContacts table
                            'full_data': contact # Store the whole dict for details view
                        }
                        name_item.setData(Qt.UserRole, item_data)
                        self.contacts_table.setItem(row_position, 0, name_item)
                        self.contacts_table.setItem(row_position, 1, QTableWidgetItem(contact.get('email', '')))
                        self.contacts_table.setItem(row_position, 2, QTableWidgetItem(contact.get('phone', '')))
                        self.contacts_table.setItem(row_position, 3, QTableWidgetItem("Platform (Client)"))
                        self.contacts_table.setItem(row_position, 4, QTableWidgetItem(client_company_name))
                        self.contacts_table.setItem(row_position, 5, QTableWidgetItem(contact.get('position', '')))
                        self.contacts_table.setItem(row_position, 6, QTableWidgetItem(contact.get('sync_status', 'N/A'))) # Placeholder
        except Exception as e:
            print(f"Error loading client contacts: {e}")
            # Optionally add an error row to the table or show a message

        # 2. Fetch Partner Contacts
        try:
            partners = db_manager.partners_crud.get_all_partners()
            if partners:
                for partner in partners:
                    partner_id = partner.get('partner_id')
                    partner_name = partner.get('partner_name', 'N/A')
                    # get_contacts_for_partner returns contacts from Contacts table joined with PartnerContacts
                    partner_contacts_list = db_manager.partners_crud.get_contacts_for_partner(partner_id)
                    for contact in partner_contacts_list:
                        row_position = self.contacts_table.rowCount()
                        self.contacts_table.insertRow(row_position)
                        name_item = QTableWidgetItem(contact.get('displayName', contact.get('name', 'N/A')))
                        item_data = {
                            'id': contact.get('contact_id'),
                            'type': 'partner_contact',
                            'source': 'platform',
                            'partner_id': partner_id,
                            'link_id': contact.get('partner_contact_id'), # ID from PartnerContacts table
                            'full_data': contact
                        }
                        name_item.setData(Qt.UserRole, item_data)
                        self.contacts_table.setItem(row_position, 0, name_item)
                        self.contacts_table.setItem(row_position, 1, QTableWidgetItem(contact.get('email', '')))
                        self.contacts_table.setItem(row_position, 2, QTableWidgetItem(contact.get('phone', '')))
                        self.contacts_table.setItem(row_position, 3, QTableWidgetItem("Platform (Partner)"))
                        self.contacts_table.setItem(row_position, 4, QTableWidgetItem(partner_name))
                        self.contacts_table.setItem(row_position, 5, QTableWidgetItem(contact.get('position', '')))
                        self.contacts_table.setItem(row_position, 6, QTableWidgetItem(contact.get('sync_status', 'N/A'))) # Placeholder
        except Exception as e:
            print(f"Error loading partner contacts: {e}")

        # 3. Fetch Company Personnel Contacts
        try:
            # Assuming get_all_company_personnel exists or is handled by iterating companies
            # For now, let's assume direct get_all_company_personnel or simulate it.
            all_personnel = []
            companies = db_manager.companies_crud.get_all_companies() # Requires companies_crud access
            if companies:
                for company_detail in companies:
                    company_id = company_detail.get('company_id')
                    personnel_in_company = db_manager.company_personnel_crud.get_personnel_for_company(company_id)
                    for p in personnel_in_company:
                        p['company_name_for_contact_list'] = company_detail.get('company_name', 'N/A') # Add company name for display
                        all_personnel.append(p)

            if all_personnel:
                for personnel_member in all_personnel:
                    personnel_id = personnel_member.get('personnel_id')
                    personnel_company_name = personnel_member.get('company_name_for_contact_list', 'N/A')
                    # get_contacts_for_personnel returns contacts from Contacts table joined with CompanyPersonnelContacts
                    personnel_contacts_list = db_manager.company_personnel_crud.get_contacts_for_personnel(personnel_id)
                    for contact in personnel_contacts_list:
                        row_position = self.contacts_table.rowCount()
                        self.contacts_table.insertRow(row_position)
                        name_item = QTableWidgetItem(contact.get('displayName', contact.get('name', 'N/A')))
                        item_data = {
                            'id': contact.get('contact_id'),
                            'type': 'personnel_contact',
                            'source': 'platform',
                            'personnel_id': personnel_id,
                            'company_id': personnel_member.get('company_id'),
                            'link_id': contact.get('company_personnel_contact_id'), # ID from CompanyPersonnelContacts
                            'full_data': contact
                        }
                        name_item.setData(Qt.UserRole, item_data)
                        self.contacts_table.setItem(row_position, 0, name_item)
                        self.contacts_table.setItem(row_position, 1, QTableWidgetItem(contact.get('email', '')))
                        self.contacts_table.setItem(row_position, 2, QTableWidgetItem(contact.get('phone', '')))
                        self.contacts_table.setItem(row_position, 3, QTableWidgetItem("Platform (Personnel)"))
                        self.contacts_table.setItem(row_position, 4, QTableWidgetItem(personnel_company_name))
                        self.contacts_table.setItem(row_position, 5, QTableWidgetItem(contact.get('position', '')))
                        self.contacts_table.setItem(row_position, 6, QTableWidgetItem(contact.get('sync_status', 'N/A'))) # Placeholder
        except Exception as e:
            print(f"Error loading company personnel contacts: {e}")

        # 4. TODO: Load Google Contacts (maintain existing logic if any, or integrate from sync logs)
        # This part would query ContactSyncLog and potentially Google People API via sync_service
        # For now, this is a placeholder comment based on the original file's comments.

        self.contacts_table.resizeColumnsToContents()
        self.filter_contacts() # Apply initial filters if any

    def filter_contacts(self):
        """
        Filters the contacts displayed in the table based on search input and type filter.
        """
        search_term = self.search_input.text().lower()
        selected_type_filter = self.type_filter_combo.currentText()

        for row in range(self.contacts_table.rowCount()):
            row_is_visible = True
            item = self.contacts_table.item(row, 0)
            if not item: continue # Should not happen if table is populated correctly

            item_data = item.data(Qt.UserRole)
            if not item_data: # Should ideally not happen
                self.contacts_table.setRowHidden(row, False) # Show if no data to filter on
                continue

            contact_actual_type = item_data.get("type", "").lower() # e.g., "client_contact", "partner_contact", "personnel_contact", "google_contact"
            contact_source_field = item_data.get("source", "").lower() # 'platform' or 'google'

            # Type Filter Logic
            if selected_type_filter == "All":
                pass # No type filtering
            elif selected_type_filter == "Client Contacts":
                if contact_actual_type != "client_contact":
                    row_is_visible = False
            elif selected_type_filter == "Partner Contacts":
                if contact_actual_type != "partner_contact":
                    row_is_visible = False
            elif selected_type_filter == "Company Personnel":
                if contact_actual_type != "personnel_contact":
                    row_is_visible = False
            elif selected_type_filter == "Google Synced Only":
                # This means it's either a pure Google contact OR a platform contact that has a google_contact_id
                # A more robust check might involve querying ContactSyncLog, but for UI filter:
                if not item_data.get("google_contact_id") and contact_source_field != "google":
                    row_is_visible = False

            # Search term filter (if type filter hasn't hidden it already)
            if row_is_visible and search_term:
                match_found = False
                for col in range(self.contacts_table.columnCount()):
                    item = self.contacts_table.item(row, col)
                    if item and search_term in item.text().lower():
                        match_found = True
                        break
                if not match_found:
                    row_is_visible = False

            self.contacts_table.setRowHidden(row, not row_is_visible)

    def on_table_selection_changed(self):
        """
        Handles changes in table selection. Enables/disables action buttons
        based on the selected contact's properties.
        """
        print("Placeholder: Selection changed...")
        selected_items = self.contacts_table.selectedItems()
        if not selected_items:
            self.current_selected_contact_info = None
            self.view_details_button.setEnabled(False)
            self.assign_role_button.setEnabled(False)
            self.manual_sync_button.setEnabled(False)
            return

        # Assuming selection of full rows, first item in selection gives the row.
        selected_row = self.contacts_table.row(selected_items[0])
        first_item_in_row = self.contacts_table.item(selected_row, 0)
        if not first_item_in_row: return # Should not happen if row is selected

        self.current_selected_contact_info = first_item_in_row.data(Qt.UserRole)
        if not self.current_selected_contact_info:
            print(f"Warning: No data stored for selected row {selected_row}")
            self.view_details_button.setEnabled(False)
            self.assign_role_button.setEnabled(False)
            self.manual_sync_button.setEnabled(False)
            return

        print(f"Selected contact info: {self.current_selected_contact_info}")

        contact_actual_type = self.current_selected_contact_info.get("type", "")
        contact_source_field = self.current_selected_contact_info.get("source", "") # 'platform' or 'google'

        # View/Edit Details: Always enabled if a contact is selected
        self.view_details_button.setEnabled(True)

        # Assign Role: Enabled if it's a Google-originated contact not yet fully linked/identified as a platform entity.
        # A simple check is if its type is 'google_contact' (meaning it's primarily known by its Google ID).
        if contact_actual_type == "google_contact":
            self.assign_role_button.setEnabled(True)
        else:
            self.assign_role_button.setEnabled(False)

        # Manual Sync: Enabled if contact has a Google presence or is a platform contact.
        # (Essentially, any contact that could potentially be part of a sync operation).
        # A more refined logic would check if sync is actually enabled/configured for the user.
        self.manual_sync_button.setEnabled(True) # Simplistic: enable if any contact is selected


    def handle_view_details(self):
        """
        Handles the "View/Edit Details" button click.
        Opens an appropriate dialog based on the selected contact's type.
        For this subtask, it will show an informational QMessageBox.
        """
        if not self.current_selected_contact_info:
            QMessageBox.warning(self, "No Selection", "Please select a contact to view details.")
            return

        data = self.current_selected_contact_info
        contact_type = data.get("type", "N/A")
        contact_id = data.get("id", "N/A") # Central Contact ID
        link_id = data.get("link_id", "N/A") # ID from the link table (ClientContacts, PartnerContacts, etc.)
        source = data.get("source", "N/A")

        info_str = f"Type: {contact_type.title().replace('_', ' ')}\nSource: {source.title()}\nCentral Contact ID: {contact_id}\nLink ID: {link_id}\n\n"

        if contact_type == "client_contact":
            info_str += f"Client ID: {data.get('client_id', 'N/A')}\n"
        elif contact_type == "partner_contact":
            info_str += f"Partner ID: {data.get('partner_id', 'N/A')}\n"
        elif contact_type == "personnel_contact":
            info_str += f"Personnel ID: {data.get('personnel_id', 'N/A')}\nCompany ID: {data.get('company_id', 'N/A')}\n"
        elif contact_type == "google_contact":
            info_str += f"Google Contact ID: {data.get('google_contact_id', 'N/A')}\n"

        info_str += f"\nFull Data: {data.get('full_data', {})}"

        QMessageBox.information(self, "Contact Details", info_str)
        # In a full implementation, this would open the respective edit dialogs:
        # if contact_type == "client_contact": # Open Client's contact editor
        # elif contact_type == "partner_contact": # Open Partner's contact editor (EditPartnerContactDialog)
        # elif contact_type == "personnel_contact": # Open Personnel's contact editor (EditPersonnelContactDialog)


    def handle_assign_role(self):
        """
        Handles the "Assign Role/Type" button click.
        For a Google-originated contact, this would open a dialog to create a new
        platform contact (Client, Partner, etc.) linked to this Google contact.
        """
        if not self.current_selected_contact_info or self.current_selected_contact_info.get("source") != "google":
            QMessageBox.warning(self, "Invalid Selection", "Please select a Google-originated contact to assign a role.")
            return

        google_contact_id = self.current_selected_contact_info.get("google_contact_id")
        print(f"Placeholder: Assign role clicked for Google Contact ID: {google_contact_id}")
        # Placeholder: Open a dialog that allows user to choose:
        # 1. Link to existing platform contact (search and link)
        # 2. Create new platform contact (Client, Partner, etc.) based on Google data.
        # This would involve _transform_google_contact_to_platform and then db_manager.add_...
        # followed by updating the ContactSyncLog.
        QMessageBox.information(self, "Assign Role", f"Would open dialog to assign a platform role to Google Contact ID: {google_contact_id}")


    def handle_manual_sync(self):
        """
        Handles the "Manual Sync" button click.
        Triggers the synchronization process for the selected contact.
        """
        if not self.current_selected_contact_info:
            QMessageBox.warning(self, "No Selection", "Please select a contact to manually sync.")
            return

        contact_id = self.current_selected_contact_info.get("id") # Platform ID
        google_contact_id = self.current_selected_contact_info.get("google_contact_id")
        contact_type = self.current_selected_contact_info.get("type")
        user_id = "current_logged_in_user_id" # Placeholder: This needs to be the actual user_id

        print(f"Placeholder: Manual sync clicked for contact type '{contact_type}', ID: '{contact_id}', Google ID: '{google_contact_id}'")

        # if not sync_service:
        #     QMessageBox.critical(self, "Error", "Sync service is not available.")
        #     return

        # Placeholder: Call appropriate sync_service function
        # if contact_source == "platform" and contact_id:
        #    sync_service.handle_contact_change_from_platform(user_id, contact_id, contact_type, 'update') # Force update
        # elif contact_source == "google" and google_contact_id:
        #    # More complex: might need to fetch, transform, and then decide action based on sync log.
        #    # Or trigger a targeted version of _sync_google_to_platform for this one contact.
        #    pass
        # else:
        #    QMessageBox.information(self, "Manual Sync", "Sync action for this contact type is not yet defined.")

        QMessageBox.information(self, "Manual Sync", f"Would trigger manual sync for: {self.current_selected_contact_info}")


# --- Main (for testing) ---
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Basic check for db_manager (can be expanded to mock if needed for standalone testing)
    if db_manager is None:
        print("CRITICAL: db_manager is None. The ContactListWidget might not function fully.")
        # Optionally, create a mock db_manager for basic UI testing
        class MockDBManager:
            def get_all_contacts(self): return []
            # Add other methods that might be called during init or load_contacts
        # db_manager = MockDBManager()
        # print("Using mock db_manager for UI testing.")


    main_widget = ContactListWidget()
    main_widget.setGeometry(100, 100, 900, 600) # x, y, width, height
    main_widget.show()

    sys.exit(app.exec_())
