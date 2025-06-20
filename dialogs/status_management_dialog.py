import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QTableWidget, QTableWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt

# Assuming db_manager.py is in the parent directory or accessible via PYTHONPATH
# For direct import if structure is /app/dialogs and /app/db
import os
import sys
# Add the parent directory of 'dialogs' to sys.path if db is a sibling directory
# This is a common way to handle imports in such structures when running files directly
# For a packaged application, you'd use relative imports like from ..db.cruds...
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)
# if parent_dir not in sys.path:
#    sys.path.append(parent_dir)
# For this specific environment, let's assume direct import paths can be resolved
# or that the calling environment (e.g. main app) has set up sys.path correctly.
# We will try a relative import first, then a direct one if that fails (common for scripts)
try:
    from ..db.cruds.status_settings_crud import (
        add_status_setting,
        get_all_status_settings,
        get_status_setting_by_id,
        update_status_setting,
        delete_status_setting,
        is_status_in_use
    )
    from .add_edit_status_dialog import AddEditStatusDialog
except ImportError:
    # Fallback for running script directly or if relative import fails
    from db.cruds.status_settings_crud import (
        add_status_setting,
        get_all_status_settings,
        get_status_setting_by_id,
        update_status_setting,
        delete_status_setting,
        is_status_in_use
    )
    from dialogs.add_edit_status_dialog import AddEditStatusDialog


class StatusManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Statuses")
        self.setMinimumSize(600, 400) # Set a minimum size for better usability
        self.init_ui()
        self.load_statuses() # Load statuses after UI is initialized
        self._update_button_states() # Initial state of buttons

    def init_ui(self):
        # Main layout
        layout = QVBoxLayout(self)

        # Table Widget
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(["ID", "Name", "Type", "Color", "Sort Order"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers) # Disable editing directly in table
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows) # Select whole rows
        layout.addWidget(self.table_widget)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete") # Will be used in a future task
        self.close_button = QPushButton("Close")

        # Disable Edit and Delete buttons initially
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

        # Connect signals
        self.add_button.clicked.connect(self.handle_add_status)
        self.edit_button.clicked.connect(self.handle_edit_status)
        self.delete_button.clicked.connect(self.handle_delete_status)
        self.close_button.clicked.connect(self.accept)
        self.table_widget.itemSelectionChanged.connect(self._update_button_states)


    def _update_button_states(self):
        """Enable/disable Edit and Delete buttons based on table selection."""
        is_row_selected = bool(self.table_widget.selectedItems())
        self.edit_button.setEnabled(is_row_selected)
        self.delete_button.setEnabled(is_row_selected) # Also manage delete button state

    def load_statuses(self):
        # print("load_statuses method called") # Less verbose for routine calls
        try:
            statuses = get_all_status_settings()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load statuses: {e}")
            statuses = [] # Ensure statuses is an empty list on error

        self.table_widget.setRowCount(0) # Clear existing rows

        if not statuses:
            # print("No statuses found or error in fetching.")
            return

        self.table_widget.setRowCount(len(statuses))
        for row_idx, status_data in enumerate(statuses):
            status_id_item = QTableWidgetItem(str(status_data.get("status_id", "")))
            # Store the actual ID in UserRole for later retrieval
            status_id_item.setData(Qt.UserRole, status_data.get("status_id"))

            name_item = QTableWidgetItem(status_data.get("status_name", ""))
            type_item = QTableWidgetItem(status_data.get("status_type", ""))
            color_item = QTableWidgetItem(status_data.get("color_hex", ""))
            sort_order_item = QTableWidgetItem(str(status_data.get("sort_order", "")))

            self.table_widget.setItem(row_idx, 0, status_id_item)
            self.table_widget.setItem(row_idx, 1, name_item)
            self.table_widget.setItem(row_idx, 2, type_item)
            self.table_widget.setItem(row_idx, 3, color_item)
            self.table_widget.setItem(row_idx, 4, sort_order_item)

        # Optional: Resize columns to content after loading data
        # self.table_widget.resizeColumnsToContents()

    def handle_add_status(self):
        dialog = AddEditStatusDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                # The add_status_setting function in the crud might need the @_manage_conn decorator
                # or explicit connection management if it's not already there.
                # Assuming it handles its own connection or is decorated.
                success_id = add_status_setting(
                    status_name=data["status_name"],
                    status_type=data["status_type"],
                    color_hex=data["color_hex"],
                    sort_order=data["sort_order"]
                )
                if success_id: # If it returns an ID or True
                    QMessageBox.information(self, "Success", f"Status '{data['status_name']}' added successfully.")
                    self.load_statuses()  # Refresh the table
                else:
                    QMessageBox.warning(self, "Failure", f"Failed to add status '{data['status_name']}'. Check logs for details.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while adding status: {e}")
                print(f"Error in handle_add_status: {e}") # For debugging

    def handle_edit_status(self):
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a status to edit.")
            return

        # Get status_id from the first item in the selected row (ID column)
        # Assumes ID is in the first column and UserRole stores the ID
        selected_row = self.table_widget.currentRow()
        id_item = self.table_widget.item(selected_row, 0) # ID is in column 0
        if not id_item:
            QMessageBox.critical(self, "Error", "Could not retrieve status ID from selected row.")
            return

        status_id = id_item.data(Qt.UserRole)
        if status_id is None:
            QMessageBox.critical(self, "Error", "No status ID associated with the selected row.")
            return

        try:
            current_status_data = get_status_setting_by_id(status_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not fetch status details: {e}")
            return

        if not current_status_data:
            QMessageBox.warning(self, "Not Found", f"Status with ID {status_id} not found.")
            return

        dialog = AddEditStatusDialog(self, status_data=current_status_data)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            try:
                success = update_status_setting(
                    status_id=status_id,
                    status_name=new_data["status_name"],
                    status_type=new_data["status_type"],
                    color_hex=new_data["color_hex"], # Pass None if not changed or to clear, based on dialog logic
                    sort_order=new_data["sort_order"]
                )
                if success:
                    QMessageBox.information(self, "Success", f"Status '{new_data['status_name']}' updated successfully.")
                    self.load_statuses()
                else:
                    QMessageBox.warning(self, "Failure", f"Failed to update status '{new_data['status_name']}'. It might have been deleted or an error occurred.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while updating status: {e}")
                print(f"Error in handle_edit_status: {e}")

    def handle_delete_status(self):
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a status to delete.")
            return

        selected_row = self.table_widget.currentRow()
        id_item = self.table_widget.item(selected_row, 0) # ID is in column 0
        if not id_item:
            QMessageBox.critical(self, "Error", "Could not retrieve status ID from selected row.")
            return

        status_id = id_item.data(Qt.UserRole)
        status_name_item = self.table_widget.item(selected_row, 1) # Name is in column 1
        status_name = status_name_item.text() if status_name_item else "this status"


        if status_id is None:
            QMessageBox.critical(self, "Error", "No status ID associated with the selected row.")
            return

        try:
            if is_status_in_use(status_id):
                QMessageBox.warning(self, "Cannot Delete Status",
                                    f"The status '{status_name}' (ID: {status_id}) cannot be deleted "
                                    "because it is currently in use by one or more clients.")
                return
        except Exception as e: # Catch potential errors from is_status_in_use itself
            QMessageBox.critical(self, "Error", f"Could not verify if status is in use: {e}")
            # is_status_in_use now returns True on DB error, so this path might be less likely
            # but good to have a catch-all.
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete the status '{status_name}' (ID: {status_id})?\n"
                                     "This action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                if delete_status_setting(status_id):
                    QMessageBox.information(self, "Success", f"Status '{status_name}' deleted successfully.")
                    self.load_statuses()
                else:
                    QMessageBox.warning(self, "Failure", f"Failed to delete status '{status_name}'. It might have already been deleted or an error occurred.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while deleting status: {e}")
                print(f"Error in handle_delete_status: {e}")


if __name__ == '__main__':
    # This part is for testing the dialog independently
    # For this to work, the db setup needs to be runnable.
    # This usually means the db file is created if it doesn't exist,
    # and tables are created by a setup script or db_manager.init_db().

    # Ensure DB is initialized for testing
    try:
        from db.db_manager import init_db, get_db_connection
        # Attempt to initialize DB (creates tables if they don't exist)
        init_db()

        # Verify connection
        conn = get_db_connection()
        if conn is None:
            print("Failed to get DB connection for testing StatusManagementDialog.")
            # sys.exit(1) # Or handle error appropriately
        else:
            conn.close() # Close it, db calls will reopen
            print("DB connection successful for testing.")

    except ImportError:
        print("Could not import db_manager to initialize DB for testing. Ensure PYTHONPATH is correct.")
        # sys.exit(1)
    except Exception as e:
        print(f"Error during DB initialization for testing: {e}")
        # sys.exit(1)

    app = QApplication(sys.argv)
    dialog = StatusManagementDialog()
    dialog.exec_()
    sys.exit(app.exec_())
