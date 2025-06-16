from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
                             QComboBox, QDateEdit, QDoubleSpinBox, QGroupBox,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QHBoxLayout, QPushButton, QDialogButtonBox, QMessageBox,
                             QInputDialog, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QIcon

# Assuming db.py is discoverable
from db import (
    get_project_by_id,
    get_all_status_settings,
    get_status_setting_by_id,
    get_all_team_members,
    get_team_member_by_id,
    get_all_clients,
    update_project,
    get_tasks_by_project_id_ordered_by_sequence, # Assumed to exist
    add_task,
    get_status_setting_by_name, # For new tasks default status
    update_task,
    delete_task
)

# Relative import for EditProductionStepDialog
from .edit_production_step_dialog import EditProductionStepDialog

class EditProductionOrderDialog(QDialog):
    def __init__(self, project_id, parent=None): # parent is expected to be MainDashboard instance
        super().__init__(parent)
        self.parent_main_dashboard = parent # Store reference to MainDashboard for logging
        self.project_id = project_id
        self.setWindowTitle(f"Edit Production Order - ID: {self.project_id}")
        self.setMinimumSize(600, 700)

        self.layout = QVBoxLayout(self)

        self.order_data = get_project_by_id(self.project_id)
        if not self.order_data:
            QMessageBox.critical(self, "Error", "Could not load production order data.")
            QTimer.singleShot(0, self.reject)
            return

        self.form_layout = QFormLayout()
        self.name_edit = QLineEdit(self.order_data.get('project_name', ''))
        self.desc_edit = QTextEdit(self.order_data.get('description', ''))
        self.desc_edit.setMinimumHeight(80)

        start_date_str = self.order_data.get('start_date', QDate.currentDate().toString("yyyy-MM-dd"))
        self.start_date_edit = QDateEdit(QDate.fromString(start_date_str, "yyyy-MM-dd"))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")

        deadline_str = self.order_data.get('deadline_date', QDate.currentDate().addDays(30).toString("yyyy-MM-dd"))
        self.deadline_edit = QDateEdit(QDate.fromString(deadline_str, "yyyy-MM-dd"))
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")

        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 10000000)
        self.budget_spin.setPrefix("€ ")
        self.budget_spin.setValue(self.order_data.get('budget', 0.0))

        self.status_combo = QComboBox()
        project_statuses = get_all_status_settings(type_filter='Project')
        current_status_id = self.order_data.get('status_id')
        if project_statuses:
            for idx, ps in enumerate(project_statuses):
                self.status_combo.addItem(ps['status_name'], ps['status_id'])
                if ps['status_id'] == current_status_id:
                    self.status_combo.setCurrentIndex(idx)
        elif current_status_id:
            status_obj = get_status_setting_by_id(current_status_id)
            if status_obj: self.status_combo.addItem(status_obj['status_name'], status_obj['status_id'])

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        priority_val = self.order_data.get('priority', 1)
        self.priority_combo.setCurrentIndex(priority_val)

        self.manager_combo = QComboBox()
        self.manager_combo.addItem("Unassigned", None)
        active_team_members = get_all_team_members(filters={'is_active': True})
        # manager_team_member_id in Projects table is indeed team_member_id, not user_id.
        current_manager_tm_id = self.order_data.get('manager_team_member_id')
        if active_team_members:
            for idx, tm in enumerate(active_team_members):
                self.manager_combo.addItem(tm['full_name'], tm['team_member_id'])
                if tm['team_member_id'] == current_manager_tm_id:
                    self.manager_combo.setCurrentIndex(idx + 1)

        self.client_combo = QComboBox()
        self.client_combo.addItem("No Client Associated", None)
        all_clients = get_all_clients()
        current_client_id = self.order_data.get('client_id')
        if all_clients:
            for idx, client in enumerate(all_clients):
                self.client_combo.addItem(client['client_name'], client['client_id'])
                if client['client_id'] == current_client_id:
                    self.client_combo.setCurrentIndex(idx + 1)


        self.form_layout.addRow("Order Name*:", self.name_edit)
        self.form_layout.addRow("Client (Optional):", self.client_combo)
        self.form_layout.addRow("Description:", self.desc_edit)
        self.form_layout.addRow("Start Date:", self.start_date_edit)
        self.form_layout.addRow("Deadline:", self.deadline_edit)
        self.form_layout.addRow("Budget (Optional):", self.budget_spin)
        self.form_layout.addRow("Status:", self.status_combo)
        self.form_layout.addRow("Priority:", self.priority_combo)
        self.form_layout.addRow("Manager:", self.manager_combo)
        self.layout.addLayout(self.form_layout)

        steps_group = QGroupBox("Production Steps (Tasks)")
        steps_layout = QVBoxLayout(steps_group)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["Step Name", "Assignee", "Status", "Due Date", "Actions"])
        self.steps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.steps_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.steps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.steps_table.verticalHeader().setVisible(False)
        self.load_existing_steps()

        steps_buttons_layout = QHBoxLayout()
        add_step_btn = QPushButton("Add New Step")
        add_step_btn.setIcon(QIcon(":/icons/plus.svg")) # Assuming icons are available
        add_step_btn.clicked.connect(self.add_new_step_dialog)

        move_up_btn = QPushButton("Move Up")
        move_up_btn.setIcon(QIcon(":/icons/arrow-up.svg"))
        move_up_btn.clicked.connect(self.move_step_up)

        move_down_btn = QPushButton("Move Down")
        move_down_btn.setIcon(QIcon(":/icons/arrow-down.svg"))
        move_down_btn.clicked.connect(self.move_step_down)

        steps_buttons_layout.addWidget(add_step_btn)
        steps_buttons_layout.addWidget(move_up_btn)
        steps_buttons_layout.addWidget(move_down_btn)
        steps_buttons_layout.addStretch()

        steps_layout.addLayout(steps_buttons_layout)
        steps_layout.addWidget(self.steps_table)
        self.layout.addWidget(steps_group)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText("Save Changes")
        self.button_box.accepted.connect(self.on_save_changes)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def load_existing_steps(self):
        self.steps_table.setRowCount(0)
        tasks = get_tasks_by_project_id_ordered_by_sequence(self.project_id)
        if not tasks: return

        self.steps_table.setRowCount(len(tasks))
        for row, task_dict in enumerate(tasks):
            task_id = task_dict['task_id']
            name_item = QTableWidgetItem(task_dict.get('task_name', 'N/A'))
            name_item.setData(Qt.UserRole, task_id)
            self.steps_table.setItem(row, 0, name_item)

            assignee_name = "Unassigned"
            assignee_id = task_dict.get('assignee_team_member_id')
            if assignee_id:
                tm = get_team_member_by_id(assignee_id)
                if tm: assignee_name = tm.get('full_name', 'Unknown')
            self.steps_table.setItem(row, 1, QTableWidgetItem(assignee_name))

            status_name = "N/A"
            status_id = task_dict.get('status_id')
            if status_id:
                stat = get_status_setting_by_id(status_id)
                if stat: status_name = stat.get('status_name', 'Unknown')
            self.steps_table.setItem(row, 2, QTableWidgetItem(status_name))

            self.steps_table.setItem(row, 3, QTableWidgetItem(task_dict.get('due_date', '')))

            step_action_widget = QWidget()
            step_action_layout = QHBoxLayout(step_action_widget)
            step_action_layout.setContentsMargins(0,0,0,0)
            step_action_layout.setSpacing(5)

            edit_step_btn = QPushButton("Edit")
            edit_step_btn.setObjectName("tableActionButton") # For QSS styling
            edit_step_btn.clicked.connect(lambda _, t_id=task_id: self.edit_single_step_dialog(t_id))

            delete_step_btn = QPushButton("Del")
            delete_step_btn.setObjectName("dangerButtonTable") # For QSS styling
            delete_step_btn.clicked.connect(lambda _, t_id=task_id, r=row: self.remove_step_from_table_and_db(t_id, r))

            step_action_layout.addWidget(edit_step_btn)
            step_action_layout.addWidget(delete_step_btn)
            self.steps_table.setCellWidget(row, 4, step_action_widget)
        self.steps_table.resizeColumnsToContents()

    def move_step_up(self):
        selected_rows = self.steps_table.selectionModel().selectedRows()
        if not selected_rows: return
        current_row = selected_rows[0].row()
        if current_row > 0:
            self.steps_table.insertRow(current_row - 1)
            for col in range(self.steps_table.columnCount()):
                item = self.steps_table.takeItem(current_row + 1, col)
                self.steps_table.setItem(current_row - 1, col, item)
                cell_widget = self.steps_table.cellWidget(current_row + 1, col)
                if cell_widget:
                    # Detach and reattach widget
                    taken_widget = self.steps_table.cellWidget(current_row + 1, col)
                    self.steps_table.setCellWidget(current_row - 1, col, taken_widget)
            self.steps_table.removeRow(current_row + 1)
            self.steps_table.selectRow(current_row - 1)

    def move_step_down(self):
        selected_rows = self.steps_table.selectionModel().selectedRows()
        if not selected_rows: return
        current_row = selected_rows[0].row()
        if current_row < self.steps_table.rowCount() - 1:
            self.steps_table.insertRow(current_row + 2) # Insert after the next row
            for col in range(self.steps_table.columnCount()):
                item = self.steps_table.takeItem(current_row, col)
                self.steps_table.setItem(current_row + 2, col, item)
                cell_widget = self.steps_table.cellWidget(current_row, col)
                if cell_widget:
                    taken_widget = self.steps_table.cellWidget(current_row, col)
                    self.steps_table.setCellWidget(current_row + 2, col, taken_widget)
            self.steps_table.removeRow(current_row)
            self.steps_table.selectRow(current_row + 1) # Select the moved row at its new position


    def add_new_step_dialog(self):
        new_step_name, ok = QInputDialog.getText(self, "Add New Step", "Step Name:")
        if ok and new_step_name:
            row_pos = self.steps_table.rowCount()
            self.steps_table.insertRow(row_pos)

            name_item = QTableWidgetItem(new_step_name)
            name_item.setData(Qt.UserRole, None) # None ID means it's new
            self.steps_table.setItem(row_pos, 0, name_item)

            self.steps_table.setItem(row_pos, 1, QTableWidgetItem("Unassigned"))
            self.steps_table.setItem(row_pos, 2, QTableWidgetItem("To Do"))
            self.steps_table.setItem(row_pos, 3, QTableWidgetItem(QDate.currentDate().addDays(7).toString("yyyy-MM-dd"))) # Default due date

            step_action_widget = QWidget()
            step_action_layout = QHBoxLayout(step_action_widget)
            step_action_layout.setContentsMargins(0,0,0,0)
            step_action_layout.setSpacing(5)
            edit_step_btn = QPushButton("Edit"); edit_step_btn.setEnabled(False)
            delete_step_btn = QPushButton("Del")
            delete_step_btn.setObjectName("dangerButtonTable")
            # For new rows, lambda r=row_pos might capture the loop variable if in a loop.
            # Here, row_pos is correct at definition time.
            delete_step_btn.clicked.connect(lambda _, r=row_pos: self.remove_step_from_table_and_db(None, r))
            step_action_layout.addWidget(edit_step_btn)
            step_action_layout.addWidget(delete_step_btn)
            self.steps_table.setCellWidget(row_pos, 4, step_action_widget)

    def edit_single_step_dialog(self, task_id):
        # Pass self (EditProductionOrderDialog instance) as parent_dialog for EditProductionStepDialog
        dialog = EditProductionStepDialog(task_id, parent_dialog=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_existing_steps()

    def remove_step_from_table_and_db(self, task_id, row_index):
        if task_id is None:
            self.steps_table.removeRow(row_index)
            return

        reply = QMessageBox.question(self, "Confirm Delete Step",
                                     f"Are you sure you want to delete step '{self.steps_table.item(row_index, 0).text()}'?\nThis will remove it from the database.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if delete_task(task_id):
                self.steps_table.removeRow(row_index)
                if hasattr(self.parent_main_dashboard, 'log_activity'):
                     self.parent_main_dashboard.log_activity(f"Deleted production step/task ID: {task_id}")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete step from database.")

    def on_save_changes(self):
        updated_order_data = {
            'project_name': self.name_edit.text().strip(),
            'client_id': self.client_combo.currentData(),
            'description': self.desc_edit.toPlainText().strip(),
            'start_date': self.start_date_edit.date().toString("yyyy-MM-dd"),
            'deadline_date': self.deadline_edit.date().toString("yyyy-MM-dd"),
            'budget': self.budget_spin.value(),
            'status_id': self.status_combo.currentData(),
            'priority': self.priority_combo.currentIndex(),
            'manager_team_member_id': self.manager_combo.currentData(),
            'project_type': 'PRODUCTION'
        }

        if not updated_order_data['project_name']:
            QMessageBox.warning(self, "Input Error", "Production Order name cannot be empty.")
            return

        update_project(self.project_id, updated_order_data)

        ui_tasks_info = []
        for i in range(self.steps_table.rowCount()):
            task_id_from_item = self.steps_table.item(i,0).data(Qt.UserRole)
            task_name_from_item = self.steps_table.item(i,0).text()
            # In a fuller version, other fields like assignee, status, due_date would be read from table.
            ui_tasks_info.append({'id': task_id_from_item,
                                  'name': task_name_from_item,
                                  'sequence': i + 1})

        existing_db_tasks_list = get_tasks_by_project_id_ordered_by_sequence(self.project_id)
        db_task_map_by_id = {t['task_id']: t for t in existing_db_tasks_list}

        for task_info_from_ui in ui_tasks_info:
            task_id = task_info_from_ui['id']
            if task_id is None: # New task added via UI
                new_task_data = {
                    'project_id': self.project_id,
                    'task_name': task_info_from_ui['name'],
                    'sequence_order': task_info_from_ui['sequence'],
                }
                # Default 'To Do' status for new tasks
                status_todo_obj = get_status_setting_by_name("To Do", "Task")
                if status_todo_obj: new_task_data['status_id'] = status_todo_obj['status_id']

                # Set reporter if MainDashboard (parent) has current_user
                if hasattr(self.parent_main_dashboard, 'current_user') and self.parent_main_dashboard.current_user:
                    user_id_for_reporter = self.parent_main_dashboard.current_user.get('user_id')
                    if user_id_for_reporter:
                        # Find team_member_id from user_id
                        tm_list = get_all_team_members(filters={'user_id': user_id_for_reporter})
                        if tm_list: new_task_data['reporter_team_member_id'] = tm_list[0].get('team_member_id')

                add_task(new_task_data)
            else: # Existing task
                db_task_details = db_task_map_by_id.get(task_id)
                if db_task_details:
                    update_payload = {}
                    if db_task_details['task_name'] != task_info_from_ui['name']:
                        update_payload['task_name'] = task_info_from_ui['name']
                    if db_task_details['sequence_order'] != task_info_from_ui['sequence']:
                        update_payload['sequence_order'] = task_info_from_ui['sequence']

                    if update_payload:
                        update_task(task_id, update_payload)

                    if task_id in db_task_map_by_id: # Mark as processed
                        del db_task_map_by_id[task_id]

        # Tasks remaining in db_task_map_by_id were deleted from UI if interactive delete wasn't final
        # However, current setup uses interactive delete which calls DB.
        # This loop is a safeguard or for batch delete on save logic.
        # For now, it's redundant if interactive deletes are successful.
        # for task_id_to_delete in db_task_map_by_id.keys():
        # delete_task(task_id_to_delete)

        self.accept()
