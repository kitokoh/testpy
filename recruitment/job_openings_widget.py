from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QVariant # Added QVariant for custom data roles
import requests # For making API calls
import json # For handling JSON data, especially in error messages

# Assuming API base URL is something like this. This should be configurable.
API_BASE_URL = "http://localhost:8000/recruitment" # Adjusted to match FastAPI router prefix

class JobOpeningsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)

        # Action buttons layout
        self.actions_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New Opening")
        self.add_button.clicked.connect(self.open_add_job_dialog)
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.open_edit_job_dialog)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_job)
        self.view_candidates_button = QPushButton("View Candidates")
        self.view_candidates_button.clicked.connect(self.view_job_candidates)

        self.actions_layout.addWidget(self.add_button)
        self.actions_layout.addWidget(self.edit_button)
        self.actions_layout.addWidget(self.delete_button)
        self.actions_layout.addStretch()
        self.actions_layout.addWidget(self.view_candidates_button)

        self.main_layout.addLayout(self.actions_layout)

        # Table for job openings
        self.job_openings_table = QTableWidget()
        # Adjusted columns for clarity: Title, Status, Closing Date, Department ID, Description
        # The job_opening_id will be stored using Qt.UserRole on the first visible item (Title)
        self.job_openings_table.setColumnCount(5)
        self.job_openings_table.setHorizontalHeaderLabels(["Title", "Status ID", "Closing Date", "Department ID", "Description"])

        # Table properties
        self.job_openings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.job_openings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.job_openings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.job_openings_table.horizontalHeader().setStretchLastSection(True)
        # self.job_openings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Commented out for more control
        self.job_openings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Title
        self.job_openings_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch) # Description
        self.job_openings_table.verticalHeader().setVisible(False)

        self.job_openings_table.selectionModel().selectionChanged.connect(self.update_action_buttons_state)

        self.main_layout.addWidget(self.job_openings_table)
        self.setLayout(self.main_layout)

        self.update_action_buttons_state()
        self.load_job_openings()

    def load_job_openings(self):
        self.job_openings_table.setRowCount(0)
        try:
            response = requests.get(f"{API_BASE_URL}/job-openings/")
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            job_openings = response.json()

            for row_num, job_data in enumerate(job_openings):
                self.job_openings_table.insertRow(row_num)

                title_item = QTableWidgetItem(job_data.get("title"))
                # Store the full job_opening_id or even the whole job_data dict for later use
                title_item.setData(Qt.UserRole, job_data) # Store full dict

                self.job_openings_table.setItem(row_num, 0, title_item)
                self.job_openings_table.setItem(row_num, 1, QTableWidgetItem(str(job_data.get("status_id", ""))))
                self.job_openings_table.setItem(row_num, 2, QTableWidgetItem(job_data.get("closing_date", "")))
                self.job_openings_table.setItem(row_num, 3, QTableWidgetItem(str(job_data.get("department_id", ""))))
                self.job_openings_table.setItem(row_num, 4, QTableWidgetItem(job_data.get("description", "")))

            # self.job_openings_table.resizeColumnsToContents()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load job openings: {e}")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "API Error", "Failed to parse job openings data from server.")


    def open_add_job_dialog(self):
        from .dialogs.job_opening_dialog import JobOpeningDialog
        dialog = JobOpeningDialog(parent=self)
        if dialog.exec_():
            job_data_to_submit = dialog.get_data()
            if job_data_to_submit:
                try:
                    # Remove status_text if API expects status_id directly and it's already there
                    # The JobOpeningCreate Pydantic model expects 'status_id', not 'status_text'
                    if 'status_text' in job_data_to_submit and 'status_id' in job_data_to_submit:
                        del job_data_to_submit['status_text']

                    response = requests.post(f"{API_BASE_URL}/job-openings/", json=job_data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Add Job Opening", "Job opening added successfully.")
                    self.load_job_openings()
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to add job opening: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to add job opening: {e}")

    def open_edit_job_dialog(self):
        selected_item_data = self.get_selected_item_data()
        if not selected_item_data:
            QMessageBox.warning(self, "Edit Job", "Please select a job opening to edit.")
            return

        job_opening_id = selected_item_data.get("job_opening_id")
        if not job_opening_id: # Should not happen if data is stored correctly
            QMessageBox.critical(self, "Error", "Could not retrieve job opening ID for selected row.")
            return

        # Fetch full details for editing (or use already stored selected_item_data if complete)
        # For this example, we assume selected_item_data from UserRole is sufficient for dialog.
        # If not, an API call like:
        # response = requests.get(f"{API_BASE_URL}/job-openings/{job_opening_id}")
        # response.raise_for_status()
        # job_details_for_dialog = response.json()
        # For now, using what's in selected_item_data which should be the full dict from API

        from .dialogs.job_opening_dialog import JobOpeningDialog
        dialog = JobOpeningDialog(job_data=selected_item_data, parent=self)

        if dialog.exec_():
            updated_data_to_submit = dialog.get_data()
            if updated_data_to_submit:
                # Remove fields that shouldn't be in PUT or are not part of JobOpeningUpdate model
                # For example, job_opening_id, created_at, updated_at from the data passed to API
                # The JobOpeningUpdate Pydantic model defines what's acceptable.
                # get_data() from dialog should already be shaping this.
                if 'status_text' in updated_data_to_submit and 'status_id' in updated_data_to_submit:
                     del updated_data_to_submit['status_text']

                try:
                    response = requests.put(f"{API_BASE_URL}/job-openings/{job_opening_id}", json=updated_data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Edit Job Opening", "Job opening updated successfully.")
                    self.load_job_openings()
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to update job opening: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to update job opening: {e}")

    def delete_selected_job(self):
        selected_item_data = self.get_selected_item_data()
        if not selected_item_data:
            QMessageBox.warning(self, "Delete Job", "Please select a job opening to delete.")
            return

        job_id = selected_item_data.get("job_opening_id")
        job_title = selected_item_data.get("title")

        reply = QMessageBox.question(self, "Delete Job Opening",
                                     f"Are you sure you want to delete '{job_title}' (ID: {job_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                response = requests.delete(f"{API_BASE_URL}/job-openings/{job_id}")
                response.raise_for_status() # Checks for 4xx/5xx errors
                QMessageBox.information(self, "Delete Job Opening", "Job opening deleted successfully.")
                self.load_job_openings()
            except requests.exceptions.HTTPError as e:
                # Try to get detail from JSON response if possible
                error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                QMessageBox.critical(self, "API Error", f"Failed to delete job opening: {error_detail}")
            except requests.exceptions.RequestException as e:
                 QMessageBox.critical(self, "API Error", f"Failed to delete job opening: {e}")


    def view_job_candidates(self):
        selected_item_data = self.get_selected_item_data()
        if not selected_item_data:
            QMessageBox.warning(self, "View Candidates", "Please select a job opening.")
            return

        job_id = selected_item_data.get('job_opening_id')
        job_title = selected_item_data.get('title')
        QMessageBox.information(self, "View Candidates", f"Viewing candidates for '{job_title}' (ID: {job_id}).\n(Implementation for candidate view is pending).")
        # TODO: Here you would typically emit a signal or call a method on a parent/controller
        # to switch to a candidates view, passing the job_id.

    def get_selected_item_data(self) -> dict | None:
        """
        Retrieves the full data dictionary stored in Qt.UserRole of the first item
        in the selected row.
        """
        selected_items = self.job_openings_table.selectedItems()
        if not selected_items:
            return None

        # Assuming the data (full job opening dict) is stored in the UserRole of the first column's item
        first_item_in_row = self.job_openings_table.item(selected_items[0].row(), 0)
        if first_item_in_row:
            return first_item_in_row.data(Qt.UserRole)
        return None

    def update_action_buttons_state(self):
        """
        Enables or disables action buttons based on table selection.
        """
        has_selection = bool(self.job_openings_table.selectedItems())
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.view_candidates_button.setEnabled(has_selection)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    # This basic __main__ is for testing the widget's appearance and basic interaction.
    # To test API calls, the FastAPI server must be running and accessible at API_BASE_URL.

    # For the dynamic import of JobOpeningDialog to work in this test block,
    # ensure recruitment/dialogs/job_opening_dialog.py exists and is importable.
    # If you run this file directly, Python's import system might need `recruitment`
    # to be in PYTHONPATH or the current working directory to be the parent of `recruitment`.

    # Example:
    # Assuming you are in the root directory of the project (parent of 'recruitment' folder)
    # you might run: python -m recruitment.job_openings_widget

    app = QApplication(sys.argv)

    # Create a dummy JobOpeningDialog if the real one is not available for isolated testing
    # This is generally not needed if you run this as part of the application or ensure paths are correct.
    try:
        from .dialogs.job_opening_dialog import JobOpeningDialog
    except ImportError:
        print("Warning: Could not import JobOpeningDialog. Using a dummy for __main__ test.")
        class JobOpeningDialog(QWidget): # Dummy dialog
            def __init__(self, job_data=None, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Dummy Dialog (Real one not found)")
                layout = QVBoxLayout(self)
                label_text = "Dummy Dialog"
                if job_data: label_text += f" for {job_data.get('title')}"
                layout.addWidget(QLabel(label_text))
                self._job_data = job_data if job_data else {}
            def exec_(self): return 0 # Simulate cancel
            def get_data(self): return self._job_data

    widget = JobOpeningsWidget()
    widget.setWindowTitle("Job Openings Test Display") # Set a window title for the test
    widget.resize(1000, 600) # Give it a decent size for testing
    widget.show()
    sys.exit(app.exec_())
```
