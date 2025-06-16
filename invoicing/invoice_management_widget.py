import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QTableWidget, QHeaderView,
    QTableWidgetItem, QAbstractItemView, QSpacerItem, QSizePolicy,
    QApplication, QMessageBox
)
from PyQt5.QtCore import QDate, Qt, QModelIndex
from PyQt5.QtGui import QIcon, QColor

# Assuming APP_ROOT_DIR setup is done in the main application for db access
# For standalone testing, this widget might need to ensure paths are set if not using compiled resources/modules.
# For now, assume db.cruds are importable.
from db.cruds import invoices_crud
from db.cruds import clients_crud # Assuming this exists and has get_client_by_id

# Dialogs
from .invoice_details_dialog import InvoiceDetailsDialog
from .record_payment_dialog import RecordPaymentDialog
from .manual_invoice_dialog import ManualInvoiceDialog

# Assuming an icon resource file is set up, e.g., resources.qrc compiled to resources_rc.py
# If not, QIcon() or QIcon.fromTheme() might be used, or direct paths.
# For now, we'll use the provided resource paths.
# import resources_rc # Example: if you have a compiled resource file

class InvoiceManagementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("invoiceManagementWidget")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Filtering Section ---
        filter_controls_widget = QWidget()
        filter_controls_widget.setObjectName("invoiceFilterControlsWidget")
        filter_layout = QHBoxLayout(filter_controls_widget) # Apply layout to the new widget

        filter_layout.addWidget(QLabel("Search:"))
        self.search_invoice_input = QLineEdit()
        self.search_invoice_input.setPlaceholderText("Invoice #, Client ID/Name...")
        filter_layout.addWidget(self.search_invoice_input)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["All", "Paid", "Unpaid", "Overdue", "Partially Paid"])
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addWidget(QLabel("Issue Date From:"))
        self.issue_date_from_edit = QDateEdit()
        self.issue_date_from_edit.setCalendarPopup(True)
        self.default_issue_date_from = QDate(2000, 1, 1) # Arbitrary far past
        self.issue_date_from_edit.setDate(self.default_issue_date_from)
        self.issue_date_from_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.issue_date_from_edit)

        filter_layout.addWidget(QLabel("To:"))
        self.issue_date_to_edit = QDateEdit()
        self.issue_date_to_edit.setCalendarPopup(True)
        self.default_issue_date_to = QDate.currentDate().addYears(5) # Arbitrary far future
        self.issue_date_to_edit.setDate(self.default_issue_date_to)
        self.issue_date_to_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.issue_date_to_edit)

        self.apply_filters_button = QPushButton("Apply Filters")
        self.apply_filters_button.setObjectName("applyFiltersButton")
        self.apply_filters_button.setIcon(QIcon(":/icons/filter.svg")) # Example icon
        self.apply_filters_button.clicked.connect(self.load_invoices) # Connect to load_invoices
        filter_layout.addWidget(self.apply_filters_button)

        filter_layout.addStretch() # Push controls to the left

        # filter_controls_widget.setLayout(filter_layout) # Already set in QHBoxLayout constructor
        main_layout.addWidget(filter_controls_widget)


        # --- Actions Section ---
        # Wrap actions_layout in a QWidget for potential specific styling if needed
        actions_container_widget = QWidget()
        actions_container_widget.setObjectName("invoiceActionsContainerWidget")
        actions_layout = QHBoxLayout(actions_container_widget)


        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setIcon(QIcon(":/icons/refresh-cw.svg"))
        self.refresh_button.clicked.connect(self.load_invoices) # Connect to load_invoices
        actions_layout.addWidget(self.refresh_button)

        self.record_payment_button = QPushButton("Record Payment")
        self.record_payment_button.setObjectName("recordPaymentButton")
        self.record_payment_button.setIcon(QIcon(":/icons/credit-card.svg")) # Fallback icon
        self.record_payment_button.setEnabled(False)
        self.record_payment_button.clicked.connect(self.open_record_payment_dialog)
        actions_layout.addWidget(self.record_payment_button)

        self.view_details_button = QPushButton("View Details")
        self.view_details_button.setObjectName("viewDetailsButton")
        self.view_details_button.setIcon(QIcon(":/icons/eye.svg"))
        self.view_details_button.setEnabled(False)
        self.view_details_button.clicked.connect(self.open_invoice_details_dialog)
        actions_layout.addWidget(self.view_details_button)

        self.add_invoice_button = QPushButton("Add New Invoice")
        self.add_invoice_button.setObjectName("addInvoiceButton")
        self.add_invoice_button.setIcon(QIcon(":/icons/plus.svg"))
        self.add_invoice_button.clicked.connect(self.open_add_invoice_dialog)
        actions_layout.addWidget(self.add_invoice_button)

        actions_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        # actions_container_widget.setLayout(actions_layout) # Already set
        main_layout.addWidget(actions_container_widget)


        # --- Invoices Table ---
        self.invoices_table = QTableWidget()
        self.invoices_table.setObjectName("invoicesTable")
        self.invoices_table.setColumnCount(8) # Adjusted column count
        self.invoices_table.setHorizontalHeaderLabels([
            "Invoice #", "Client ID", "Client Name", "Issue Date",
            "Due Date", "Total Amount", "Currency", "Status"
        ])

        self.invoices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.invoices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.invoices_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.invoices_table.verticalHeader().setVisible(False)
        self.invoices_table.horizontalHeader().setStretchLastSection(True)
        self.invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) # Allow column resizing
        self.invoices_table.doubleClicked.connect(self.handle_table_double_click) # Connect double click

        # Adjust column widths (example values, can be fine-tuned)
        self.invoices_table.setColumnWidth(0, 120) # Invoice #
        self.invoices_table.setColumnWidth(1, 200) # Client ID (can be hidden if Name is good)
        self.invoices_table.setColumnWidth(2, 200) # Client Name
        self.invoices_table.setColumnWidth(3, 100) # Issue Date
        self.invoices_table.setColumnWidth(4, 100) # Due Date
        self.invoices_table.setColumnWidth(5, 120) # Total Amount
        self.invoices_table.setColumnWidth(6, 80)  # Currency
        self.invoices_table.setColumnWidth(7, 100) # Status


        self.invoices_table.itemSelectionChanged.connect(self.update_action_buttons_state)
        main_layout.addWidget(self.invoices_table)

        self.setLayout(main_layout)

        # Initial load of invoices
        self.load_invoices()

    def load_invoices(self):
        """Loads invoices from the database based on filters and populates the table."""
        self.invoices_table.setRowCount(0) # Clear existing rows

        filters = {}
        search_term = self.search_invoice_input.text().strip()
        if search_term:
            # This 'search_term' needs to be handled by invoices_crud.list_all_invoices
            # It might involve searching across multiple fields like invoice_number, client_id (or fetched client_name)
            filters['search_term'] = search_term

        selected_status_text = self.status_filter_combo.currentText()
        if selected_status_text != "All":
            filters['payment_status'] = selected_status_text.lower()

        if self.issue_date_from_edit.date() != self.default_issue_date_from:
            filters['issue_date_start'] = self.issue_date_from_edit.date().toString("yyyy-MM-dd")

        if self.issue_date_to_edit.date() != self.default_issue_date_to:
            filters['issue_date_end'] = self.issue_date_to_edit.date().toString("yyyy-MM-dd")

        try:
            # print(f"Loading invoices with filters: {filters}") # Debug
            invoice_list = invoices_crud.list_all_invoices(filters=filters, sort_by="issue_date_desc")
        except Exception as e:
            print(f"Error loading invoices: {e}") # Proper error handling (e.g., QMessageBox) should be added
            invoice_list = []

        self.invoices_table.setRowCount(len(invoice_list))

        status_color_map = {
            "paid": QColor("#d4edda"),      # Light Green
            "unpaid": QColor("#f8f9fa"),    # Light Grey/White (or white)
            "overdue": QColor("#f8d7da"),   # Light Red
            "partially paid": QColor("#fff3cd") # Light Yellow
        }

        for row, invoice_data in enumerate(invoice_list):
            client_name = "N/A"
            if invoice_data.get('client_id'):
                try:
                    client = clients_crud.get_client_by_id(invoice_data['client_id'])
                    if client:
                        client_name = client.get('client_name', 'N/A')
                except Exception as e:
                    print(f"Error fetching client name for client_id {invoice_data['client_id']}: {e}")


            # Ensure all items are created before trying to set data or background
            # Col 0: Invoice #
            item_invoice_no = QTableWidgetItem(str(invoice_data.get('invoice_number', '')))
            item_invoice_no.setData(Qt.UserRole, invoice_data.get('invoice_id')) # Store full ID
            self.invoices_table.setItem(row, 0, item_invoice_no)

            # Col 1: Client ID (can be hidden later if desired)
            self.invoices_table.setItem(row, 1, QTableWidgetItem(str(invoice_data.get('client_id', ''))))
            # Col 2: Client Name
            self.invoices_table.setItem(row, 2, QTableWidgetItem(client_name))
            # Col 3: Issue Date
            self.invoices_table.setItem(row, 3, QTableWidgetItem(str(invoice_data.get('issue_date', ''))))
            # Col 4: Due Date
            self.invoices_table.setItem(row, 4, QTableWidgetItem(str(invoice_data.get('due_date', ''))))
            # Col 5: Total Amount (format as currency if possible)
            total_amount_str = "{:,.2f}".format(invoice_data.get('total_amount', 0.0))
            item_total_amount = QTableWidgetItem(total_amount_str)
            item_total_amount.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.invoices_table.setItem(row, 5, item_total_amount)
            # Col 6: Currency
            self.invoices_table.setItem(row, 6, QTableWidgetItem(str(invoice_data.get('currency', ''))))
            # Col 7: Status
            status_text = invoice_data.get('payment_status', '').title() # title() for "Paid", "Unpaid"
            self.invoices_table.setItem(row, 7, QTableWidgetItem(status_text))

            # Apply background color based on status
            row_color = status_color_map.get(invoice_data.get('payment_status', '').lower(), QColor("white"))
            for col in range(self.invoices_table.columnCount()):
                table_item = self.invoices_table.item(row, col)
                if table_item: # Should exist now
                    table_item.setBackground(row_color)

        # self.invoices_table.resizeColumnsToContents() # Optional: might be slow with many rows
        self.update_action_buttons_state()


    def apply_filters(self):
        """Placeholder to apply filters and reload invoices."""
        # This method is now effectively replaced by load_invoices directly
        # unless more complex pre-processing of filters is needed.
        # For now, load_invoices is called by the button.
        print("apply_filters called, redirecting to load_invoices")
        self.load_invoices()


    def refresh_invoices(self):
        """Placeholder to refresh the invoice list."""
        # This method is now effectively replaced by load_invoices directly.
        print("refresh_invoices called, redirecting to load_invoices")
        self.load_invoices()


    def open_record_payment_dialog(self):
        """Opens the RecordPaymentDialog for the selected invoice."""
        selected_row_index = self.invoices_table.currentRow()
        if selected_row_index < 0: # No row selected
            QMessageBox.warning(self, "No Selection", "Please select an invoice to record a payment.")
            return

        invoice_id_item = self.invoices_table.item(selected_row_index, 0) # Invoice # / ID item
        invoice_id = invoice_id_item.data(Qt.UserRole) if invoice_id_item else None

        if not invoice_id:
            QMessageBox.critical(self, "Error", "Could not retrieve invoice ID for the selected row.")
            return

        dialog = RecordPaymentDialog(invoice_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_invoices() # Refresh table on successful payment recording

    def open_invoice_details_dialog(self):
        """Opens the InvoiceDetailsDialog for the selected invoice."""
        selected_row_index = self.invoices_table.currentRow()
        if selected_row_index < 0: # No row selected
            QMessageBox.warning(self, "No Selection", "Please select an invoice to view its details.")
            return

        invoice_id_item = self.invoices_table.item(selected_row_index, 0)
        invoice_id = invoice_id_item.data(Qt.UserRole) if invoice_id_item else None

        if not invoice_id:
            QMessageBox.critical(self, "Error", "Could not retrieve invoice ID for the selected row.")
            return

        dialog = InvoiceDetailsDialog(invoice_id, self)
        dialog.exec_() # Details dialog is read-only, no need to refresh table after

    def open_add_invoice_dialog(self):
        """Opens the ManualInvoiceDialog to add a new invoice."""
        dialog = ManualInvoiceDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_invoices() # Refresh table on successful new invoice creation

    def handle_table_double_click(self, model_index: QModelIndex):
        """Handles double-click on a table row to open invoice details."""
        if not model_index.isValid():
            return

        # The selection model might not update immediately on double click,
        # so explicitly select the row of the double-clicked index.
        self.invoices_table.selectRow(model_index.row())
        self.open_invoice_details_dialog()


    def update_action_buttons_state(self):
        """Enable/disable action buttons based on table selection."""
        has_selection = bool(self.invoices_table.selectedItems()) # Checks if any cell is selected
        # More precise: check if a full row is selected or if currentRow is valid
        # current_row_valid = self.invoices_table.currentRow() >= 0

        self.record_payment_button.setEnabled(has_selection)
        self.view_details_button.setEnabled(has_selection)

        if has_selection:
            current_row = self.invoices_table.currentRow()
            if current_row >=0:
                status_item = self.invoices_table.item(current_row, 7) # Status column
                if status_item and status_item.text().lower() == "paid":
                    self.record_payment_button.setEnabled(False) # Example: disable if already paid
        # print("update_action_buttons_state called") # Reduce noisy prints


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # This section might be needed if your widget's methods directly or indirectly
    # call database functions that rely on db_config.py and an initialized schema.
    # For pure UI layout testing without calling `load_invoices` that hits DB, it might not be strictly necessary.
    # However, good practice to set it up if there's any chance of DB interaction.
    try:
        # Adjust path to import db_config and init_schema from the project root
        APP_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if APP_ROOT_DIR not in sys.path:
            sys.path.insert(0, APP_ROOT_DIR)

        from db import db_config # To set DATABASE_PATH if needed
        from db.init_schema import initialize_database

        # Example: use a specific test DB or ensure default is okay for a read-only test
        # db_config.DATABASE_PATH = "test_gui_invoices.db" # Or ":memory:" if no persistence needed
        # initialize_database() # Create schema if it doesn't exist
        print("Database initialized (or verified) for GUI test.")

    except ImportError as e:
        print(f"Error importing database modules for GUI test run: {e}")
        print("Proceeding with UI layout test only. Database interactions might fail.")
    except Exception as e:
        print(f"Error initializing database for GUI test run: {e}")
        print("Proceeding with UI layout test only. Database interactions might fail.")


    widget = InvoiceManagementWidget()
    widget.setWindowTitle("Invoice Management Test")
    widget.setGeometry(100, 100, 1200, 700) # Increased size for better visibility
    widget.show()
    sys.exit(app.exec_())
```
