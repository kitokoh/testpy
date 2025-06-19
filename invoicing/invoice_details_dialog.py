import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QDialogButtonBox, QScrollArea, QWidget, QApplication
)
from PyQt5.QtCore import Qt

# Assuming APP_ROOT_DIR setup is done in the main application for db access
# For standalone testing, this widget might need to ensure paths are set.
# For now, assume db.cruds are importable.
from db.cruds import invoices_crud, clients_crud
from db.cruds import projects_crud # Assuming this exists with get_project_by_id

class InvoiceDetailsDialog(QDialog):
    def __init__(self, invoice_id, parent=None):
        super().__init__(parent)
        self.setObjectName("invoiceDetailsDialog")
        self.invoice_id = invoice_id
        self.invoice_data = None # To store fetched data

        self.init_ui()
        self.load_invoice_data()

    def init_ui(self):
        self.setWindowTitle(f"Invoice Details - ID: {self.invoice_id[:8]}...") # Show partial ID
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget() # Made it a class member to set object name
        self.content_widget.setObjectName("detailsFormContainer")
        self.form_layout = QFormLayout(self.content_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.form_layout.setLabelAlignment(Qt.AlignRight) # Align labels to the right

        self.content_widget.setLayout(self.form_layout)
        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area)

        self.details_button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.details_button_box.setObjectName("detailsButtonBox")
        self.details_button_box.rejected.connect(self.reject) # Close button triggers reject
        main_layout.addWidget(self.details_button_box)

        self.setLayout(main_layout)

    def _add_form_row(self, label_text, value_text):
        """Helper to add a row to the form layout with bold label."""
        label = QLabel(f"<b>{label_text}:</b>")
        value = QLabel(str(value_text) if value_text is not None else "N/A")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse) # Allow copying value
        value.setWordWrap(True) # Wrap long text
        self.form_layout.addRow(label, value)

    def load_invoice_data(self):
        try:
            self.invoice_data = invoices_crud.get_invoice_by_id(self.invoice_id)
        except Exception as e:
            print(f"Error fetching invoice details: {e}")
            self.invoice_data = None

        if not self.invoice_data:
            self._clear_layout(self.form_layout)
            error_label = QLabel("<font color='red'>Error: Invoice not found or could not be loaded.</font>")
            self.form_layout.addRow(error_label)
            return

        # Populate form with invoice data
        self._add_form_row("Invoice ID", self.invoice_data.get('invoice_id'))
        self._add_form_row("Invoice Number", self.invoice_data.get('invoice_number'))

        # Client Details
        client_id = self.invoice_data.get('client_id')
        client_display = str(client_id)
        if client_id:
            try:
                client = clients_crud.get_client_by_id(client_id)
                if client:
                    client_name = client.get('client_name', 'N/A')
                    client_display = f"{client_name} (ID: {client_id})"
            except Exception as e:
                print(f"Error fetching client details for ID {client_id}: {e}")
                client_display = f"Error loading client (ID: {client_id})"
        self._add_form_row("Client", client_display)

        # Project Details
        project_id = self.invoice_data.get('project_id')
        project_display = "N/A"
        if project_id:
            try:
                project = projects_crud.get_project_by_id(project_id) # Assumes projects_crud exists
                if project:
                    project_name = project.get('project_name', 'N/A')
                    project_display = f"{project_name} (ID: {project_id})"
                else:
                    project_display = f"Project not found (ID: {project_id})"
            except AttributeError: # If projects_crud or get_project_by_id doesn't exist
                print("Warning: projects_crud.get_project_by_id not available. Displaying ID only.")
                project_display = f"Project ID: {project_id} (details unavailable)"
            except Exception as e:
                print(f"Error fetching project details for ID {project_id}: {e}")
                project_display = f"Error loading project (ID: {project_id})"
        self._add_form_row("Project", project_display)

        # Document ID
        self._add_form_row("Associated Document ID", self.invoice_data.get('document_id'))

        # Dates
        self._add_form_row("Issue Date", self.invoice_data.get('issue_date'))
        self._add_form_row("Due Date", self.invoice_data.get('due_date'))

        # Financials
        total_amount = self.invoice_data.get('total_amount', 0.0)
        currency = self.invoice_data.get('currency', '')
        self._add_form_row("Total Amount", f"{total_amount:,.2f} {currency}")

        self._add_form_row("Payment Status", str(self.invoice_data.get('payment_status', '')).title())
        self._add_form_row("Payment Date", self.invoice_data.get('payment_date'))
        self._add_form_row("Payment Method", self.invoice_data.get('payment_method'))
        self._add_form_row("Transaction ID", self.invoice_data.get('transaction_id'))

        # Other
        self._add_form_row("Notes", self.invoice_data.get('notes'))
        self._add_form_row("Created At", self.invoice_data.get('created_at'))
        self._add_form_row("Updated At", self.invoice_data.get('updated_at'))

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    child_layout = item.layout()
                    if child_layout is not None:
                        self._clear_layout(child_layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # This dialog is best tested by launching it from InvoiceManagementWidget
    # after an invoice is selected. For standalone, you'd need to ensure
    # the database is set up and a valid invoice_id exists.

    # Example of how to set up for standalone test (requires actual DB setup):
    # ---
    # APP_ROOT_DIR_STANDALONE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # if APP_ROOT_DIR_STANDALONE not in sys.path:
    #     sys.path.insert(0, APP_ROOT_DIR_STANDALONE)
    # from db import db_config, init_schema
    # from db.cruds import invoices_crud # To potentially add a test invoice
    # db_config.DATABASE_PATH = "test_invoice_details.db" # Use a test DB
    # init_schema.initialize_database()
    #
    # # Add a dummy client, project if needed by your FK constraints for invoices
    # # client_id = clients_crud.add_client(...)
    # # project_id = projects_crud.add_project(...)
    #
    # test_invoice_data = {
    #     'client_id': "dummy_client_id", # Replace with actual or created client ID
    #     'invoice_number': f"TEST-INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    #     'issue_date': "2023-01-01",
    #     'due_date': "2023-02-01",
    #     'total_amount': 123.45,
    #     'currency': 'USD',
    #     'payment_status': 'unpaid'
    # }
    # try:
    #     # Ensure invoices_crud.add_invoice is adapted or use direct SQL to insert
    #     # For this example, we assume such an invoice exists or is created.
    #     # test_id = invoices_crud.add_invoice(test_invoice_data)
    #     # if test_id:
    #     #     dialog = InvoiceDetailsDialog(invoice_id=test_id)
    #     #     dialog.exec_() # Use exec_() for modal dialog
    #     # else:
    #     #     print("Failed to create a test invoice for the dialog.")
    #     print("To test InvoiceDetailsDialog, run it via InvoiceManagementWidget.")
    # except Exception as e:
    #     print(f"Error during standalone test setup: {e}")
    # ---

    main_window = QWidget()
    layout = QVBoxLayout(main_window)
    label = QLabel("To test InvoiceDetailsDialog, run it via InvoiceManagementWidget with a selected invoice.\n"
                   "Ensure the database is initialized and contains invoices.")
    layout.addWidget(label)
    main_window.setWindowTitle("InvoiceDetailsDialog Test Placeholder")
    main_window.show()

    sys.exit(app.exec_())
```
