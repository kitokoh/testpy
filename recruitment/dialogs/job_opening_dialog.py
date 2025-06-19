from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QTextEdit, QComboBox, QDialogButtonBox,
                             QDateEdit, QMessageBox)
from PyQt5.QtCore import QDate, Qt

class JobOpeningDialog(QDialog):
    def __init__(self, job_data: dict = None, parent=None):
        super().__init__(parent)

        self.job_data = job_data # Store for pre-filling if in edit mode

        if self.job_data:
            self.setWindowTitle("Edit Job Opening")
        else:
            self.setWindowTitle("Add New Job Opening")

        self.setMinimumWidth(400)

        # Main layout
        self.layout = QVBoxLayout(self)

        # Form layout for input fields
        self.form_layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.form_layout.addRow("Title:", self.title_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter detailed description of the job role, responsibilities, and requirements.")
        self.form_layout.addRow("Description:", self.description_edit)

        self.status_combo = QComboBox()
        # TODO: These statuses should ideally come from a central config or API call to StatusSettings
        # For now, using placeholder IDs. These should match what's in your DB's StatusSettings table for 'JobOpening' type.
        self.status_map_display_to_id = {
            "Open": 1,
            "Closed": 2,
            "On Hold": 3,
            "Draft": 4
        }
        # For populating combobox and finding by ID
        self.status_map_id_to_display = {v: k for k, v in self.status_map_display_to_id.items()}

        self.status_combo.addItems(self.status_map_display_to_id.keys())
        self.form_layout.addRow("Status:", self.status_combo)

        self.closing_date_edit = QDateEdit()
        self.closing_date_edit.setCalendarPopup(True)
        self.closing_date_edit.setDate(QDate.currentDate().addDays(30)) # Default to 30 days from now
        self.closing_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.form_layout.addRow("Closing Date:", self.closing_date_edit)

        # Department ID (Optional, could be QLineEdit or QComboBox if departments are predefined)
        self.department_id_edit = QLineEdit()
        self.department_id_edit.setPlaceholderText("(Optional) Enter Department ID")
        # self.form_layout.addRow("Department ID:", self.department_id_edit) # Add if needed

        # Created By User ID (Optional, usually set by backend)
        self.created_by_user_id_edit = QLineEdit()
        self.created_by_user_id_edit.setPlaceholderText("(Optional) Enter Creator User ID")
        # self.form_layout.addRow("Creator User ID:", self.created_by_user_id_edit) # Add if needed

        self.layout.addLayout(self.form_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        # If job_data is provided (edit mode), populate fields
        if self.job_data:
            self.populate_form()

    def populate_form(self):
        """Populates the form fields with data from self.job_data."""
        if not self.job_data:
            return

        self.title_edit.setText(self.job_data.get("title", ""))
        self.description_edit.setPlainText(self.job_data.get("description", ""))

        # Set status in QComboBox
        # This assumes job_data.status is the display name e.g. "Open"
        # If job_data.status is an ID, you'll need to map it back or change how statuses are handled
        status_text = self.job_data.get("status") # This was from get_selected_row_data
        if status_text:
            index = self.status_combo.findText(status_text, Qt.MatchFixedString)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
            else:
                # If status from table isn't in combo, maybe add it or log warning
            # print(f"Warning: Status '{status_text}' not found in QComboBox during edit.")
                # Potentially, the status_id from the actual data model should be used here
                # For now, this relies on the text matching.
            status_id_from_data = self.job_data.get("status_id")
            if status_id_from_data is not None:
                status_display_name = self.status_map_id_to_display.get(status_id_from_data)
                if status_display_name:
                    index = self.status_combo.findText(status_display_name, Qt.MatchFixedString)
                    if index >= 0:
                        self.status_combo.setCurrentIndex(index)
                else:
                    print(f"Warning: Status ID '{status_id_from_data}' not found in status_map_id_to_display during edit.")


        closing_date_str = self.job_data.get("closing_date")
        if closing_date_str:
            q_date = QDate.fromString(closing_date_str, "yyyy-MM-dd") # Ensure format matches
            if q_date.isValid():
                self.closing_date_edit.setDate(q_date)

        # department_id_val = self.job_data.get("department_id")
        # if department_id_val is not None:
        #     self.department_id_edit.setText(str(department_id_val))
        #
        # created_by_val = self.job_data.get("created_by_user_id")
        # if created_by_val:
        #     self.created_by_user_id_edit.setText(str(created_by_val))


    def get_data(self) -> dict | None:
        """
        Retrieves the data from the form fields as a dictionary.
        Returns None if validation fails (though accept() handles this).
        """
        title = self.title_edit.text().strip()
        if not title:
            # This validation is now in validate_and_accept
            return None

        data = {
            "title": title,
            "description": self.description_edit.toPlainText().strip(),
            # "status_text": self.status_combo.currentText(), # Text like "Open" - No longer primary
            "status_id": self.status_map_display_to_id.get(self.status_combo.currentText()), # The mapped ID
            "closing_date": self.closing_date_edit.date().toString("yyyy-MM-dd"),
        }

        # Handle optional fields based on Pydantic models (JobOpeningCreate/Update)
        # department_id and created_by_user_id are not currently in the dialog form for simplicity
        # If they were, they would be added here:
        # dep_id_str = self.department_id_edit.text().strip()
        # if dep_id_str.isdigit():
        #    data["department_id"] = int(dep_id_str)
        # else:
        #    data["department_id"] = None # Or omit if API handles missing optional fields

        # For JobOpeningCreate, created_by_user_id is optional.
        # For JobOpeningUpdate, these are also optional.
        # The API models define what's required.
        # This dialog's get_data should align with JobOpeningCreate for new,
        # and JobOpeningUpdate for edits.
        # JobOpeningCreate requires: title. Optional: description, status_id, department_id, created_by_user_id, closing_date
        # JobOpeningUpdate allows all to be optional.

        # Ensure required fields for 'create' are present or have defaults if that's the mode.
        # For 'update', all fields are optional, so sending only changed ones is fine.
        # The current structure of get_data() provides all fields from the dialog.
        # The API Pydantic models will handle validation of required/optional fields.

        return data

    def validate_and_accept(self):
        """Validate input before accepting the dialog."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Input Error", "Title cannot be empty.")
            self.title_edit.setFocus()
            return

        # Add more validation as needed (e.g., closing date not in past for new openings)
        if not self.job_data: # Only for new openings
            if self.closing_date_edit.date() < QDate.currentDate():
                 QMessageBox.warning(self, "Input Error", "Closing date cannot be in the past for a new opening.")
                 self.closing_date_edit.setFocus()
                 return

        self.accept() # Proceed to accept the dialog


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test "Add" mode
    add_dialog = JobOpeningDialog()
    # add_dialog.setWindowTitle("Test Add Job Opening Dialog") # Already set internally
    if add_dialog.exec_():
        print("Add Dialog Accepted. Data:", add_dialog.get_data())
    else:
        print("Add Dialog Cancelled.")

    print("-" * 20)

    # Test "Edit" mode
    sample_edit_data_from_api = { # Simulating data structure from API (JobOpeningResponse)
        "job_opening_id": "uuid-test-123",
        "title": "Senior Python Developer",
        "description": "Seeking an experienced Python developer for backend systems.",
        "status_id": 1, # "Open"
        "closing_date": "2024-10-15",
        "department_id": 5, # Example
        "created_by_user_id": "user-xyz",
        "created_at": "2023-01-01T10:00:00Z", # Example
        "updated_at": "2023-01-05T12:00:00Z"  # Example
    }
    # The dialog's populate_form expects "status" as text if using the old way,
    # or "status_id" if using the new way for QComboBox.
    # Let's ensure populate_form uses status_id correctly.

    edit_dialog = JobOpeningDialog(job_data=sample_edit_data_from_api)
    if edit_dialog.exec_():
        print("Edit Dialog Accepted. Data:", edit_dialog.get_data())
    else:
        print("Edit Dialog Cancelled.")

    sys.exit(app.exec_())
```
