from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QComboBox, QLabel, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt, QVariant
import requests
import json

API_BASE_URL = "http://localhost:8000/recruitment"

class InterviewsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)

        # Filter layout
        self.filter_layout = QHBoxLayout()
        self.filter_layout.addWidget(QLabel("Filter by Job Opening:"))
        self.job_filter_combo = QComboBox()
        self.job_filter_combo.setMinimumWidth(200)
        self.job_filter_combo.currentIndexChanged.connect(self.job_filter_changed)
        self.filter_layout.addWidget(self.job_filter_combo)

        self.filter_layout.addWidget(QLabel("Candidate:"))
        self.candidate_filter_combo = QComboBox()
        self.candidate_filter_combo.setMinimumWidth(200)
        self.candidate_filter_combo.currentIndexChanged.connect(self.load_interviews) # Load interviews when candidate changes
        self.filter_layout.addWidget(self.candidate_filter_combo)
        self.filter_layout.addStretch()
        self.main_layout.addLayout(self.filter_layout)

        # Action buttons layout
        self.actions_layout = QHBoxLayout()
        self.schedule_button = QPushButton("Schedule Interview")
        self.schedule_button.clicked.connect(self.open_schedule_interview_dialog)
        self.edit_button = QPushButton("View/Edit Details")
        self.edit_button.clicked.connect(self.open_edit_interview_dialog)
        self.cancel_interview_button = QPushButton("Cancel Interview")
        self.cancel_interview_button.clicked.connect(self.cancel_selected_interview)

        self.actions_layout.addWidget(self.schedule_button)
        self.actions_layout.addWidget(self.edit_button)
        self.actions_layout.addWidget(self.cancel_interview_button)
        self.actions_layout.addStretch()
        self.main_layout.addLayout(self.actions_layout)

        # Table for interviews
        self.interviews_table = QTableWidget()
        self.interviews_table.setColumnCount(7) # interview_id, candidate_name, job_title, interviewer, scheduled_at, type, status
        self.interviews_table.setHorizontalHeaderLabels([
            "Interview ID", "Candidate", "Job Opening",
            "Interviewer ID", "Scheduled At", "Type", "Status ID"
        ])
        # self.interviews_table.setColumnHidden(0, True) # Optionally hide ID if preferred

        self.interviews_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.interviews_table.setSelectionMode(QTableWidget.SingleSelection)
        self.interviews_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.interviews_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.interviews_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive) # Candidate
        self.interviews_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive) # Job Opening
        self.interviews_table.verticalHeader().setVisible(False)

        self.interviews_table.selectionModel().selectionChanged.connect(self.update_action_buttons_state)
        self.main_layout.addWidget(self.interviews_table)
        self.setLayout(self.main_layout)

        self.update_action_buttons_state()
        self.load_job_openings_filter() # Initial load

    def job_filter_changed(self):
        self.load_candidates_filter()
        # load_interviews will be called by candidate_filter_combo.currentIndexChanged or manually if needed
        # If "All Jobs" is selected, candidate filter is cleared, then interviews for "All Jobs, All Candidates" loaded.

    def load_job_openings_filter(self):
        try:
            response = requests.get(f"{API_BASE_URL}/job-openings/?limit=500")
            response.raise_for_status()
            job_openings = response.json()

            self.job_filter_combo.blockSignals(True)
            self.job_filter_combo.clear()
            self.job_filter_combo.addItem("All Job Openings", userData=None)
            for jo in job_openings:
                self.job_filter_combo.addItem(jo.get("title"), userData=jo.get("job_opening_id"))
            self.job_filter_combo.blockSignals(False)
            self.job_filter_combo.setCurrentIndex(0) # Trigger candidate load & interview load for "All"

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load job openings for filter: {e}")
            self.job_filter_combo.blockSignals(False)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "API Error", "Failed to parse job openings list for filter.")
            self.job_filter_combo.blockSignals(False)
        # Manually trigger the first load sequence
        self.job_filter_changed()


    def load_candidates_filter(self):
        selected_job_id = self.job_filter_combo.currentData()
        self.candidate_filter_combo.blockSignals(True)
        self.candidate_filter_combo.clear()
        self.candidate_filter_combo.addItem("All Candidates", userData=None)

        if selected_job_id: # A specific job opening is selected
            try:
                response = requests.get(f"{API_BASE_URL}/job-openings/{selected_job_id}/candidates/?limit=500")
                response.raise_for_status()
                candidates = response.json()
                for cand in candidates:
                    display_name = f"{cand.get('first_name')} {cand.get('last_name')} ({cand.get('email')})"
                    self.candidate_filter_combo.addItem(display_name, userData=cand.get("candidate_id"))
            except requests.exceptions.RequestException as e:
                QMessageBox.warning(self, "API Error", f"Failed to load candidates for job opening {selected_job_id}: {e}")
            except json.JSONDecodeError:
                 QMessageBox.warning(self, "API Error", f"Failed to parse candidates for job {selected_job_id}.")

        self.candidate_filter_combo.blockSignals(False)
        self.candidate_filter_combo.setCurrentIndex(0) # Default to "All Candidates" for the selected job
        self.load_interviews() # Load interviews based on new candidate filter (which might be "All Candidates")

    def load_interviews(self):
        self.interviews_table.setRowCount(0)
        job_id = self.job_filter_combo.currentData()
        candidate_id = self.candidate_filter_combo.currentData()

        params = {}
        if job_id:
            params["job_opening_id"] = job_id
        if candidate_id:
            params["candidate_id"] = candidate_id

        try:
            # The API endpoint for interviews GET /interviews/ should support filtering via query params
            response = requests.get(f"{API_BASE_URL}/interviews/", params=params)
            response.raise_for_status()
            interviews = response.json()

            for row_num, interview_data in enumerate(interviews):
                self.interviews_table.insertRow(row_num)

                id_item = QTableWidgetItem(interview_data.get("interview_id"))
                id_item.setData(Qt.UserRole, interview_data) # Store full data
                self.interviews_table.setItem(row_num, 0, id_item)

                # For display, it's better to fetch candidate/job names, but API returns IDs.
                # This requires either:
                # 1. API to return nested objects with names (e.g. candidate.first_name)
                # 2. Frontend to make additional calls or have cached data to map IDs to names.
                # For now, we'll display IDs or make placeholder text.
                self.interviews_table.setItem(row_num, 1, QTableWidgetItem(f"Cand: {interview_data.get('candidate_id')[:8]}..."))
                self.interviews_table.setItem(row_num, 2, QTableWidgetItem(f"Job: {interview_data.get('job_opening_id')[:8]}..."))
                self.interviews_table.setItem(row_num, 3, QTableWidgetItem(str(interview_data.get("interviewer_team_member_id", "N/A"))))
                self.interviews_table.setItem(row_num, 4, QTableWidgetItem(interview_data.get("scheduled_at", "")))
                self.interviews_table.setItem(row_num, 5, QTableWidgetItem(interview_data.get("interview_type", "")))
                self.interviews_table.setItem(row_num, 6, QTableWidgetItem(str(interview_data.get("status_id", ""))))

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load interviews: {e}")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "API Error", "Failed to parse interviews data from server.")
        self.update_action_buttons_state()

    def get_selected_interview_data(self) -> dict | None:
        selected_items = self.interviews_table.selectedItems()
        if not selected_items: return None
        # Assuming ID is in the first column and data in its UserRole
        first_item = self.interviews_table.item(selected_items[0].row(), 0)
        return first_item.data(Qt.UserRole) if first_item else None

    def open_schedule_interview_dialog(self):
        from .dialogs.interview_dialog import InterviewDialog # Assuming this will be created

        # Pass current filter selections to the dialog if useful
        current_job_id = self.job_filter_combo.currentData()
        current_candidate_id = self.candidate_filter_combo.currentData()

        dialog = InterviewDialog(parent=self, initial_job_id=current_job_id, initial_candidate_id=current_candidate_id)
        if dialog.exec_():
            data_to_submit = dialog.get_data()
            if data_to_submit:
                try:
                    response = requests.post(f"{API_BASE_URL}/interviews/", json=data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Schedule Interview", "Interview scheduled successfully.")
                    self.load_interviews() # Refresh
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to schedule interview: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to schedule interview: {e}")


    def open_edit_interview_dialog(self):
        selected_interview = self.get_selected_interview_data()
        if not selected_interview:
            QMessageBox.warning(self, "Edit Interview", "Please select an interview to edit.")
            return

        from .dialogs.interview_dialog import InterviewDialog
        dialog = InterviewDialog(interview_data=selected_interview, parent=self)
        if dialog.exec_():
            data_to_submit = dialog.get_data()
            if data_to_submit:
                interview_id = selected_interview.get("interview_id")
                try:
                    response = requests.put(f"{API_BASE_URL}/interviews/{interview_id}", json=data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Edit Interview", "Interview updated successfully.")
                    self.load_interviews() # Refresh
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to update interview: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to update interview: {e}")


    def cancel_selected_interview(self):
        # Note: "Cancel" usually means updating status. "Delete" means removing the record.
        # This method implements DELETE. If "Cancel" means updating status, a different method/dialog is needed.
        selected_interview = self.get_selected_interview_data()
        if not selected_interview:
            QMessageBox.warning(self, "Delete Interview", "Please select an interview to delete.")
            return

        interview_id = selected_interview.get("interview_id")
        scheduled_time = selected_interview.get("scheduled_at", "this interview")

        reply = QMessageBox.question(self, "Delete Interview",
                                     f"Are you sure you want to delete the interview scheduled for {scheduled_time} (ID: {interview_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                response = requests.delete(f"{API_BASE_URL}/interviews/{interview_id}")
                response.raise_for_status()
                QMessageBox.information(self, "Delete Interview", "Interview record deleted successfully.")
                self.load_interviews() # Refresh
            except requests.exceptions.HTTPError as e:
                error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                QMessageBox.critical(self, "API Error", f"Failed to delete interview: {error_detail}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "API Error", f"Failed to delete interview: {e}")

    def update_action_buttons_state(self):
        has_selection = bool(self.interviews_table.selectedItems())
        self.edit_button.setEnabled(has_selection)
        self.cancel_interview_button.setEnabled(has_selection) # Renamed from delete_button

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # Dummy InterviewDialog for basic __main__ test run
    try:
        from .dialogs.interview_dialog import InterviewDialog
    except ImportError:
        print("Warning: recruitment.dialogs.interview_dialog not found. Using Dummy for __main__.")
        class InterviewDialog(QWidget): # QDialog would be better
            def __init__(self, interview_data=None, parent=None, initial_job_id=None, initial_candidate_id=None):
                super().__init__(parent)
                self.setWindowTitle("Dummy Interview Dialog")
                layout = QVBoxLayout(self); self.setLayout(layout)
                label_text = "Interview Dialog (Simulated)"
                if interview_data: label_text += f" for editing ID: {interview_data.get('interview_id')}"
                elif initial_job_id or initial_candidate_id: label_text += f" for Job: {initial_job_id}, Cand: {initial_candidate_id}"
                layout.addWidget(QLabel(label_text))
                self._interview_data = interview_data or {}
            def exec_(self): return 0 # Simulate cancel
            def get_data(self): return {"candidate_id": "dummy_cand_id", "job_opening_id": "dummy_job_id", "scheduled_at": "2025-01-01T10:00:00"}

    widget = InterviewsWidget()
    widget.setWindowTitle("Interviews Management Test")
    widget.resize(1200, 700)
    widget.show()
    sys.exit(app.exec_())
# ```
