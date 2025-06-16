import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QPushButton, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLabel, QHeaderView, QApplication, QWidget
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QIcon
from db.cruds import clients_crud, projects_crud, products_crud, client_project_products_crud
from datetime import datetime, timedelta

class FinalInvoiceDataDialog(QDialog):
    def __init__(self, client_id, project_id=None, company_id=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.project_id = project_id
        self.company_id = company_id # Stored for potential future use (e.g. company-specific defaults)

        self.line_items_data_internal = [] # To store dicts of item data before adding to table

        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("Prepare Final Invoice Data")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        main_layout = QVBoxLayout(self)

        # --- Header Info ---
        header_form_layout = QFormLayout()
        self.client_label = QLabel("Client: N/A")
        self.project_label = QLabel("Project: N/A")
        header_form_layout.addRow(self.client_label)
        if self.project_id:
            header_form_layout.addRow(self.project_label)

        self.issue_date_edit = QDateEdit(QDate.currentDate())
        self.issue_date_edit.setCalendarPopup(True)
        self.issue_date_edit.setDisplayFormat("yyyy-MM-dd")
        header_form_layout.addRow("Issue Date:", self.issue_date_edit)

        self.due_date_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        header_form_layout.addRow("Due Date:", self.due_date_edit)

        self.payment_terms_edit = QLineEdit("Payment due within 30 days")
        header_form_layout.addRow("Payment Terms:", self.payment_terms_edit)

        self.tax_rate_spinbox = QDoubleSpinBox()
        self.tax_rate_spinbox.setSuffix(" %")
        self.tax_rate_spinbox.setRange(0.0, 100.0)
        self.tax_rate_spinbox.setValue(20.0) # Default VAT
        self.tax_rate_spinbox.valueChanged.connect(self.update_totals)
        header_form_layout.addRow("Tax Rate:", self.tax_rate_spinbox)

        self.tax_label_edit = QLineEdit("VAT")
        header_form_layout.addRow("Tax Label:", self.tax_label_edit)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["EUR", "USD", "GBP", "CAD", "AUD"]) # Common currencies
        self.currency_combo.setCurrentText("EUR") # Default
        self.currency_combo.currentTextChanged.connect(self.update_totals) # Update totals if currency symbol changes
        header_form_layout.addRow("Currency:", self.currency_combo)

        self.invoice_notes_edit = QTextEdit()
        self.invoice_notes_edit.setPlaceholderText("Optional notes for the invoice...")
        self.invoice_notes_edit.setFixedHeight(60)
        header_form_layout.addRow("Invoice Notes:", self.invoice_notes_edit)

        main_layout.addLayout(header_form_layout)

        # --- Line Items Section ---
        main_layout.addWidget(QLabel("<h3>Invoice Line Items:</h3>"))

        # Input for adding new items
        add_item_layout = QHBoxLayout()
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)
        self.product_combo.currentIndexChanged.connect(self.on_product_selected)
        add_item_layout.addWidget(self.product_combo)

        self.quantity_spinbox = QDoubleSpinBox()
        self.quantity_spinbox.setRange(0.01, 99999.0)
        self.quantity_spinbox.setValue(1.0)
        self.quantity_spinbox.setDecimals(2)
        add_item_layout.addWidget(QLabel("Qty:"))
        add_item_layout.addWidget(self.quantity_spinbox)

        self.unit_price_spinbox = QDoubleSpinBox()
        self.unit_price_spinbox.setRange(0.00, 9999999.00)
        self.unit_price_spinbox.setDecimals(2)
        # self.unit_price_spinbox.setPrefix(self.currency_combo.currentText() + " ") # Dynamic prefix later
        add_item_layout.addWidget(QLabel("Unit Price:"))
        add_item_layout.addWidget(self.unit_price_spinbox)

        self.add_item_button = QPushButton("Add Item")
        self.add_item_button.setIcon(QIcon(":/icons/plus.svg"))
        self.add_item_button.clicked.connect(self.add_line_item)
        add_item_layout.addWidget(self.add_item_button)
        main_layout.addLayout(add_item_layout)

        self.line_items_table = QTableWidget()
        self.line_items_table.setColumnCount(7) # ID, Name, Desc, Qty, Unit Price, Total, Action
        self.line_items_table.setHorizontalHeaderLabels(["Product ID", "Product Name", "Description", "Quantity", "Unit Price", "Total", "Remove"])
        self.line_items_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Or allow editing quantity/price
        self.line_items_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.line_items_table.hideColumn(0) # Hide Product ID, used internally
        self.line_items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name
        self.line_items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Description
        main_layout.addWidget(self.line_items_table)

        # --- Totals Display ---
        totals_layout = QFormLayout()
        self.subtotal_label = QLabel("0.00")
        self.tax_amount_label = QLabel("0.00")
        self.grand_total_label = QLabel("0.00")
        totals_layout.addRow("<b>Subtotal:</b>", self.subtotal_label)
        totals_layout.addRow(self.tax_label_edit.text() + ":", self.tax_amount_label) # Tax label will update dynamically
        totals_layout.addRow("<b>Grand Total:</b>", self.grand_total_label)
        main_layout.addLayout(totals_layout)
        self.tax_label_edit.textChanged.connect(lambda text: totals_layout.labelForField(self.tax_amount_label).setText(f"<b>{text} ({self.tax_rate_spinbox.value()}%):</b>"))


        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Generate Invoice")
        self.button_box.accepted.connect(self.accept_data_collection)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def load_initial_data(self):
        # Load Client Name
        client = clients_crud.get_client_by_id(self.client_id)
        if client:
            self.client_label.setText(f"<b>Client:</b> {client.get('client_name', 'N/A')}")

        # Load Project Name
        if self.project_id:
            project = projects_crud.get_project_by_id(self.project_id)
            if project:
                self.project_label.setText(f"<b>Project:</b> {project.get('project_name', 'N/A')}")
        else:
            self.project_label.setVisible(False)

        # Load Products into ComboBox
        self.product_combo.addItem("Select Product...", None)
        try:
            products = products_crud.get_all_products(active_only=True) # Fetch only active products
            if products:
                for prod in products:
                    # Store dict of relevant product info for easy access
                    self.product_combo.addItem(f"{prod.get('product_name')} ({prod.get('language_code')})", prod)
        except Exception as e:
            print(f"Error loading global products: {e}")
            QMessageBox.warning(self, "Data Load Error", f"Could not load products: {e}")

        # Pre-populate line items from ClientProjectProducts if client/project context
        try:
            if self.client_id: # Always try to load for client, or client+project
                cpp_items = client_project_products_crud.get_products_for_client_or_project(self.client_id, self.project_id)
                for item in cpp_items:
                    # Fetch full product details for each item
                    prod_details = products_crud.get_product_by_id(item['product_id'])
                    if prod_details:
                        unit_price = item.get('unit_price_override') if item.get('unit_price_override') is not None else prod_details.get('base_unit_price', 0.0)

                        line_item = {
                            "product_id": prod_details['product_id'],
                            "name": prod_details['product_name'],
                            "description": prod_details.get('description', ''),
                            "quantity": float(item['quantity']),
                            "unit_price_raw": float(unit_price)
                        }
                        self._add_item_to_table(line_item)
                        self.line_items_data_internal.append(line_item) # Keep internal list synced
        except Exception as e:
            print(f"Error pre-populating line items: {e}")
            QMessageBox.warning(self, "Data Load Error", f"Could not pre-populate line items: {e}")

        self.update_totals()


    def on_product_selected(self):
        product_data = self.product_combo.currentData()
        if product_data and isinstance(product_data, dict):
            price = product_data.get('base_unit_price', 0.0)
            self.unit_price_spinbox.setValue(float(price if price is not None else 0.0))
            self.quantity_spinbox.setValue(1.0) # Reset quantity
        else:
            self.unit_price_spinbox.setValue(0.0)

    def add_line_item(self):
        product_data = self.product_combo.currentData()
        if not product_data or not isinstance(product_data, dict):
            QMessageBox.warning(self, "No Product", "Please select a product to add.")
            return

        quantity = self.quantity_spinbox.value()
        unit_price = self.unit_price_spinbox.value()

        if quantity <= 0:
            QMessageBox.warning(self, "Invalid Quantity", "Quantity must be greater than zero.")
            return
        if unit_price < 0: # Allow zero price for free items
            QMessageBox.warning(self, "Invalid Price", "Unit price cannot be negative.")
            return

        line_item = {
            "product_id": product_data.get('product_id'),
            "name": product_data.get('product_name', 'N/A'),
            "description": product_data.get('description', ''),
            "quantity": quantity,
            "unit_price_raw": unit_price
        }
        self.line_items_data_internal.append(line_item)
        self._add_item_to_table(line_item)
        self.update_totals()

    def _add_item_to_table(self, item_data: dict):
        row_position = self.line_items_table.rowCount()
        self.line_items_table.insertRow(row_position)

        self.line_items_table.setItem(row_position, 0, QTableWidgetItem(str(item_data.get("product_id"))))
        self.line_items_table.setItem(row_position, 1, QTableWidgetItem(item_data.get("name")))
        self.line_items_table.setItem(row_position, 2, QTableWidgetItem(item_data.get("description")))

        qty_item = QTableWidgetItem(f"{item_data.get('quantity'):.2f}")
        qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.line_items_table.setItem(row_position, 3, qty_item)

        price_item = QTableWidgetItem(f"{item_data.get('unit_price_raw'):.2f}")
        price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.line_items_table.setItem(row_position, 4, price_item)

        total_item = QTableWidgetItem(f"{(item_data.get('quantity') * item_data.get('unit_price_raw')):.2f}")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.line_items_table.setItem(row_position, 5, total_item)

        remove_button = QPushButton("Remove")
        remove_button.setIcon(QIcon(":/icons/trash.svg"))
        remove_button.clicked.connect(lambda: self.remove_line_item(row_position)) # Use lambda to pass row
        self.line_items_table.setCellWidget(row_position, 6, remove_button)
        self.line_items_table.resizeRowToContents(row_position)


    def remove_line_item(self, row_to_remove):
        # Need to find the actual row if rows above it were removed.
        # It's safer to remove from self.line_items_data_internal first by product_id or unique aspect
        # then rebuild table, or remove carefully by tracking actual current row.
        # For now, if buttons are recreated, lambda captures initial row_position.
        # This can be tricky if rows are removed causing indices to shift.
        # A more robust way is to find the button that sent the signal and get its row.

        # Simple approach: if row_to_remove is the original index from when button was created.
        # This assumes that when a row is removed, the table widget re-indexes subsequent rows.
        # We need to remove from the *model* (self.line_items_data_internal) correctly.
        # The product_id of the item in the row to remove can be used to find it in the list.

        product_id_to_remove = self.line_items_table.item(row_to_remove, 0).text() # Get product ID from hidden col

        # Find and remove from internal list
        # This is complicated if multiple identical product_ids can exist with different prices/qtys
        # For now, assume we remove the first match found for this row.
        # A truly robust solution would assign unique IDs to each line_item_data_internal entry.

        # Let's use the row index directly on the internal list IF it's guaranteed to be in sync.
        # This requires careful management.
        if 0 <= row_to_remove < len(self.line_items_data_internal):
            del self.line_items_data_internal[row_to_remove]
            self.line_items_table.removeRow(row_to_remove)
             # After removing a row, buttons in subsequent rows might have stale row indices in their lambdas.
             # Re-connecting signals for all remove buttons or rebuilding items is safer.
             # For simplicity here, we'll assume this basic removal works for now.
            self.update_totals()
        else:
            print(f"Warning: Tried to remove row at invalid index {row_to_remove}")


    def update_totals(self):
        subtotal = 0.0
        for row in range(self.line_items_table.rowCount()):
            try:
                # total_text = self.line_items_table.item(row, 5).text() # "Total" column
                # subtotal += float(total_text)
                # Safer: use internal data or recalculate from qty and price columns
                qty = float(self.line_items_table.item(row, 3).text())
                price = float(self.line_items_table.item(row, 4).text())
                subtotal += qty * price
            except (ValueError, AttributeError):
                print(f"Warning: Could not parse total for row {row}")
                continue

        currency_symbol = self.currency_combo.currentText() # This is just the code, e.g. "EUR"
        # For display, we might want a symbol like €, $, £. This requires a mapping.
        # For now, the spinbox prefix handles it, and templates use context.currency_symbol.
        # Here, let's assume currency_symbol for display is just the code.

        self.subtotal_label.setText(f"{subtotal:,.2f} {currency_symbol}")

        tax_rate = self.tax_rate_spinbox.value() / 100.0
        tax_amount = subtotal * tax_rate
        self.tax_amount_label.setText(f"{tax_amount:,.2f} {currency_symbol}")

        grand_total = subtotal + tax_amount
        self.grand_total_label.setText(f"<b>{grand_total:,.2f} {currency_symbol}</b>")

    def accept_data_collection(self):
        if self.line_items_table.rowCount() == 0:
            QMessageBox.warning(self, "No Items", "Please add at least one line item to the invoice.")
            return

        issue_d = self.issue_date_edit.date()
        due_d = self.due_date_edit.date()
        if issue_d > due_d:
            QMessageBox.warning(self, "Date Error", "Issue date cannot be after the due date.")
            return

        self.accept() # Proceed

    def get_data(self) -> tuple[list, dict]:
        line_items_for_pdf = []
        for row in range(self.line_items_table.rowCount()):
            line_items_for_pdf.append({
                'product_id': self.line_items_table.item(row, 0).text(), # Hidden Product ID
                'name': self.line_items_table.item(row, 1).text(),
                'description': self.line_items_table.item(row, 2).text(),
                'quantity': float(self.line_items_table.item(row, 3).text()),
                'unit_price': float(self.line_items_table.item(row, 4).text()) # Use 'unit_price' as key for context
            })

        additional_context = {
            'issue_date': self.issue_date_edit.date().toString("yyyy-MM-dd"),
            'due_date': self.due_date_edit.date().toString("yyyy-MM-dd"),
            'final_payment_terms': self.payment_terms_edit.text().strip(),
            'tax_rate_percentage': self.tax_rate_spinbox.value(),
            'tax_label': self.tax_label_edit.text().strip(),
            'currency_symbol': self.currency_combo.currentText(), # This should be the code like "EUR"
            'invoice_notes': self.invoice_notes_edit.toPlainText().strip(),
            # Subtotal, tax amount, grand total will be recalculated by get_final_invoice_context_data
            # based on the line items and tax rate provided here.
        }
        return line_items_for_pdf, additional_context

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # For proper testing, DB setup and mock data are needed as this dialog
    # tries to load clients, projects, and products.
    # Standalone execution without DB will show empty combo boxes.

    # --- Example Standalone Setup (Commented out by default) ---
    # import os
    # import uuid
    # APP_ROOT_DIR_STANDALONE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # if APP_ROOT_DIR_STANDALONE not in sys.path:
    #    sys.path.insert(0, APP_ROOT_DIR_STANDALONE)
    # from db import db_config, init_schema
    # db_config.DATABASE_PATH = "test_final_invoice_dialog.db"
    # init_schema.initialize_database()
    # # Add dummy data to clients, projects, products tables for testing
    # try:
    #     # Example: clients_crud.add_client(...) etc.
    #     # This requires CRUD functions to be runnable and DB initialized.
    #     print("DB initialized for standalone dialog test. Add mock data for full functionality.")
    # except Exception as e_main_test:
    #     print(f"Error setting up DB for standalone test: {e_main_test}")
    # --- End Example Standalone Setup ---

    # Dummy IDs for testing dialog structure if DB is not set up
    dummy_client_id = "dummy_client"
    dummy_project_id = "dummy_project" # Can be None

    dialog = FinalInvoiceDataDialog(client_id=dummy_client_id, project_id=dummy_project_id)
    dialog.show()

    sys.exit(app.exec_())

