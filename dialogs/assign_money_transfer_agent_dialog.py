# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QDoubleSpinBox, QDialogButtonBox, QMessageBox, QLabel
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

# Assuming CRUD functions are directly importable from their modules
# Adjust if a central db_manager is used for these specific CRUDs as well
try:
    from db.cruds import money_transfer_agents_crud as mta_crud
    from db.cruds import client_order_money_transfer_agents_crud as coma_crud
except ImportError as e:
    # This is a critical problem for the dialog's functionality.
    # A real application might log this and disable functionality or show an error.
    # For now, we'll print to stderr and raise, as the dialog cannot function.
    import sys
    print(f"CRITICAL: Failed to import CRUD modules: {e}", file=sys.stderr)
    # Depending on the application's structure, might raise an error or have a fallback.
    # For now, let's make it clear that the dialog won't work as intended.
    # raise ImportError(f"Failed to import CRUD modules for AssignMoneyTransferAgentDialog: {e}") from e
    # Or, define dummy functions if we want the UI to load but be non-functional:
    class DummyCRUD:
        def get_all_money_transfer_agents(self, *args, **kwargs): return []
        def assign_agent_to_client_order(self, *args, **kwargs): return {'success': False, 'error': 'CRUD module not loaded'}
    mta_crud = DummyCRUD()
    coma_crud = DummyCRUD()
    QMessageBox.critical(None, "Dev Error", "AssignMoneyTransferAgentDialog failed to load database modules. Functionality will be limited.")


class AssignMoneyTransferAgentDialog(QDialog):
    def __init__(self, client_id, order_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.order_id = order_id # This corresponds to project_id

        self.setWindowTitle(self.tr("Assign Money Transfer Agent"))
        self.setMinimumWidth(450)
        self.setup_ui()
        self.load_available_agents()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10) # Consistent spacing

        # Agent ComboBox
        self.agent_combo = QComboBox()
        form_layout.addRow(self.tr("Available Agent:"), self.agent_combo)

        # Assignment Details
        self.assignment_details_edit = QTextEdit()
        self.assignment_details_edit.setPlaceholderText(self.tr("Enter any specific details about this assignment..."))
        self.assignment_details_edit.setFixedHeight(100) # Slightly taller for more details
        form_layout.addRow(self.tr("Assignment Details:"), self.assignment_details_edit)

        # Fee Estimate
        self.fee_estimate_spinbox = QDoubleSpinBox()
        self.fee_estimate_spinbox.setRange(0.0, 9999999.99) # Standard range
        self.fee_estimate_spinbox.setDecimals(2)
        self.fee_estimate_spinbox.setPrefix("$ ") # Assuming USD, adjust if currency varies
        form_layout.addRow(self.tr("Fee Estimate:"), self.fee_estimate_spinbox)

        main_layout.addLayout(form_layout)

        # Button Box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Assign"))
        # Example of setting object name for styling if used:
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Cancel"))

        self.button_box.accepted.connect(self.accept_assignment) # Connect to custom accept method
        self.button_box.rejected.connect(self.reject) # Standard reject

        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_available_agents(self):
        self.agent_combo.clear()
        try:
            # Fetch only active agents
            agents = mta_crud.get_all_money_transfer_agents(include_deleted=False)
            if not agents:
                self.agent_combo.addItem(self.tr("No money transfer agents available."), None)
                self.agent_combo.setEnabled(False)
                # Optionally, disable the OK button as well
                self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
                return

            self.agent_combo.setEnabled(True)
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            for agent in agents:
                # Display name, store agent_id as data
                self.agent_combo.addItem(agent.get('name', self.tr("Unnamed Agent")), agent.get('agent_id'))
        except Exception as e:
            # Log the error for debugging
            # logger.error(f"Failed to load money transfer agents: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Database Error"),
                                 self.tr("Could not load money transfer agents: {0}").format(str(e)))
            self.agent_combo.setEnabled(False)
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def accept_assignment(self):
        selected_agent_id = self.agent_combo.currentData()
        details_text = self.assignment_details_edit.toPlainText().strip()
        fee_value = self.fee_estimate_spinbox.value()

        if selected_agent_id is None:
            QMessageBox.warning(self, self.tr("Validation Error"),
                                self.tr("Please select a money transfer agent."))
            self.agent_combo.setFocus()
            return

        # Call the CRUD function to assign the agent
        try:
            result = coma_crud.assign_agent_to_client_order(
                client_id=self.client_id,
                order_id=self.order_id, # project_id is passed as order_id
                agent_id=selected_agent_id,
                assignment_details=details_text,
                fee_estimate=fee_value
                # user_id could be added if needed by the CRUD and available here
            )

            if result.get('success'):
                QMessageBox.information(self, self.tr("Success"),
                                        self.tr("Money transfer agent assigned successfully. Assignment ID: {0}").format(result.get('assignment_id')))
                super().accept()  # Close the dialog and return QDialog.Accepted
            else:
                error_message = result.get('error', self.tr("An unknown error occurred."))
                QMessageBox.warning(self, self.tr("Assignment Failed"),
                                    self.tr("Could not assign the money transfer agent: {0}").format(error_message))
        except Exception as e:
            # logger.error(f"Unexpected error during agent assignment: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Unexpected Error"),
                                 self.tr("An unexpected error occurred: {0}").format(str(e)))

# Example usage (for testing purposes, normally instantiated by other parts of the application)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # Dummy client_id and order_id for testing
    test_client_id = "client_uuid_123"
    test_order_id = "order_proj_uuid_456"

    # This basic setup is needed to run a QDialog
    app = QApplication(sys.argv)

    # Example: How mta_crud might be populated for testing if imports fail initially
    # This is just for local testing of the dialog in isolation.
    if isinstance(mta_crud, DummyCRUD): # If the real import failed
        print("Using dummy mta_crud for dialog testing.")
        class RealDummyMtaCRUD:
            def get_all_money_transfer_agents(self, *args, **kwargs):
                return [
                    {'agent_id': 'agent1', 'name': 'Test Agent One'},
                    {'agent_id': 'agent2', 'name': 'Test Agent Two'}
                ]
        mta_crud = RealDummyMtaCRUD()

        class RealDummyComaCRUD:
            def assign_agent_to_client_order(self, client_id, order_id, agent_id, assignment_details, fee_estimate):
                print(f"Dummy Assign: Client({client_id}), Order({order_id}), Agent({agent_id}), Details({assignment_details}), Fee({fee_estimate})")
                return {'success': True, 'assignment_id': 'dummy_assign_id_789'}
        coma_crud = RealDummyComaCRUD()


    dialog = AssignMoneyTransferAgentDialog(client_id=test_client_id, order_id=test_order_id)
    if dialog.exec_() == QDialog.Accepted:
        print("Assignment accepted (dialog perspective).")
    else:
        print("Assignment cancelled (dialog perspective).")
    sys.exit(app.exec_())
