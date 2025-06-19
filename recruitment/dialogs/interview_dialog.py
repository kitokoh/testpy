from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QComboBox, QDialogButtonBox, QMessageBox, QTextEdit,
                             QDateTimeEdit, QSpinBox, QLabel)
from PyQt5.QtCore import Qt, QDateTime, QVariant
import requests
import json

API_BASE_URL = "http://localhost:8000/recruitment"

class InterviewDialog(QDialog):
    def __init__(self, interview_data: dict = None, parent=None, initial_job_id: str = None, initial_candidate_id: str = None):
        super().__init__(parent)

        self.interview_data = interview_data
        self.initial_job_id = initial_job_id
        self.initial_candidate_id = initial_candidate_id

        if self.interview_data:
            self.setWindowTitle("Edit Interview Details")
        else:
            self.setWindowTitle("Schedule New Interview")

        self.setMinimumWidth(500)

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.job_opening_combo = QComboBox()
        self.job_opening_combo.currentIndexChanged.connect(self.job_opening_selected)
        self.form_layout.addRow("Job Opening:", self.job_opening_combo)

        self.candidate_combo = QComboBox()
        self.form_layout.addRow("Candidate:", self.candidate_combo)

        self.interviewer_combo = QComboBox() # Placeholder for Team Members
        # TODO: Populate this from a Team Members API if available
        self.interviewer_combo.addItem("Select Interviewer (Optional)", userData=None)
        self.interviewer_combo.addItem("Interviewer ID 1 (Dummy)", userData=1)
        self.interviewer_combo.addItem("Interviewer ID 2 (Dummy)", userData=2)
        self.form_layout.addRow("Interviewer:", self.interviewer_combo)

        self.scheduled_at_edit = QDateTimeEdit()
        self.scheduled_at_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.scheduled_at_edit.setCalendarPopup(True)
        self.scheduled_at_edit.setDisplayFormat("yyyy-MM-dd hh:mm ap")
        self.form_layout.addRow("Scheduled At:", self.scheduled_at_edit)

        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(15, 240) # 15 mins to 4 hours
        self.duration_spinbox.setValue(60)
        self.duration_spinbox.setSuffix(" minutes")
        self.form_layout.addRow("Duration:", self.duration_spinbox)

        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("e.g., Phone Screen, Technical, Behavioral, On-site")
        self.form_layout.addRow("Interview Type:", self.type_edit)

        self.location_link_edit = QLineEdit()
        self.location_link_edit.setPlaceholderText("e.g., Room C1, Zoom link, Google Meet link")
        self.form_layout.addRow("Location/Link:", self.location_link_edit)

        self.status_combo = QComboBox()
        # TODO: Populate from StatusSettings API for 'InterviewStatus' type
        self.interview_statuses_map = {
            "Scheduled": 20, # Placeholder IDs
            "Completed": 21,
            "Cancelled": 22,
            "Rescheduled": 23,
            "No Show": 24
        }
        self.interview_status_id_to_display = {v:k for k,v in self.interview_statuses_map.items()}
        self.status_combo.addItems(self.interview_statuses_map.keys())
        self.form_layout.addRow("Status:", self.status_combo)

        self.feedback_edit = QTextEdit()
        self.feedback_edit.setPlaceholderText("Overall feedback, notes, assessment...")
        self.form_layout.addRow(QLabel("Feedback:"), self.feedback_edit) # Use QLabel for QTextEdit row

        self.feedback_rating_spinbox = QSpinBox()
        self.feedback_rating_spinbox.setRange(0, 5) # 0 for N/A or not rated, 1-5 for rating
        self.feedback_rating_spinbox.setSpecialValueText("N/A") # Display N/A for 0
        self.form_layout.addRow("Rating (1-5):", self.feedback_rating_spinbox)


        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.load_job_openings() # Initial data load

        if self.interview_data:
            self.populate_form(self.interview_data)
        elif self.initial_job_id: # If new interview, but job is pre-selected from widget filter
            self.select_combo_item_by_data(self.job_opening_combo, self.initial_job_id)
            if self.initial_candidate_id: # If candidate also pre-selected
                 # load_candidates_for_job would have been called by job_opening_selected signal
                 # Now we need to select the candidate
                 # This needs a slight delay or direct call if load_candidates_for_job is synchronous
                 self.select_combo_item_by_data(self.candidate_combo, self.initial_candidate_id)


    def load_job_openings(self):
        try:
            response = requests.get(f"{API_BASE_URL}/job-openings/?limit=500")
            response.raise_for_status()
            job_openings = response.json()

            self.job_opening_combo.blockSignals(True)
            self.job_opening_combo.clear()
            self.job_opening_combo.addItem("Select Job Opening...", userData=None)
            for jo in job_openings:
                self.job_opening_combo.addItem(f"{jo.get('title')} (ID: ...{jo.get('job_opening_id')[-6:]})", userData=jo.get("job_opening_id"))
            self.job_opening_combo.blockSignals(False)

            # If editing, or initial_job_id is set, try to select it
            if self.interview_data and self.interview_data.get("job_opening_id"):
                self.select_combo_item_by_data(self.job_opening_combo, self.interview_data.get("job_opening_id"))
            elif self.initial_job_id:
                 self.select_combo_item_by_data(self.job_opening_combo, self.initial_job_id)
            else: # Default to triggering candidate load for "Select Job..." or first item if that's not desired
                self.job_opening_selected()


        except requests.exceptions.RequestException as e:
            QMessageBox.warning(self, "API Error", f"Failed to load job openings: {e}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "API Error", "Failed to parse job openings for dialog.")


    def job_opening_selected(self):
        job_id = self.job_opening_combo.currentData()
        self.load_candidates_for_job(job_id)

    def load_candidates_for_job(self, job_id):
        self.candidate_combo.blockSignals(True)
        self.candidate_combo.clear()
        self.candidate_combo.addItem("Select Candidate...", userData=None)

        if job_id:
            try:
                response = requests.get(f"{API_BASE_URL}/job-openings/{job_id}/candidates/?limit=500")
                response.raise_for_status()
                candidates = response.json()
                for cand in candidates:
                    display_name = f"{cand.get('first_name')} {cand.get('last_name')} (ID: ...{cand.get('candidate_id')[-6:]})"
                    self.candidate_combo.addItem(display_name, userData=cand.get("candidate_id"))
            except requests.exceptions.RequestException as e:
                QMessageBox.warning(self, "API Error", f"Failed to load candidates for job {job_id}: {e}")
            except json.JSONDecodeError:
                QMessageBox.warning(self, "API Error", f"Failed to parse candidates for job {job_id}.")

        self.candidate_combo.blockSignals(False)
        # If editing, or initial_candidate_id is set for this job, try to select it
        if self.interview_data and self.interview_data.get("candidate_id") == self.candidate_combo.itemData(self.candidate_combo.findData(self.interview_data.get("candidate_id"))):
            self.select_combo_item_by_data(self.candidate_combo, self.interview_data.get("candidate_id"))
        elif self.initial_candidate_id and job_id == self.initial_job_id: # Ensure this candidate selection is for the right job
             self.select_combo_item_by_data(self.candidate_combo, self.initial_candidate_id)


    def load_interviewers(self):
        # Placeholder - In a real app, fetch from /team-members or similar
        # self.interviewer_combo.addItem("Interviewer 1", userData=1) # Example
        pass

    def populate_form(self, data):
        # Job opening and candidate selection is handled by load methods and initial_job/candidate_id

        interviewer_id = data.get("interviewer_team_member_id")
        if interviewer_id is not None:
            self.select_combo_item_by_data(self.interviewer_combo, interviewer_id)

        scheduled_at_str = data.get("scheduled_at")
        if scheduled_at_str:
            self.scheduled_at_edit.setDateTime(QDateTime.fromString(scheduled_at_str, Qt.ISODate)) # Assuming ISO format from API

        self.duration_spinbox.setValue(data.get("duration_minutes", 60))
        self.type_edit.setText(data.get("interview_type", ""))
        self.location_link_edit.setText(data.get("location_or_link", ""))

        status_id = data.get("status_id")
        if status_id is not None:
            status_display = self.interview_status_id_to_display.get(status_id)
            if status_display:
                self.status_combo.setCurrentText(status_display)
            else:
                 print(f"Warning: Interview status ID '{status_id}' not found in map during populate.")

        self.feedback_edit.setPlainText(data.get("feedback_notes_overall", ""))
        self.feedback_rating_spinbox.setValue(data.get("feedback_rating", 0))


    def get_data(self) -> dict | None:
        job_id = self.job_opening_combo.currentData()
        cand_id = self.candidate_combo.currentData()

        # Validation is now in validate_and_accept
        data = {
            "job_opening_id": job_id,
            "candidate_id": cand_id,
            "interviewer_team_member_id": self.interviewer_combo.currentData(),
            "scheduled_at": self.scheduled_at_edit.dateTime().toString(Qt.ISODate), # Send in ISO format
            "duration_minutes": self.duration_spinbox.value(),
            "interview_type": self.type_edit.text().strip() or None,
            "location_or_link": self.location_link_edit.text().strip() or None,
            "status_id": self.interview_statuses_map.get(self.status_combo.currentText()),
            "feedback_notes_overall": self.feedback_edit.toPlainText().strip() or None,
        }
        # Only include rating if it's not 0 (N/A)
        rating = self.feedback_rating_spinbox.value()
        if rating > 0:
            data["feedback_rating"] = rating
        else:
            data["feedback_rating"] = None # Or omit if API prefers that for nulls

        return data

    def select_combo_item_by_data(self, combo: QComboBox, data_to_select):
        if data_to_select is None: return
        for i in range(combo.count()):
            if combo.itemData(i) == data_to_select:
                combo.setCurrentIndex(i)
                return
        print(f"Warning: Could not find data '{data_to_select}' in {combo.objectName() if combo.objectName() else 'QComboBox'}.")


    def validate_and_accept(self):
        job_id = self.job_opening_combo.currentData()
        cand_id = self.candidate_combo.currentData()

        if not job_id:
            QMessageBox.warning(self, "Input Error", "Please select a Job Opening.")
            self.job_opening_combo.setFocus()
            return
        if not cand_id:
            QMessageBox.warning(self, "Input Error", "Please select a Candidate.")
            self.candidate_combo.setFocus()
            return

        # Add other critical validations if necessary
        self.accept()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test "Add" mode
    print("Testing Add Interview Dialog (ensure API is running for Job/Candidate combos)")
    add_dialog = InterviewDialog(initial_job_id="job-uuid-abc", initial_candidate_id="cand-uuid-123") # Example pre-selection
    if add_dialog.exec_():
        print("Add Interview Dialog Accepted. Data:", add_dialog.get_data())
    else:
        print("Add Interview Dialog Cancelled.")

    print("-" * 20)

    sample_interview = {
        "interview_id": "int-uuid-789",
        "candidate_id": "cand-uuid-123", # Should exist in candidate_combo for selected job
        "job_opening_id": "job-uuid-abc", # Should exist in job_opening_combo
        "recruitment_step_id": "step-uuid-def", # Optional
        "interviewer_team_member_id": 1, # Dummy ID
        "scheduled_at": "2024-08-15T14:30:00", # ISO format
        "duration_minutes": 45,
        "interview_type": "Technical Screen",
        "location_or_link": "Zoom Link XYZ",
        "status_id": 20, # "Scheduled"
        "feedback_notes_overall": "Initial discussion, seems promising.",
        "feedback_rating": 0 # N/A
    }
    print("Testing Edit Interview Dialog (ensure API is running for Job/Candidate combos)")
    edit_dialog = InterviewDialog(interview_data=sample_interview)
    if edit_dialog.exec_():
        print("Edit Interview Dialog Accepted. Data:", edit_dialog.get_data())
    else:
        print("Edit Interview Dialog Cancelled.")

    sys.exit(app.exec_())
```
