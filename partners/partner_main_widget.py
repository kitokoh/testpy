# partners/partner_main_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
                             QLineEdit, QHBoxLayout, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QMessageBox, QApplication, QComboBox, QDialog)
from PyQt5.QtCore import Qt
from db import get_all_partner_categories, get_all_partners, get_partners_in_category, get_categories_for_partner, get_partner_by_id
from .partner_dialog import PartnerDialog
from .partner_category_dialog import PartnerCategoryDialog
from contact_manager.sync_service import handle_contact_change_from_platform # For Google Sync

class PartnerMainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Partner Management")
        # self.current_user_id = "user_xyz" # This should be set by the main application upon login

        layout = QVBoxLayout(self)

        # Top layout for search, filter, and add button
        filter_controls_layout = QHBoxLayout() # Renamed for clarity
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Partners (Name, Email, Location)...")
        filter_controls_layout.addWidget(self.search_input)

        self.category_filter_combo = QComboBox()
        filter_controls_layout.addWidget(QLabel("Filter by Category:")) # Label for clarity
        filter_controls_layout.addWidget(self.category_filter_combo)

        # Status Filter
        self.status_filter_combo = QComboBox()
        filter_controls_layout.addWidget(QLabel("Filter by Status:"))
        filter_controls_layout.addWidget(self.status_filter_combo)

        # Partner Type Filter
        self.partner_type_filter_combo = QComboBox()
        filter_controls_layout.addWidget(QLabel("Filter by Type:"))
        filter_controls_layout.addWidget(self.partner_type_filter_combo)

        self.add_partner_button = QPushButton("Add Partner")
        filter_controls_layout.addWidget(self.add_partner_button)

        self.manage_categories_button = QPushButton("Manage Categories")
        filter_controls_layout.addWidget(self.manage_categories_button)
        layout.addLayout(filter_controls_layout)

        # Action buttons layout
        action_buttons_layout = QHBoxLayout()
        self.send_email_button = QPushButton("Send Email")
        self.send_email_button.setEnabled(False)
        action_buttons_layout.addWidget(self.send_email_button)

        self.send_whatsapp_button = QPushButton("Send WhatsApp")
        self.send_whatsapp_button.setEnabled(False)
        action_buttons_layout.addWidget(self.send_whatsapp_button)
        action_buttons_layout.addStretch() # Add stretch to push buttons to the left
        layout.addLayout(action_buttons_layout)

        # Table for displaying partners
        self.partners_table = QTableWidget()
        self.partners_table.setColumnCount(7) # Increased for Status and Partner Type
        self.partners_table.setHorizontalHeaderLabels(["Name", "Email", "Phone", "Location", "Categories", "Status", "Partner Type"])
        self.partners_table.setEditTriggers(QTableWidget.NoEditTriggers) # Non-editable directly
        self.partners_table.setSelectionBehavior(QTableWidget.SelectRows) # Select whole rows
        self.partners_table.setSelectionMode(QAbstractItemView.SingleSelection) # Select one row at a time
        self.partners_table.verticalHeader().setVisible(False) # Hide vertical header
        # self.partners_table.horizontalHeader().setStretchLastSection(True) # No longer last section stretches
        self.partners_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Name
        self.partners_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Email
        self.partners_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Phone
        self.partners_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Location
        self.partners_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch) # Categories
        self.partners_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Status
        self.partners_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents) # Partner Type
        self.partners_table.setSortingEnabled(True)
        layout.addWidget(self.partners_table)

        # Connect signals
        self.add_partner_button.clicked.connect(self.open_add_partner_dialog)
        self.manage_categories_button.clicked.connect(self.open_manage_categories_dialog)
        self.partners_table.itemDoubleClicked.connect(self.handle_table_double_click)
        self.partners_table.itemSelectionChanged.connect(self.update_action_button_states)
        self.send_email_button.clicked.connect(self.handle_send_email)
        self.send_whatsapp_button.clicked.connect(self.handle_send_whatsapp)
        self.search_input.textChanged.connect(self.filter_partners_list) # Connect search
        self.category_filter_combo.currentIndexChanged.connect(self.filter_partners_list) # Connect category filter
        self.status_filter_combo.currentIndexChanged.connect(self.filter_partners_list)
        self.partner_type_filter_combo.currentIndexChanged.connect(self.filter_partners_list)

        self.load_status_filter()
        self.load_partner_type_filter()
        self.load_category_filter() # Load categories into filter
        self.load_partners() # Initial load of all partners
        self.update_action_button_states() # Initial state for action buttons

    def load_status_filter(self):
        self.status_filter_combo.blockSignals(True)
        self.status_filter_combo.clear()
        self.status_filter_combo.addItem("All Statuses", None) # UserData is None for "All"
        self.status_filter_combo.addItems(["Active", "Inactive", "Prospect", "Onboarding", "Terminated"])
        # For actual filtering by text, currentText() will be used if currentData() is not None.
        # If we wanted to pass the text as currentData for actual items:
        # for item in ["Active", "Inactive", "Prospect", "Onboarding", "Terminated"]:
        #    self.status_filter_combo.addItem(item, item) # Store text as data
        self.status_filter_combo.blockSignals(False)

    def load_partner_type_filter(self):
        self.partner_type_filter_combo.blockSignals(True)
        self.partner_type_filter_combo.clear()
        self.partner_type_filter_combo.addItem("All Types", None) # UserData is None for "All"
        self.partner_type_filter_combo.addItems(["Supplier", "Reseller", "Service Provider", "Referral", "Other"])
        # Similar to status filter, if text is needed as data:
        # for item in ["Supplier", "Reseller", "Service Provider", "Referral", "Other"]:
        #    self.partner_type_filter_combo.addItem(item, item)
        self.partner_type_filter_combo.blockSignals(False)

    def load_category_filter(self):
        current_category_id = self.category_filter_combo.currentData()
        self.category_filter_combo.blockSignals(True) # Block signals during repopulation
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("All Categories", None)
        try:
            categories = get_all_partner_categories()
            if categories:
                for category in categories:
                    # Assuming category_id is the correct key from get_all_partner_categories
                    self.category_filter_combo.addItem(category['category_name'], category['partner_category_id'])


            # Restore selection
            if current_category_id is not None:
                index = self.category_filter_combo.findData(current_category_id)
                if index != -1:
                    self.category_filter_combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Categories", f"Could not load categories for filter: {e}")
        finally:
            self.category_filter_combo.blockSignals(False) # Unblock signals

    def update_action_button_states(self):
        selected_items = self.partners_table.selectedItems()
        is_partner_selected = bool(selected_items)
        self.send_email_button.setEnabled(is_partner_selected)
        self.send_whatsapp_button.setEnabled(is_partner_selected)

    def get_selected_partner_id(self):
        selected_items = self.partners_table.selectedItems()
        if not selected_items:
            return None
        current_row = self.partners_table.currentRow()
        name_item = self.partners_table.item(current_row, 0)
        if name_item:
            return name_item.data(Qt.UserRole)
        return None

    def handle_send_email(self):
        partner_id = self.get_selected_partner_id()
        if not partner_id:
            QMessageBox.warning(self, "Send Email", "No partner selected.")
            return
        partner = get_partner_by_id(partner_id)
        if partner and partner.get('email'):
            # ... (email sending logic)
            QMessageBox.information(self, "Send Email", f"Email dialog for {partner['email']} would open here.")
        elif partner:
            QMessageBox.warning(self, "Send Email", f"Partner '{partner.get('name')}' does not have an email address.")
        else:
            QMessageBox.warning(self, "Send Email", "Could not retrieve partner details.")

    def handle_send_whatsapp(self):
        partner_id = self.get_selected_partner_id()
        if not partner_id:
            QMessageBox.warning(self, "Send WhatsApp", "No partner selected.")
            return
        partner = get_partner_by_id(partner_id)
        if partner and partner.get('phone'):
            # ... (whatsapp logic)
            QMessageBox.information(self, "Send WhatsApp", f"WhatsApp for {partner['phone']} would open here.")
        elif partner:
            QMessageBox.warning(self, "Send WhatsApp", f"Partner '{partner.get('name')}' does not have a phone number.")
        else:
            QMessageBox.warning(self, "Send WhatsApp", "Could not retrieve partner details.")

    def filter_partners_list(self):
        search_text = self.search_input.text().lower().strip()
        selected_category_id = self.category_filter_combo.currentData()
        selected_status = self.status_filter_combo.currentData() if self.status_filter_combo.currentIndex() > 0 else None
        selected_type = self.partner_type_filter_combo.currentData() if self.partner_type_filter_combo.currentIndex() > 0 else None
        # Pass text directly for status and type if "All" is not selected, otherwise None
        status_filter_value = self.status_filter_combo.currentText() if self.status_filter_combo.currentData() is not None else None
        type_filter_value = self.partner_type_filter_combo.currentText() if self.partner_type_filter_combo.currentData() is not None else None

        self.load_partners(search_term=search_text, category_id_filter=selected_category_id,
                           status_filter=status_filter_value, type_filter=type_filter_value)

    def load_partners(self, search_term=None, category_id_filter=None, status_filter=None, type_filter=None):
        self.partners_table.setRowCount(0)
        try:
            all_partners = get_all_partners() # This fetches all partners, including new fields
            if all_partners is None: all_partners = []

            partners_to_display = list(all_partners) # Start with all partners

            # Filter by Category (DB query if possible, or client-side)
            # Current implementation: if category_id_filter is applied, it re-queries.
            # For simplicity with new filters, let's assume all_partners is the base and we filter client-side from here.
            # If performance becomes an issue, get_all_partners in CRUD would need to accept more filters.
            if category_id_filter is not None:
                # This part assumes get_partners_in_category returns full partner details,
                # or we need to filter all_partners based on IDs from get_partners_in_category.
                # For now, let's simplify and assume client-side filtering on all_partners for all dropdowns.
                # This means get_all_partners() is the primary source, and then we filter it.
                # So, we'll adjust the logic slightly:
                ids_in_category = {p['partner_id'] for p in get_partners_in_category(category_id_filter) or []}
                partners_to_display = [p for p in partners_to_display if p['partner_id'] in ids_in_category]


            # Client-side filtering for search term
            if search_term:
                filtered_by_search = []
                for partner in partners_to_display:
                    # Ensure 'partner_name' is used as 'name' might not be the primary key in the partner dict
                    if (search_term in partner.get('partner_name', '').lower() or
                        search_term in (partner.get('email', '') or '').lower() or
                        # search_term in (partner.get('location', '') or '').lower() or # 'location' is not a direct field
                        search_term in (partner.get('address', '') or '').lower() or # Use 'address'
                        search_term in (partner.get('notes', '') or '').lower()):
                        filtered_by_search.append(partner)
                partners_to_display = filtered_by_search

            # Client-side filtering for Status
            if status_filter:
                partners_to_display = [p for p in partners_to_display if p.get('status') == status_filter]

            # Client-side filtering for Partner Type
            if type_filter:
                partners_to_display = [p for p in partners_to_display if p.get('partner_type') == type_filter]


            self.partners_table.setSortingEnabled(False)
            for partner in partners_to_display:
                row_position = self.partners_table.rowCount()
                self.partners_table.insertRow(row_position)

                # Use 'partner_name' from DB, fallback to 'name' if necessary
                name_item = QTableWidgetItem(partner.get('partner_name', partner.get('name', '')))
                name_item.setData(Qt.UserRole, partner.get('partner_id'))
                self.partners_table.setItem(row_position, 0, name_item)
                self.partners_table.setItem(row_position, 1, QTableWidgetItem(partner.get('email', '')))
                self.partners_table.setItem(row_position, 2, QTableWidgetItem(partner.get('phone', '')))
                self.partners_table.setItem(row_position, 3, QTableWidgetItem(partner.get('address', ''))) # Use 'address'

                # Categories
                categories_list = get_categories_for_partner(partner.get('partner_id'))
                # Ensure 'category_name' is used as 'name' might be ambiguous
                categories_str = ", ".join([cat.get('category_name', '') for cat in categories_list]) if categories_list else ""
                self.partners_table.setItem(row_position, 4, QTableWidgetItem(categories_str))

                # New columns
                self.partners_table.setItem(row_position, 5, QTableWidgetItem(partner.get('status', '')))
                self.partners_table.setItem(row_position, 6, QTableWidgetItem(partner.get('partner_type', '')))

            self.partners_table.setSortingEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load partners: {e}")

    def open_add_partner_dialog(self):
        dialog = PartnerDialog(parent=self)
        # Conceptual: Pass current_user_id to dialog if available and needed by dialog's own sync hooks
        # current_user_id_value = getattr(self, 'current_user_id', None) # Safely get current_user_id
        # if current_user_id_value:
        #     dialog.current_user_id = current_user_id_value
        # else:
        #     print("Warning: current_user_id not set in PartnerMainWidget, cannot pass to PartnerDialog for sync hooks.")


        if dialog.exec_() == QDialog.Accepted:
            self.load_partners() # Refresh table
            # Comment: The PartnerDialog (in partner_dialog.py) should be modified.
            # After successfully saving a *new* partner (if it has primary contact fields like email/phone)
            # or more importantly, when adding/editing/deleting contacts in the PartnerContacts table
            # (which is likely managed by a different dialog specific to partner contacts),
            # call handle_contact_change_from_platform.
            # Example for a new Partner's own details (if they are synced):
            # if dialog.new_partner_id and current_user_id_value:
            #     try:
            #         handle_contact_change_from_platform(
            #             user_id=str(current_user_id_value),
            #             local_contact_id=str(dialog.new_partner_id), # This is the partner_id
            #             local_contact_type='partner_main_details', # Type for partner's own record
            #             change_type='create'
            #         )
            #     except Exception as e:
            #         print(f"Error triggering sync for new partner's main details: {e}")
            #
            # For individual PartnerContacts (from PartnerContacts table), the hooks would be:
            # - After adding a PartnerContact: type='partner_contact', change_type='create'
            # - After updating a PartnerContact: type='partner_contact', change_type='update'
            # - Before deleting a PartnerContact: type='partner_contact', change_type='delete'

    def handle_table_double_click(self, item):
        if not item: return
        current_row = item.row()
        name_item = self.partners_table.item(current_row, 0)
        if name_item:
            self.open_edit_partner_dialog(name_item)

    def open_edit_partner_dialog(self, name_item_clicked):
        partner_id = name_item_clicked.data(Qt.UserRole)
        if partner_id:
            dialog = PartnerDialog(partner_id=partner_id, parent=self)
            # current_user_id_value = getattr(self, 'current_user_id', None)
            # if current_user_id_value:
            #     dialog.current_user_id = current_user_id_value
            # else:
            #     print("Warning: current_user_id not set in PartnerMainWidget, cannot pass to PartnerDialog for sync hooks.")

            if dialog.exec_() == QDialog.Accepted:
                self.load_partners() # Refresh table
                # Comment: Similar to add, the PartnerDialog (in partner_dialog.py)
                # should call handle_contact_change_from_platform if the partner's own
                # direct contact details (if synced) are updated.
                # Example for updating Partner's own details:
                # if current_user_id_value:
                #     try:
                #         handle_contact_change_from_platform(
                #             user_id=str(current_user_id_value),
                #             local_contact_id=str(partner_id),
                #             local_contact_type='partner_main_details',
                #             change_type='update'
                #         )
                #     except Exception as e:
                #         print(f"Error triggering sync for updated partner's main details: {e}")
                # See note in open_add_partner_dialog regarding individual PartnerContacts.

    def open_manage_categories_dialog(self):
        category_dialog = PartnerCategoryDialog(parent=self)
        if category_dialog.exec_() == QDialog.Accepted:
            self.load_category_filter()
            self.filter_partners_list()

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    # Example: Set a current_user_id if needed for testing the conceptual comments
    # main_widget = PartnerMainWidget()
    # main_widget.current_user_id = "test_user_partners_widget"
    # main_widget.show()
    PartnerMainWidget().show() # Simpler show for basic UI test
    sys.exit(app.exec_())
