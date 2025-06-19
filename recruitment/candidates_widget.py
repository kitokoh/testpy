from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QComboBox, QLabel, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt, QVariant
import requests
import json

# API_BASE_URL = "http://localhost:8000/api/v1/recruitment" # Match your actual API prefix
API_BASE_URL = "http://localhost:8000/recruitment" # As defined in previous API structure

class CandidatesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)

        # Filter layout
        self.filter_layout = QHBoxLayout()
        self.filter_layout.addWidget(QLabel("Filter by Job Opening:"))
        self.job_filter_combo = QComboBox()
        self.job_filter_combo.setMinimumWidth(250)
        self.job_filter_combo.currentIndexChanged.connect(self.load_candidates)
        self.filter_layout.addWidget(self.job_filter_combo)
        self.filter_layout.addStretch()
        self.main_layout.addLayout(self.filter_layout)

        # Action buttons layout
        self.actions_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Candidate")
        self.add_button.clicked.connect(self.open_add_candidate_dialog)
        self.edit_button = QPushButton("View/Edit Details")
        self.edit_button.clicked.connect(self.open_edit_candidate_dialog)
        self.delete_button = QPushButton("Delete Candidate")
        self.delete_button.clicked.connect(self.delete_selected_candidate)

        self.actions_layout.addWidget(self.add_button)
        self.actions_layout.addWidget(self.edit_button)
        self.actions_layout.addWidget(self.delete_button)
        self.actions_layout.addStretch()
        self.main_layout.addLayout(self.actions_layout)

        # Table for candidates
        self.candidates_table = QTableWidget()
        self.candidates_table.setColumnCount(7)
        self.candidates_table.setHorizontalHeaderLabels([
            "First Name", "Last Name", "Email", "Phone",
            "Status ID", "Job Opening ID", "Candidate ID (Hidden)"
        ])
        self.candidates_table.setColumnHidden(6, True) # Hide the Candidate ID column

        self.candidates_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidates_table.setSelectionMode(QTableWidget.SingleSelection)
        self.candidates_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.candidates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.candidates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.candidates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.candidates_table.verticalHeader().setVisible(False)

        self.candidates_table.selectionModel().selectionChanged.connect(self.update_action_buttons_state)
        self.main_layout.addWidget(self.candidates_table)
        self.setLayout(self.main_layout)

        self.update_action_buttons_state()
        self.load_job_openings_into_filter() # This will trigger load_candidates via currentIndexChanged

    def load_job_openings_into_filter(self):
        try:
            response = requests.get(f"{API_BASE_URL}/job-openings/?limit=500") # Get a good number of openings
            response.raise_for_status()
            job_openings = response.json()

            self.job_filter_combo.blockSignals(True) # Block signals during population
            self.job_filter_combo.clear()
            self.job_filter_combo.addItem("All Candidates", userData=None) # Option for all
            for jo in job_openings:
                self.job_filter_combo.addItem(jo.get("title"), userData=jo.get("job_opening_id"))
            self.job_filter_combo.blockSignals(False)

            # Trigger load_candidates for the initially selected item (usually "All Candidates")
            # or the first job opening if "All Candidates" is not desired as default.
            self.job_filter_combo.setCurrentIndex(0) # Set to "All Candidates"
            self.load_candidates() # Manually call after populating and setting index if needed

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load job openings for filter: {e}")
            self.job_filter_combo.blockSignals(False) # Ensure signals unblocked on error
        except json.JSONDecodeError:
            QMessageBox.critical(self, "API Error", "Failed to parse job openings list from server.")
            self.job_filter_combo.blockSignals(False)


    def load_candidates(self):
        self.candidates_table.setRowCount(0)
        selected_job_id = self.job_filter_combo.currentData()

        url = ""
        if selected_job_id:
            url = f"{API_BASE_URL}/job-openings/{selected_job_id}/candidates/"
        else: # "All Candidates"
            url = f"{API_BASE_URL}/candidates/"

        try:
            response = requests.get(url)
            response.raise_for_status()
            candidates = response.json()

            for row_num, cand_data in enumerate(candidates):
                self.candidates_table.insertRow(row_num)

                fn_item = QTableWidgetItem(cand_data.get("first_name"))
                # Store full candidate data in the first item's UserRole for easy access
                fn_item.setData(Qt.UserRole, cand_data)

                self.candidates_table.setItem(row_num, 0, fn_item)
                self.candidates_table.setItem(row_num, 1, QTableWidgetItem(cand_data.get("last_name")))
                self.candidates_table.setItem(row_num, 2, QTableWidgetItem(cand_data.get("email")))
                self.candidates_table.setItem(row_num, 3, QTableWidgetItem(cand_data.get("phone", "")))
                self.candidates_table.setItem(row_num, 4, QTableWidgetItem(str(cand_data.get("current_status_id", ""))))
                self.candidates_table.setItem(row_num, 5, QTableWidgetItem(cand_data.get("job_opening_id")))
                # Store candidate_id in a hidden column for direct access if UserRole method is not preferred for ID
                self.candidates_table.setItem(row_num, 6, QTableWidgetItem(cand_data.get("candidate_id")))

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "API Error", f"Failed to load candidates: {e}")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "API Error", "Failed to parse candidates data from server.")
        self.update_action_buttons_state()


    def get_selected_candidate_data(self) -> dict | None:
        selected_items = self.candidates_table.selectedItems()
        if not selected_items:
            return None

        first_item_in_row = self.candidates_table.item(selected_items[0].row(), 0)
        if first_item_in_row:
            return first_item_in_row.data(Qt.UserRole) # Retrieve the full dict
        return None

    def open_add_candidate_dialog(self):
        # Placeholder - Actual implementation will involve CandidateDialog
        from .dialogs.candidate_dialog import CandidateDialog # Assuming this will be created
        dialog = CandidateDialog(parent=self) # No candidate_data for add mode
        if dialog.exec_():
            data_to_submit = dialog.get_data()
            if data_to_submit:
                try:
                    response = requests.post(f"{API_BASE_URL}/candidates/", json=data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Add Candidate", "Candidate added successfully.")
                    self.load_candidates() # Refresh
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to add candidate: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to add candidate: {e}")
        QMessageBox.information(self, "Add Candidate", "Placeholder: Open Add Candidate Dialog.")


    def open_edit_candidate_dialog(self):
        selected_candidate = self.get_selected_candidate_data()
        if not selected_candidate:
            QMessageBox.warning(self, "Edit Candidate", "Please select a candidate to edit.")
            return

        from .dialogs.candidate_dialog import CandidateDialog # Assuming this will be created
        dialog = CandidateDialog(candidate_data=selected_candidate, parent=self)
        if dialog.exec_():
            data_to_submit = dialog.get_data()
            if data_to_submit:
                candidate_id = selected_candidate.get("candidate_id")
                try:
                    response = requests.put(f"{API_BASE_URL}/candidates/{candidate_id}", json=data_to_submit)
                    response.raise_for_status()
                    QMessageBox.information(self, "Edit Candidate", "Candidate updated successfully.")
                    self.load_candidates() # Refresh
                except requests.exceptions.HTTPError as e:
                    error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                    QMessageBox.critical(self, "API Error", f"Failed to update candidate: {error_detail}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "API Error", f"Failed to update candidate: {e}")
        QMessageBox.information(self, "Edit Candidate", f"Placeholder: Open Edit Candidate Dialog for {selected_candidate.get('first_name')}.")

    def delete_selected_candidate(self):
        selected_candidate = self.get_selected_candidate_data()
        if not selected_candidate:
            QMessageBox.warning(self, "Delete Candidate", "Please select a candidate to delete.")
            return

        candidate_id = selected_candidate.get("candidate_id")
        candidate_name = f"{selected_candidate.get('first_name')} {selected_candidate.get('last_name')}"

        reply = QMessageBox.question(self, "Delete Candidate",
                                     f"Are you sure you want to delete {candidate_name} (ID: {candidate_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                response = requests.delete(f"{API_BASE_URL}/candidates/{candidate_id}")
                response.raise_for_status()
                QMessageBox.information(self, "Delete Candidate", f"{candidate_name} deleted successfully.")
                self.load_candidates() # Refresh
            except requests.exceptions.HTTPError as e:
                error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
                QMessageBox.critical(self, "API Error", f"Failed to delete candidate: {error_detail}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "API Error", f"Failed to delete candidate: {e}")
        QMessageBox.information(self, "Delete Candidate", f"Placeholder: Delete candidate {selected_candidate.get('first_name')}.")


    def update_action_buttons_state(self):
        has_selection = bool(self.candidates_table.selectedItems())
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # Need to ensure dialogs.candidate_dialog exists for dynamic imports in methods
    # For testing this widget standalone, you might need to create a dummy CandidateDialog
    # or ensure the path is set up correctly.
    # For now, button clicks will attempt to import it.

    # Dummy CandidateDialog for basic __main__ test run if the actual file isn't there yet
    try:
        from .dialogs.candidate_dialog import CandidateDialog
    except ImportError:
        print("Warning: recruitment.dialogs.candidate_dialog not found. Using Dummy for __main__.")
        class CandidateDialog(QWidget): # QDialog would be better
            def __init__(self, candidate_data=None, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Dummy Candidate Dialog")
                layout = QVBoxLayout(self)
                self.data_label = QLabel("Candidate Dialog (Simulated)")
                if candidate_data:
                    self.data_label.setText(f"Editing: {candidate_data.get('first_name')}")
                layout.addWidget(self.data_label)
                self.ok_button = QPushButton("OK")
                # self.ok_button.clicked.connect(self.accept) # QDialog has accept/reject
                layout.addWidget(self.ok_button)
                self._candidate_data = candidate_data or {}
                self._accepted = False

            def exec_(self): # Simulate QDialog.exec_
                # self.show() # Non-modal for this dummy
                # This dummy needs a way to simulate modal behavior and return Accepted/Rejected
                # For now, just return 1 to simulate accepted for testing flow.
                # In a real test, you'd interact with the dialog.
                return 1 # Simulate QDialog.Accepted

            def get_data(self):
                return {"first_name": "Test", "last_name": "User", "email": "test@example.com", "job_opening_id": "dummy_job_id"}


    widget = CandidatesWidget()
    widget.setWindowTitle("Candidates Management Test")
    widget.resize(1200, 700)
    widget.show()
    sys.exit(app.exec_())
# ```
