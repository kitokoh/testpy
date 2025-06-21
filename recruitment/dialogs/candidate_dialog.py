from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QComboBox, QDialogButtonBox, QMessageBox, QTextEdit, QLabel)
from PyQt5.QtCore import Qt, QVariant
import requests
import json

# API_BASE_URL = "http://localhost:8000/api/v1/recruitment" # Match your actual API prefix
API_BASE_URL = "http://localhost:8000/recruitment" # As defined in previous API structure

class CandidateDialog(QDialog):
    def __init__(self, candidate_data: dict = None, parent=None):
        super().__init__(parent)

        self.candidate_data = candidate_data

        if self.candidate_data:
            self.setWindowTitle("Edit Candidate Details")
        else:
            self.setWindowTitle("Add New Candidate")

        self.setMinimumWidth(450)

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.first_name_edit = QLineEdit()
        self.form_layout.addRow("First Name:", self.first_name_edit)

        self.last_name_edit = QLineEdit()
        self.form_layout.addRow("Last Name:", self.last_name_edit)

        self.email_edit = QLineEdit()
        self.form_layout.addRow("Email:", self.email_edit)

        self.phone_edit = QLineEdit()
        self.form_layout.addRow("Phone:", self.phone_edit)

        self.resume_path_edit = QLineEdit()
        self.resume_path_edit.setPlaceholderText("(Optional) Path or URL to resume")
        self.form_layout.addRow("Resume Path:", self.resume_path_edit)

        # In a more advanced version, this could be a file chooser
        # self.cover_letter_path_edit = QLineEdit()
        # self.cover_letter_path_edit.setPlaceholderText("(Optional) Path or URL to cover letter")
        # self.form_layout.addRow("Cover Letter Path:", self.cover_letter_path_edit)

        self.application_source_edit = QLineEdit()
        self.application_source_edit.setPlaceholderText("e.g., LinkedIn, Referral, Website")
        self.form_layout.addRow("Application Source:", self.application_source_edit)

        self.job_opening_combo = QComboBox()
        self.form_layout.addRow("Job Opening:", self.job_opening_combo)

        self.status_combo = QComboBox()
        # TODO: Populate statuses dynamically from API (StatusSettings for 'CandidateApplication' type)
        self.candidate_statuses_map = {
            "Applied": 10, # Placeholder IDs, should match DB
            "Screening": 11,
            "Interviewing": 12,
            "Offer Extended": 13,
            "Hired": 14,
            "Rejected": 15,
        }
        self.candidate_status_id_to_display = {v:k for k,v in self.candidate_statuses_map.items()}
        self.status_combo.addItems(self.candidate_statuses_map.keys())
        self.form_layout.addRow("Current Status:", self.status_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Additional notes about the candidate...")
        self.form_layout.addRow(QLabel("Notes:"), self.notes_edit) # Use QLabel for QTextEdit row

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.load_job_openings_into_combo() # Load JDs into ComboBox

        if self.candidate_data:
            self.populate_form(self.candidate_data)

    def load_job_openings_into_combo(self):
        try:
            response = requests.get(f"{API_BASE_URL}/job-openings/?limit=500")
            response.raise_for_status()
            job_openings = response.json()

            self.job_opening_combo.blockSignals(True)
            self.job_opening_combo.clear()
            if not self.candidate_data: # For new candidate, give a prompt
                 self.job_opening_combo.addItem("Select Job Opening...", userData=None)

            for jo in job_openings:
                self.job_opening_combo.addItem(jo.get("title"), userData=jo.get("job_opening_id"))
            self.job_opening_combo.blockSignals(False)

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load job openings for dialog: {e}")
            self.job_opening_combo.blockSignals(False)
        except json.JSONDecodeError:
             QMessageBox.critical(self, "API Error", f"Failed to parse job openings for dialog.")
             self.job_opening_combo.blockSignals(False)


    def populate_form(self, data):
        self.first_name_edit.setText(data.get("first_name", ""))
        self.last_name_edit.setText(data.get("last_name", ""))
        self.email_edit.setText(data.get("email", ""))
        self.phone_edit.setText(data.get("phone", ""))
        self.resume_path_edit.setText(data.get("resume_path", ""))
        # self.cover_letter_path_edit.setText(data.get("cover_letter_path", ""))
        self.application_source_edit.setText(data.get("application_source", ""))
        self.notes_edit.setPlainText(data.get("notes", ""))

        # Set Job Opening in ComboBox
        job_id = data.get("job_opening_id")
        if job_id:
            for i in range(self.job_opening_combo.count()):
                if self.job_opening_combo.itemData(i) == job_id:
                    self.job_opening_combo.setCurrentIndex(i)
                    break

        # Set Status in ComboBox
        status_id = data.get("current_status_id")
        if status_id is not None:
            status_display = self.candidate_status_id_to_display.get(status_id)
            if status_display:
                 index = self.status_combo.findText(status_display, Qt.MatchFixedString)
                 if index >= 0:
                    self.status_combo.setCurrentIndex(index)
            else:
                print(f"Warning: Candidate status ID '{status_id}' not found in map.")


    def get_data(self) -> dict | None:
        """Returns form data as a dictionary, or None if validation fails."""
        # Validation is now in validate_and_accept
        data = {
            "first_name": self.first_name_edit.text().strip(),
            "last_name": self.last_name_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "phone": self.phone_edit.text().strip() or None,
            "resume_path": self.resume_path_edit.text().strip() or None,
            # "cover_letter_path": self.cover_letter_path_edit.text().strip() or None,
            "application_source": self.application_source_edit.text().strip() or None,
            "job_opening_id": self.job_opening_combo.currentData(),
            "current_status_id": self.candidate_statuses_map.get(self.status_combo.currentText()),
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
        return data

    def validate_and_accept(self):
        first_name = self.first_name_edit.text().strip()
        last_name = self.last_name_edit.text().strip()
        email = self.email_edit.text().strip()
        job_opening_id = self.job_opening_combo.currentData()

        if not all([first_name, last_name, email]):
            QMessageBox.warning(self, "Input Error", "First Name, Last Name, and Email are required.")
            return

        if not job_opening_id and self.job_opening_combo.currentIndex() == 0 and not self.candidate_data : # If "Select Job Opening..." is chosen for a new candidate
             QMessageBox.warning(self, "Input Error", "Please select a Job Opening for the new candidate.")
             return

        # Further email validation could be done using regex if needed, but FastAPI model handles it.
        self.accept()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test "Add" mode
    add_dialog = CandidateDialog()
    if add_dialog.exec_():
        print("Add Candidate Dialog Accepted. Data:", add_dialog.get_data())
    else:
        print("Add Candidate Dialog Cancelled.")

    print("-" * 20)

    # Test "Edit" mode - Simulating candidate_data that would come from API
    sample_candidate = {
        "candidate_id": "cand-uuid-123",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "phone": "555-1234",
        "resume_path": "/resumes/jane_doe.pdf",
        "application_source": "Referral",
        "job_opening_id": "job-uuid-abc", # This ID should exist in the job_opening_combo after load
        "current_status_id": 11, # "Screening"
        "notes": "Strong referral from existing employee."
    }
    # To test edit mode properly, job_opening_combo needs to be populated
    # and sample_candidate.job_opening_id should match one of the userDatas.
    # The load_job_openings_into_combo is called in __init__.
    # If the API is not running, this combo will be empty.

    print("Testing Edit Dialog. Ensure API is running for Job Openings to populate combo.")
    edit_dialog = CandidateDialog(candidate_data=sample_candidate)
    if edit_dialog.exec_():
        print("Edit Candidate Dialog Accepted. Data:", edit_dialog.get_data())
    else:
        print("Edit Candidate Dialog Cancelled.")

    sys.exit(app.exec_())
```
