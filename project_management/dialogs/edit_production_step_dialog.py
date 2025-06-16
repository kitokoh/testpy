from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
                             QDateEdit, QDoubleSpinBox, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import QTimer, QDate, Qt # Qt might not be directly used, but QDate is.
from datetime import datetime

from db import (
    get_task_by_id,
    get_all_status_settings,
    get_status_setting_by_id,
    get_all_team_members,
    update_task
)

class EditProductionStepDialog(QDialog):
    def __init__(self, task_id, parent_dialog): # parent_dialog is EditProductionOrderDialog
        super().__init__(parent_dialog)
        self.task_id = task_id
        # Store parent_dialog to access MainDashboard instance later for logging
        self.parent_dialog = parent_dialog
        self.setWindowTitle(f"Edit Production Step (ID: {self.task_id})")
        self.setMinimumWidth(450)

        self.task_data = get_task_by_id(self.task_id)
        if not self.task_data:
            QMessageBox.critical(self, "Error", "Could not load task data for editing.")
            QTimer.singleShot(0, self.reject) # Close if data fails to load
            return

        self.layout = QFormLayout(self)
        self.layout.setSpacing(10)

        self.step_name_edit = QLineEdit(self.task_data.get('task_name', ''))
        self.description_edit = QTextEdit(self.task_data.get('description', ''))
        self.description_edit.setFixedHeight(80)

        self.status_combo = QComboBox()
        task_statuses = get_all_status_settings(type_filter='Task')
        current_status_id = self.task_data.get('status_id')
        if task_statuses:
            for idx, ts in enumerate(task_statuses):
                self.status_combo.addItem(ts['status_name'], ts['status_id'])
                if ts['status_id'] == current_status_id:
                    self.status_combo.setCurrentIndex(idx)
        elif current_status_id: # Fallback if task_statuses is empty but current_status_id exists
            status_obj = get_status_setting_by_id(current_status_id)
            if status_obj: self.status_combo.addItem(status_obj['status_name'], status_obj['status_id'])

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"]) # 0, 1, 2
        self.priority_combo.setCurrentIndex(self.task_data.get('priority', 1)) # Default to Medium if not set

        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("Unassigned", None)
        team_members = get_all_team_members(filters={'is_active': True})
        current_assignee_id = self.task_data.get('assignee_team_member_id')
        if team_members:
            for idx, tm in enumerate(team_members):
                self.assignee_combo.addItem(tm['full_name'], tm['team_member_id'])
                if tm['team_member_id'] == current_assignee_id:
                    self.assignee_combo.setCurrentIndex(idx + 1) # +1 due to "Unassigned"

        due_date_str = self.task_data.get('due_date', '')
        self.due_date_edit = QDateEdit(QDate.fromString(due_date_str, "yyyy-MM-dd") if due_date_str else QDate.currentDate())
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")

        self.est_duration_spin = QDoubleSpinBox()
        self.est_duration_spin.setRange(0, 9999.99)
        self.est_duration_spin.setSuffix(" hours")
        self.est_duration_spin.setValue(self.task_data.get('estimated_duration_hours', 0.0))

        self.layout.addRow("Step Name*:", self.step_name_edit)
        self.layout.addRow("Description:", self.description_edit)
        self.layout.addRow("Status:", self.status_combo)
        self.layout.addRow("Priority:", self.priority_combo)
        self.layout.addRow("Assignee:", self.assignee_combo)
        self.layout.addRow("Due Date:", self.due_date_edit)
        self.layout.addRow("Est. Duration:", self.est_duration_spin)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_save_step)
        self.button_box.rejected.connect(self.reject)
        self.layout.addRow(self.button_box)

    def on_save_step(self):
        step_name = self.step_name_edit.text().strip()
        if not step_name:
            QMessageBox.warning(self, "Input Error", "Step name cannot be empty.")
            return

        updated_data = {
            'task_name': step_name,
            'description': self.description_edit.toPlainText().strip(),
            'status_id': self.status_combo.currentData(),
            'priority': self.priority_combo.currentIndex(),
            'assignee_team_member_id': self.assignee_combo.currentData(),
            'due_date': self.due_date_edit.date().toString("yyyy-MM-dd") if self.due_date_edit.date().isValid() else None,
            'estimated_duration_hours': self.est_duration_spin.value()
        }

        selected_status_id = self.status_combo.currentData()
        if selected_status_id:
            status_details = get_status_setting_by_id(selected_status_id)
            if status_details and status_details.get('is_completion_status'):
                if not self.task_data.get('completed_at'): # Only set if not already completed
                    updated_data['completed_at'] = datetime.utcnow().isoformat() + "Z"
            else: # If not a completion status, ensure completed_at is None
                updated_data['completed_at'] = None

        if update_task(self.task_id, updated_data):
            # Access MainDashboard instance through parent_dialog (EditProductionOrderDialog)
            # which should have a reference to MainDashboard (parent_main_dashboard)
            if hasattr(self.parent_dialog, 'parent_main_dashboard') and \
               hasattr(self.parent_dialog.parent_main_dashboard, 'log_activity'):
                 self.parent_dialog.parent_main_dashboard.log_activity(f"Updated production step/task ID: {self.task_id}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to update step. Check logs.")
