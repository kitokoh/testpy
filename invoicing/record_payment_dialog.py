import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QPushButton, QDialogButtonBox, QMessageBox,
    QApplication, QWidget # Added QApplication, QWidget for standalone test
)
from PyQt5.QtCore import QDate, Qt
from datetime import datetime

# Assuming APP_ROOT_DIR setup is done in the main application for db access
# For now, assume db.cruds are importable.
from db.cruds import invoices_crud
from db.cruds import clients_crud # For fetching client name

class RecordPaymentDialog(QDialog):
    def __init__(self, invoice_id, parent=None):
        super().__init__(parent)
        self.setObjectName("recordPaymentDialog")
        self.invoice_id = invoice_id
        self.invoice_data = None
        self.client_data = None

        try:
            self.invoice_data = invoices_crud.get_invoice_by_id(self.invoice_id)
            if self.invoice_data and self.invoice_data.get('client_id'):
                self.client_data = clients_crud.get_client_by_id(self.invoice_data['client_id'])
        except Exception as e:
            print(f"Error fetching initial data for RecordPaymentDialog: {e}")
            # Allow dialog to open to show an error, or could raise here / return status

        if not self.invoice_data:
            # This case should ideally be handled by the caller, but as a fallback:
            QMessageBox.critical(self, "Error", f"Invoice with ID '{self.invoice_id}' not found or could not be loaded.")
            # self.reject() # or self.close(), but this might happen before show()
            # Defer actual UI setup if data is missing
            self._valid_invoice = False
        else:
            self._valid_invoice = True

        self.init_ui()
        if self._valid_invoice:
            self.populate_fields()
        else:
            # If invoice data is invalid, ensure dialog shows an error state
            self.setWindowTitle("Error Loading Invoice")
            error_label = QLabel("<font color='red'>Could not load invoice details. Please close this dialog.</font>")
            layout = self.layout() # Get the main layout
            if layout:
                # Clear existing widgets if any were added before error check
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                layout.addWidget(error_label)
            # Disable buttons if they exist
            if hasattr(self, 'button_box'):
                 save_button = self.button_box.button(QDialogButtonBox.Save)
                 if save_button: save_button.setEnabled(False)


    def init_ui(self):
        if not self._valid_invoice and hasattr(self, 'layout') and self.layout() is not None :
             # If constructor decided it's invalid and UI is already partially built
             return

        self.setWindowTitle(f"Record Payment - Invoice: {self.invoice_data.get('invoice_number', self.invoice_id[:8]) if self.invoice_data else 'N/A'}")
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)

        # Read-only context labels
        self.invoice_number_label = QLabel()
        self.client_name_label = QLabel()
        self.total_amount_label = QLabel()
        main_layout.addWidget(self.invoice_number_label)
        main_layout.addWidget(self.client_name_label)
        main_layout.addWidget(self.total_amount_label)

        # Spacer
        main_layout.addSpacing(15)

        form_container_widget = QWidget()
        form_container_widget.setObjectName("paymentFormContainer")
        self.form_layout = QFormLayout(form_container_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.payment_date_edit = QDateEdit(QDate.currentDate())
        self.payment_date_edit.setCalendarPopup(True)
        self.payment_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.form_layout.addRow("Payment Date:", self.payment_date_edit)

        self.payment_method_edit = QLineEdit()
        self.form_layout.addRow("Payment Method:", self.payment_method_edit)

        self.transaction_id_edit = QLineEdit()
        self.form_layout.addRow("Transaction ID:", self.transaction_id_edit)

        self.payment_status_combo = QComboBox()
        # Common statuses when recording a payment. "unpaid" could be to revert.
        self.payment_status_combo.addItems(["paid", "partially paid", "unpaid"])
        self.form_layout.addRow("Payment Status:", self.payment_status_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(80) # Reasonable height for notes
        self.form_layout.addRow("Notes:", self.notes_edit)

        # form_container_widget.setLayout(self.form_layout) # Already set in constructor
        main_layout.addWidget(form_container_widget)

        self.payment_button_box = QDialogButtonBox()
        self.payment_button_box.setObjectName("paymentButtonBox")
        self.payment_button_box.addButton("Save Payment", QDialogButtonBox.AcceptRole)
        self.payment_button_box.addButton(QDialogButtonBox.Cancel)

        self.payment_button_box.accepted.connect(self.accept_payment)
        self.payment_button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.payment_button_box)

        self.setLayout(main_layout)

    def populate_fields(self):
        if not self.invoice_data: # Should be guarded by _valid_invoice
            return

        self.invoice_number_label.setText(f"<b>Invoice #:</b> {self.invoice_data.get('invoice_number', 'N/A')}")

        client_name_str = "N/A"
        if self.client_data:
            client_name_str = self.client_data.get('client_name', 'N/A')
        elif self.invoice_data.get('client_id'):
             client_name_str = f"Client ID: {self.invoice_data.get('client_id')} (Name not found)"
        self.client_name_label.setText(f"<b>Client:</b> {client_name_str}")

        total_amount = self.invoice_data.get('total_amount', 0.0)
        currency = self.invoice_data.get('currency', '')
        self.total_amount_label.setText(f"<b>Total Amount:</b> {total_amount:,.2f} {currency}")

        if self.invoice_data.get('payment_date'):
            try:
                payment_dt = QDate.fromString(self.invoice_data.get('payment_date'), "yyyy-MM-dd")
                if payment_dt.isValid():
                    self.payment_date_edit.setDate(payment_dt)
            except Exception as e:
                print(f"Error parsing payment_date from DB: {e}")
                # Keep default (today) if parsing fails

        self.payment_method_edit.setText(self.invoice_data.get('payment_method', ''))
        self.transaction_id_edit.setText(self.invoice_data.get('transaction_id', ''))

        current_status = self.invoice_data.get('payment_status', 'unpaid').lower()
        if self.payment_status_combo.findText(current_status, Qt.MatchFixedString) >= 0:
            self.payment_status_combo.setCurrentText(current_status)
        elif current_status == "overdue": # If current status is "overdue", default to "paid" or "unpaid"
            self.payment_status_combo.setCurrentText("paid")


        self.notes_edit.setPlainText(self.invoice_data.get('notes', ''))

    def accept_payment(self):
        if not self._valid_invoice:
            self.reject() # Should not happen if buttons are disabled
            return

        update_data = {
            'payment_date': self.payment_date_edit.date().toString("yyyy-MM-dd"),
            'payment_method': self.payment_method_edit.text().strip(),
            'transaction_id': self.transaction_id_edit.text().strip(),
            'payment_status': self.payment_status_combo.currentText().lower(),
            'notes': self.notes_edit.toPlainText().strip()
        }

        try:
            success = invoices_crud.update_invoice(self.invoice_id, update_data)
            if success:
                QMessageBox.information(self, "Success", "Payment details updated successfully.")
                self.accept() # Closes the dialog with QDialog.Accepted
            else:
                QMessageBox.warning(self, "Update Failed", "Failed to update payment details in the database. No rows were changed.")
        except Exception as e:
            print(f"Error updating payment details: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while updating payment details: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # This dialog is best tested by launching it from InvoiceManagementWidget
    # after an invoice is selected. Standalone testing requires DB setup and a valid invoice_id.

    # --- Example of how to set up for standalone test (requires actual DB setup): ---
    # import os
    # APP_ROOT_DIR_STANDALONE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # if APP_ROOT_DIR_STANDALONE not in sys.path:
    #     sys.path.insert(0, APP_ROOT_DIR_STANDALONE)
    # from db import db_config, init_schema
    # from db.cruds import invoices_crud, clients_crud
    #
    # db_config.DATABASE_PATH = "test_record_payment.db" # Use a test DB
    # init_schema.initialize_database()
    #
    # # 1. Add a dummy client
    # client_id_for_test = str(uuid.uuid4())
    # try:
    #     # Assuming clients_crud.add_client takes a dict or specific args
    #     # This is a placeholder, actual add_client might differ
    #     # clients_crud.add_client({'client_id': client_id_for_test, 'client_name': 'Test Client for Payment Dialog', ...})
    #     conn = sqlite3.connect(db_config.DATABASE_PATH)
    #     conn.execute("INSERT INTO Clients (client_id, client_name, project_identifier) VALUES (?, ?, ?)",
    #                  (client_id_for_test, "Test Client Payment", "TCP"))
    #     conn.commit()
    #     conn.close()
    # except Exception as e_client:
    #     print(f"Error adding test client: {e_client}")
    #     client_id_for_test = None # Ensure it's None if creation fails
    #
    # test_invoice_id_for_dialog = None
    # if client_id_for_test:
    #     test_invoice_data = {
    #         'client_id': client_id_for_test,
    #         'invoice_number': f"PAY-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    #         'issue_date': "2023-03-01",
    #         'due_date': "2023-04-01",
    #         'total_amount': 500.00,
    #         'currency': 'USD',
    #         'payment_status': 'unpaid'
    #     }
    #     try:
    #         test_invoice_id_for_dialog = invoices_crud.add_invoice(test_invoice_data)
    #     except Exception as e_inv:
    #         print(f"Error adding test invoice: {e_inv}")
    #
    # if test_invoice_id_for_dialog:
    #     dialog = RecordPaymentDialog(invoice_id=test_invoice_id_for_dialog)
    #     dialog.exec_() # Use exec_() for modal dialog
    # else:
    #     print("Failed to create a test invoice for the dialog. Displaying placeholder info.")
    #     main_window = QWidget()
    #     layout = QVBoxLayout(main_window)
    #     label = QLabel("To test RecordPaymentDialog properly, ensure DB is set up and a valid invoice can be created.\n"
    #                    "Currently, a test invoice could not be prepared.")
    #     layout.addWidget(label)
    #     main_window.setWindowTitle("RecordPaymentDialog Test Placeholder")
    #     main_window.show()
    # --- End Standalone Test Example ---

    # Default placeholder for when not running full standalone test setup
    main_window_placeholder = QWidget()
    layout_placeholder = QVBoxLayout(main_window_placeholder)
    label_placeholder = QLabel("To test RecordPaymentDialog, run it via InvoiceManagementWidget with a selected invoice.\n"
                               "Ensure the database is initialized and contains invoices.")
    layout_placeholder.addWidget(label_placeholder)
    main_window_placeholder.setWindowTitle("RecordPaymentDialog Test Information")
    main_window_placeholder.show()

    sys.exit(app.exec_())
```
