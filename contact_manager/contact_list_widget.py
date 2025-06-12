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
        # This section will be replaced with actual data fetching logic.

        # Example 1: Dummy Platform Client Contact
        row_position = self.contacts_table.rowCount()
        self.contacts_table.insertRow(row_position)
        self.contacts_table.setItem(row_position, 0, QTableWidgetItem("John Doe (Client)"))
        self.contacts_table.setItem(row_position, 1, QTableWidgetItem("john.doe@exampleclient.com"))
        self.contacts_table.setItem(row_position, 2, QTableWidgetItem("123-456-7890"))
        self.contacts_table.setItem(row_position, 3, QTableWidgetItem("Platform (Client)"))
        self.contacts_table.setItem(row_position, 4, QTableWidgetItem("Doe Corp"))
        self.contacts_table.setItem(row_position, 5, QTableWidgetItem("CEO"))
        self.contacts_table.setItem(row_position, 6, QTableWidgetItem("Synced"))
        # Store raw data in a user role for later retrieval
        self.contacts_table.item(row_position, 0).setData(Qt.UserRole, {"id": "client_1", "type": "client_contact", "source": "platform"})

        # Example 2: Dummy Google-Originated Contact (not yet linked)
        row_position = self.contacts_table.rowCount()
        self.contacts_table.insertRow(row_position)
        self.contacts_table.setItem(row_position, 0, QTableWidgetItem("Jane Smith (Google)"))
        self.contacts_table.setItem(row_position, 1, QTableWidgetItem("jane.smith@gmail.com"))
        self.contacts_table.setItem(row_position, 2, QTableWidgetItem("987-654-3210"))
        self.contacts_table.setItem(row_position, 3, QTableWidgetItem("Google"))
        self.contacts_table.setItem(row_position, 4, QTableWidgetItem("Smith Innovations"))
        self.contacts_table.setItem(row_position, 5, QTableWidgetItem("Lead Developer"))
        self.contacts_table.setItem(row_position, 6, QTableWidgetItem("Pending Link"))
        self.contacts_table.item(row_position, 0).setData(Qt.UserRole, {"google_contact_id": "people/c_google123", "type": "google_contact", "source": "google"})

        # Actual fetching logic would involve:
        # 1. db_manager.get_all_contacts() (for client contacts from Contacts table)
        #    - Need to join with ClientContacts and Clients for full info.
        # 2. db_manager.get_all_partner_contacts() (if such a function exists, or iterate partners then contacts)
        # 3. db_manager.get_all_company_personnel() (if exists)
        # 4. Iterate through db_manager.get_all_sync_logs_for_user(current_user_id)
        #    - If local_contact_id is null/placeholder, it's a Google-originated contact.
        #    - If local_contact_id is present, it's a platform contact that's also on Google.
        #    - Get sync status and etags from the log.
        #
        # Populate table rows with QTableWidgetItems. Store identifiers and source type
        # in item data (e.g., item.setData(Qt.UserRole, {'id': contact_id, 'type': 'client'})).

        self.contacts_table.resizeColumnsToContents()
        self.filter_contacts() # Apply initial filters if any

    def filter_contacts(self):
        """
        Filters the contacts displayed in the table based on search input and type filter.
        This is a basic string matching filter. More sophisticated filtering might be needed.
        """
        print("Placeholder: Filtering contacts...")
        search_term = self.search_input.text().lower()
        selected_type_filter = self.type_filter_combo.currentText()

        for row in range(self.contacts_table.rowCount()):
            row_is_visible = True

            # Type filter
            item_data = self.contacts_table.item(row, 0).data(Qt.UserRole) if self.contacts_table.item(row, 0) else {}
            contact_source_type = item_data.get("type", "").lower() # e.g., "client_contact", "google_contact"

            if selected_type_filter == "Client Contacts" and "client" not in contact_source_type:
                row_is_visible = False
            elif selected_type_filter == "Partner Contacts" and "partner" not in contact_source_type:
                row_is_visible = False
            elif selected_type_filter == "Company Personnel" and "personnel" not in contact_source_type: # Assuming "personnel" in type
                row_is_visible = False
            elif selected_type_filter == "Google Synced Only" and "google" not in contact_source_type and item_data.get("source") != "google":
                 # This logic needs refinement: "Google Synced Only" could mean "exists in ContactSyncLog"
                 # or "originated from Google". For now, using item_data.get("source") == "google"
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

        contact_type = self.current_selected_contact_info.get("type")
        contact_source = self.current_selected_contact_info.get("source") # 'platform' or 'google'

        # View/Edit Details: Always enabled if a contact is selected, behavior depends on type.
        self.view_details_button.setEnabled(True)

        # Assign Role: Enabled if it's a Google-originated contact not yet fully linked to a platform role.
        if contact_source == "google" and contact_type == "google_contact": # i.e. not yet a platform entity
            # More specific check: if it's in ContactSyncLog but local_contact_id is placeholder
            self.assign_role_button.setEnabled(True)
        else:
            self.assign_role_button.setEnabled(False)

        # Manual Sync: Enabled if contact has a Google presence (i.e., in ContactSyncLog or is a Google contact).
        # And if sync_service is available.
        if (contact_source == "google" or self.current_selected_contact_info.get("google_contact_id") or
           (contact_source == "platform" and self.current_selected_contact_info.get("id"))): # Platform contacts can be synced
            # Check if sync_service is available (placeholder for now)
            # self.manual_sync_button.setEnabled(sync_service is not None)
            self.manual_sync_button.setEnabled(True) # Placeholder: always true if selectable
        else:
            self.manual_sync_button.setEnabled(False)


    def handle_view_details(self):
        """
        Handles the "View/Edit Details" button click.
        Opens an appropriate dialog based on the selected contact's type.
        """
        if not self.current_selected_contact_info:
            QMessageBox.warning(self, "No Selection", "Please select a contact to view details.")
            return

        contact_id = self.current_selected_contact_info.get("id") # Platform ID
        google_contact_id = self.current_selected_contact_info.get("google_contact_id")
        contact_type = self.current_selected_contact_info.get("type")

        print(f"Placeholder: View details clicked for contact type '{contact_type}', ID: '{contact_id}', Google ID: '{google_contact_id}'")

        # Placeholder: Logic to open different dialogs
        if contact_type == "client_contact" and contact_id:
            # Example: Open ClientContactDialog(contact_id)
            QMessageBox.information(self, "View Details", f"Would open details for Platform Client Contact ID: {contact_id}")
        elif contact_type == "google_contact" and google_contact_id:
            # Example: Open a dialog showing Google contact details, possibly allowing linking
            QMessageBox.information(self, "View Details", f"Would open details for Google Contact ID: {google_contact_id}")
        else:
            QMessageBox.information(self, "View Details", f"Viewing details for: {self.current_selected_contact_info}")


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
