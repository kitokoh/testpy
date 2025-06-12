# partners/partner_main_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
                             QLineEdit, QHBoxLayout, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QMessageBox, QApplication, QComboBox) # Added QComboBox
from PyQt5.QtCore import Qt
import db.crud as db_manager
from .partner_dialog import PartnerDialog
from .partner_category_dialog import PartnerCategoryDialog

class PartnerMainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Partner Management")

        layout = QVBoxLayout(self)

        # Top layout for search, filter, and add button
        filter_controls_layout = QHBoxLayout() # Renamed for clarity
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Partners (Name, Email, Location)...")
        filter_controls_layout.addWidget(self.search_input)

        self.category_filter_combo = QComboBox()
        filter_controls_layout.addWidget(QLabel("Filter by Category:")) # Label for clarity
        filter_controls_layout.addWidget(self.category_filter_combo)

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
        self.partners_table.setColumnCount(5)
        self.partners_table.setHorizontalHeaderLabels(["Name", "Email", "Phone", "Location", "Categories"])
        self.partners_table.setEditTriggers(QTableWidget.NoEditTriggers) # Non-editable directly
        self.partners_table.setSelectionBehavior(QTableWidget.SelectRows) # Select whole rows
        self.partners_table.setSelectionMode(QAbstractItemView.SingleSelection) # Select one row at a time
        self.partners_table.verticalHeader().setVisible(False) # Hide vertical header
        self.partners_table.horizontalHeader().setStretchLastSection(True)
        self.partners_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
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

        self.load_category_filter() # Load categories into filter
        self.load_partners() # Initial load of all partners
        self.update_action_button_states() # Initial state for action buttons

    def load_category_filter(self):
        current_category_id = self.category_filter_combo.currentData()
        self.category_filter_combo.blockSignals(True) # Block signals during repopulation
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("All Categories", None)
        try:
            categories = db_manager.get_all_partner_categories()
            if categories:
                for category in categories:
                    self.category_filter_combo.addItem(category['name'], category['category_id'])

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
        # Assuming the partner_id is stored in the UserRole of the first column item (Name)
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

        partner = db_manager.get_partner_by_id(partner_id)
        if partner and partner.get('email'):
            partner_email = partner['email']
            QMessageBox.information(self, "Send Email",
                                    f"Email dialog for {partner_email} would open here.\n"
                                    "(Actual email functionality not yet implemented).")
            # In a real app:
            # email_dialog = EmailComposeDialog(to_address=partner_email, parent=self)
            # email_dialog.exec_()
        elif partner:
            QMessageBox.warning(self, "Send Email", f"Partner '{partner.get('name')}' does not have an email address.")
        else:
            QMessageBox.warning(self, "Send Email", "Could not retrieve partner details.")

    def handle_send_whatsapp(self):
        partner_id = self.get_selected_partner_id()
        if not partner_id:
            QMessageBox.warning(self, "Send WhatsApp", "No partner selected.")
            return

        partner = db_manager.get_partner_by_id(partner_id)
        if partner and partner.get('phone'):
            partner_phone = partner['phone']
            clipboard = QApplication.clipboard()
            clipboard.setText(partner_phone)
            QMessageBox.information(self, "Send WhatsApp",
                                    f"Phone number '{partner_phone}' for partner '{partner.get('name')}' has been copied to clipboard. "
                                    "You can paste it into WhatsApp.")
        elif partner:
            QMessageBox.warning(self, "Send WhatsApp", f"Partner '{partner.get('name')}' does not have a phone number.")
        else:
            QMessageBox.warning(self, "Send WhatsApp", "Could not retrieve partner details.")

    def filter_partners_list(self):
        search_text = self.search_input.text().lower().strip()
        selected_category_id = self.category_filter_combo.currentData()
        self.load_partners(search_term=search_text, category_id_filter=selected_category_id)

    def load_partners(self, search_term=None, category_id_filter=None):
        self.partners_table.setRowCount(0)
        try:
            all_partners = db_manager.get_all_partners()
            if all_partners is None: all_partners = []

            partners_to_display = []

            if category_id_filter is not None:
                # Get partner IDs for the selected category
                partner_ids_in_category_list = db_manager.get_partners_in_category(category_id_filter)
                # Ensure this returns a list of dicts with 'partner_id'
                if partner_ids_in_category_list is not None:
                    ids_in_category = {p['partner_id'] for p in partner_ids_in_category_list}
                    partners_to_display = [p for p in all_partners if p['partner_id'] in ids_in_category]
                else: # No partners in this category or error
                    partners_to_display = [] # Start with empty if category filter yields nothing
            else:
                partners_to_display = list(all_partners) # Make a mutable copy

            if search_term:
                filtered_by_search = []
                for partner in partners_to_display: # Iterate over already category-filtered list
                    name = partner.get('name', '').lower()
                    email = partner.get('email', '').lower() if partner.get('email') else ''
                    location = partner.get('location', '').lower() if partner.get('location') else ''
                    notes = partner.get('notes', '').lower() if partner.get('notes') else '' # Also search notes

                    if (search_term in name or
                        search_term in email or
                        search_term in location or
                        search_term in notes):
                        filtered_by_search.append(partner)
                partners_to_display = filtered_by_search

            self.partners_table.setSortingEnabled(False)
            for partner in partners_to_display:
                row_position = self.partners_table.rowCount()
                self.partners_table.insertRow(row_position)

                name_item = QTableWidgetItem(partner.get('name'))
                name_item.setData(Qt.UserRole, partner.get('partner_id'))

                self.partners_table.setItem(row_position, 0, name_item)
                self.partners_table.setItem(row_position, 1, QTableWidgetItem(partner.get('email')))
                self.partners_table.setItem(row_position, 2, QTableWidgetItem(partner.get('phone')))
                self.partners_table.setItem(row_position, 3, QTableWidgetItem(partner.get('location')))

                categories_list = db_manager.get_categories_for_partner(partner.get('partner_id'))
                categories_str = ", ".join([cat.get('name') for cat in categories_list]) if categories_list else ""
                self.partners_table.setItem(row_position, 4, QTableWidgetItem(categories_str))

            self.partners_table.setSortingEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load partners: {e}")

    def open_add_partner_dialog(self):
        dialog = PartnerDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_partners() # Refresh table

    def handle_table_double_click(self, item):
        if not item: return
        current_row = item.row()
        name_item = self.partners_table.item(current_row, 0) # Name is in column 0
        if name_item:
            self.open_edit_partner_dialog(name_item)

    def open_edit_partner_dialog(self, name_item_clicked):
        partner_id = name_item_clicked.data(Qt.UserRole)
        if partner_id:
            dialog = PartnerDialog(partner_id=partner_id, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_partners() # Refresh table

    def open_manage_categories_dialog(self):
        category_dialog = PartnerCategoryDialog(parent=self)
        # We check if dialog.exec_() is QDialog.Accepted, though for PartnerCategoryDialog,
        # it just has an "Ok" button which maps to accept(). Changes are live in DB.
        if category_dialog.exec_() == QDialog.Accepted:
            self.load_category_filter() # Reload categories in filter
            self.filter_partners_list() # Refresh partner list with current filters

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    main_widget = PartnerMainWidget()
    main_widget.show()
    sys.exit(app.exec_())
