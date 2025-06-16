import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QPushButton, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QApplication, QWidget # Added QApplication, QWidget for standalone
)
from PyQt5.QtCore import QDate, Qt
from datetime import datetime # Not directly used, but good for potential date logic

# Assuming APP_ROOT_DIR setup is done in the main application for db access
# For now, assume db.cruds are importable.
from db.cruds import invoices_crud, clients_crud
from db.cruds import projects_crud # Assumed to exist with get_projects_by_client or similar

class ManualInvoiceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("manualInvoiceDialog")
        self.init_ui()
        self.load_combo_data()

    def init_ui(self):
        self.setWindowTitle("Create New Manual Invoice")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        form_container_widget = QWidget()
        form_container_widget.setObjectName("manualInvoiceFormContainer")
        self.form_layout = QFormLayout(form_container_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Client ComboBox
        self.client_combo = QComboBox()
        self.client_combo.currentIndexChanged.connect(self.on_client_selected)
        self.form_layout.addRow("Client:*", self.client_combo)

        # Project ComboBox
        self.project_combo = QComboBox()
        self.project_combo.setEnabled(False) # Initially disabled
        self.form_layout.addRow("Project (Optional):", self.project_combo)

        # Invoice Number
        self.invoice_number_edit = QLineEdit()
        self.invoice_number_edit.setPlaceholderText("e.g., INV-2024-001")
        self.form_layout.addRow("Invoice Number:*", self.invoice_number_edit)

        # Issue Date
        self.issue_date_edit = QDateEdit(QDate.currentDate())
        self.issue_date_edit.setCalendarPopup(True)
        self.issue_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.form_layout.addRow("Issue Date:", self.issue_date_edit)

        # Due Date
        self.due_date_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.form_layout.addRow("Due Date:", self.due_date_edit)

        # Total Amount
        self.total_amount_spinbox = QDoubleSpinBox()
        self.total_amount_spinbox.setRange(0.00, 10000000.00) # Example range
        self.total_amount_spinbox.setDecimals(2)
        self.total_amount_spinbox.setPrefix("$ ") # Example prefix, can be dynamic
        self.form_layout.addRow("Total Amount:*", self.total_amount_spinbox)

        # Currency
        self.currency_edit = QLineEdit("USD") # Default currency
        self.form_layout.addRow("Currency:", self.currency_edit)

        # Payment Status
        self.payment_status_combo = QComboBox()
        self.payment_status_combo.addItems(["unpaid", "paid", "partially paid"])
        self.payment_status_combo.setCurrentText("unpaid")
        self.form_layout.addRow("Initial Status:", self.payment_status_combo)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(80)
        self.form_layout.addRow("Notes:", self.notes_edit)

        # form_container_widget.setLayout(self.form_layout) # Already set in constructor
        main_layout.addWidget(form_container_widget)

        self.manual_invoice_button_box = QDialogButtonBox()
        self.manual_invoice_button_box.setObjectName("manualInvoiceButtonBox")
        self.manual_invoice_button_box.addButton("Save Invoice", QDialogButtonBox.AcceptRole)
        self.manual_invoice_button_box.addButton(QDialogButtonBox.Cancel)

        self.manual_invoice_button_box.accepted.connect(self.accept_invoice_creation)
        self.manual_invoice_button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.manual_invoice_button_box)

        self.setLayout(main_layout)

    def load_combo_data(self):
        self.client_combo.clear()
        self.client_combo.addItem("Select Client...", None) # UserData is None
        try:
            clients = clients_crud.get_all_clients() # Assumes this function exists
            if clients:
                for client in clients:
                    self.client_combo.addItem(client.get('client_name', 'Unknown Client'), client.get('client_id'))
            else:
                print("No clients found or error in clients_crud.get_all_clients")
        except AttributeError:
             print("Warning: clients_crud.get_all_clients not available.")
        except Exception as e:
            print(f"Error loading clients: {e}")

        self.on_client_selected() # To set initial state of project_combo

    def on_client_selected(self):
        self.project_combo.clear()
        self.project_combo.addItem("Optional - Select Project...", None) # UserData is None

        client_id = self.client_combo.currentData()
        if client_id:
            try:
                # Assumes projects_crud.get_projects_by_client(client_id) exists
                projects = projects_crud.get_projects_by_client_id(client_id)
                if projects:
                    for project in projects:
                        self.project_combo.addItem(project.get('project_name', 'Unknown Project'), project.get('project_id'))
                    self.project_combo.setEnabled(True)
                else:
                    # No projects for this client, or error
                    self.project_combo.setEnabled(False)
            except AttributeError: # If projects_crud or method doesn't exist
                print(f"Warning: projects_crud.get_projects_by_client_id not available.")
                self.project_combo.setEnabled(False)
            except Exception as e:
                print(f"Error loading projects for client ID {client_id}: {e}")
                self.project_combo.setEnabled(False)
        else:
            self.project_combo.setEnabled(False)

    def accept_invoice_creation(self):
        # Validation
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Validation Error", "Please select a client.")
            return

        invoice_number = self.invoice_number_edit.text().strip()
        if not invoice_number:
            QMessageBox.warning(self, "Validation Error", "Please enter an invoice number.")
            return

        total_amount = self.total_amount_spinbox.value()
        if total_amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Total amount must be greater than zero.")
            return

        currency = self.currency_edit.text().strip()
        if not currency:
            QMessageBox.warning(self, "Validation Error", "Please enter a currency code (e.g., USD, EUR).")
            return


        # Gather Data
        invoice_data = {
            'client_id': client_id,
            'project_id': self.project_combo.currentData(), # Can be None
            'invoice_number': invoice_number,
            'issue_date': self.issue_date_edit.date().toString("yyyy-MM-dd"),
            'due_date': self.due_date_edit.date().toString("yyyy-MM-dd"),
            'total_amount': total_amount,
            'currency': currency,
            'payment_status': self.payment_status_combo.currentText().lower(),
            'notes': self.notes_edit.toPlainText().strip(),
            # payment_date, payment_method, transaction_id are usually set when recording payment
        }

        try:
            new_invoice_id = invoices_crud.add_invoice(invoice_data)
            if new_invoice_id:
                QMessageBox.information(self, "Success", f"Invoice {invoice_number} created successfully with ID: {new_invoice_id}.")
                self.accept() # Closes the dialog with QDialog.Accepted
            else:
                # This case might happen if add_invoice returns None on non-exception failure (e.g. unique constraint)
                QMessageBox.warning(self, "Creation Failed", "Failed to create invoice. The invoice number might already exist or there was a database issue.")
        except Exception as e:
            print(f"Error creating invoice: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred while creating the invoice: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # --- For Standalone Testing with Data (Example) ---
    # import os
    # APP_ROOT_DIR_STANDALONE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # if APP_ROOT_DIR_STANDALONE not in sys.path:
    #     sys.path.insert(0, APP_ROOT_DIR_STANDALONE)
    #
    # from db import db_config, init_schema
    # import uuid
    #
    # db_config.DATABASE_PATH = "test_manual_invoice_dialog.db"
    # init_schema.initialize_database()
    #
    # # Add dummy clients and projects for combobox population
    # try:
    #     client_id_1 = str(uuid.uuid4())
    #     client_id_2 = str(uuid.uuid4())
    #     project_id_1a = str(uuid.uuid4())
    #     project_id_1b = str(uuid.uuid4())
    #
    #     # Simplified direct SQL for test setup
    #     conn = sqlite3.connect(db_config.DATABASE_PATH)
    #     cursor = conn.cursor()
    #     cursor.execute("INSERT INTO Clients (client_id, client_name, project_identifier) VALUES (?, ?, ?)", (client_id_1, "Test Client Alpha Dialog", "TCDA"))
    #     cursor.execute("INSERT INTO Clients (client_id, client_name, project_identifier) VALUES (?, ?, ?)", (client_id_2, "Test Client Beta Dialog", "TCDB"))
    #     # Need status and user for project
    #     status_id = cursor.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)", ("Planning", "Project")).lastrowid
    #     user_id = cursor.execute("INSERT OR IGNORE INTO Users (user_id, username, email, password_hash, role) VALUES (?, ?, ?, ?, ?)", (str(uuid.uuid4()), "dummyuser_dialog", "du@ex.com", "hash", "admin")).lastrowid
    #
    #     cursor.execute("INSERT INTO Projects (project_id, client_id, project_name, status_id, manager_team_member_id) VALUES (?, ?, ?, ?, ?)", (project_id_1a, client_id_1, "Project Alpha One (Dialog)", status_id, user_id))
    #     cursor.execute("INSERT INTO Projects (project_id, client_id, project_name, status_id, manager_team_member_id) VALUES (?, ?, ?, ?, ?)", (project_id_1b, client_id_1, "Project Alpha Two (Dialog)", status_id, user_id))
    #     conn.commit()
    #     conn.close()
    #     print("Dummy clients and projects added for dialog test.")
    # except Exception as e_setup:
    #     print(f"Error setting up dummy data for dialog test: {e_setup}")
    # --- End Standalone Example Setup ---

    dialog = ManualInvoiceDialog()
    dialog.show()

    # If using the standalone setup, this ensures the dialog can actually populate from the DB
    # If not, it will show empty combo boxes (or with errors printed to console if CRUDs fail)

    sys.exit(app.exec_())
```
