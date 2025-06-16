from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QHeaderView, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

# Assuming db.py is in the parent directory of project_management
# and the application is run from a context where 'db' is discoverable.
from db import (
    get_project_by_id,
    get_all_clients, # Used to get client name
    get_status_setting_by_id,
    get_team_member_by_id,
    get_tasks_by_project_id_ordered_by_sequence, # Assumed to exist in db.py
    get_task_by_id # Not directly in original ProductionOrderDetailDialog, but related to tasks
)

class ProductionOrderDetailDialog(QDialog):
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.order_data = get_project_by_id(self.project_id)

        if not self.order_data:
            QMessageBox.critical(self, "Error", f"Could not load details for Production Order ID: {self.project_id}")
            QTimer.singleShot(0, self.reject)
            return

        self.setWindowTitle(f"Details: {self.order_data.get('project_name', 'Production Order')}")
        self.setMinimumSize(750, 650)

        self.layout = QVBoxLayout(self)

        # Main Info Section (using QGroupBox for structure)
        info_group = QGroupBox("Order Information")
        info_form_layout = QFormLayout(info_group)

        # Helper to add rows to form layout
        def add_info_row(label_text, value_text):
            label_widget = QLabel(f"<b>{label_text}:</b>")
            value_widget = QLabel(str(value_text) if value_text is not None else "N/A")
            value_widget.setWordWrap(True)
            info_form_layout.addRow(label_widget, value_widget)

        add_info_row("Order ID", self.order_data.get('project_id'))
        add_info_row("Order Name", self.order_data.get('project_name'))

        client_id = self.order_data.get('client_id')
        client_name = "N/A"
        if client_id:
            # get_all_clients might return a list. If so, need to find the specific client.
            # Assuming get_all_clients can take filters, or a get_client_by_id exists.
            # For now, using get_all_clients and filtering locally if it returns a list.
            clients_list = get_all_clients(filters={'client_id': client_id})
            if clients_list and isinstance(clients_list, list) and len(clients_list) > 0:
                 client_name = clients_list[0].get('client_name', 'Unknown Client')
            elif isinstance(clients_list, dict) and clients_list.get('client_id') == client_id: # If it directly returns the client dict
                 client_name = clients_list.get('client_name', 'Unknown Client')
            # If a more direct get_client_by_id(client_id) exists, that would be better.
            # client_obj = get_client_by_id(client_id)
            # if client_obj: client_name = client_obj.get('client_name', 'Unknown Client')

        add_info_row("Client", client_name)

        add_info_row("Description", self.order_data.get('description', "No description provided."))
        add_info_row("Start Date", self.order_data.get('start_date'))
        add_info_row("Deadline", self.order_data.get('deadline_date'))

        status_id = self.order_data.get('status_id')
        status_text = "N/A"
        if status_id:
            status_obj = get_status_setting_by_id(status_id)
            if status_obj: status_text = status_obj.get('status_name', 'Unknown')
        add_info_row("Status", status_text)

        priority_map = {0: "Low", 1: "Medium", 2: "High"}
        add_info_row("Priority", priority_map.get(self.order_data.get('priority'), "N/A"))
        add_info_row("Progress", f"{self.order_data.get('progress_percentage', 0)}%")

        manager_id = self.order_data.get('manager_team_member_id') # This is team_member_id in Projects table
        manager_name = "Unassigned"
        if manager_id: # manager_id is a team_member_id
            manager_tm = get_team_member_by_id(manager_id) # So, use get_team_member_by_id
            if manager_tm: manager_name = manager_tm.get('full_name', 'Unknown Manager')
        add_info_row("Manager", manager_name)

        add_info_row("Budget", f"€{self.order_data.get('budget', 0.0):,.2f}")
        add_info_row("Type", self.order_data.get('project_type', 'N/A'))
        add_info_row("Created At", self.order_data.get('created_at'))
        add_info_row("Last Updated", self.order_data.get('updated_at'))

        self.layout.addWidget(info_group)

        # Production Steps (Tasks) Section
        steps_group = QGroupBox("Production Steps")
        steps_layout = QVBoxLayout(steps_group)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(8) # Sequence, Name, Assignee, Status, Priority, Due, Est.Hours, Actual Hours
        self.steps_table.setHorizontalHeaderLabels([
            "Seq", "Step Name", "Assignee", "Status", "Priority",
            "Due Date", "Est. Hours", "Actual Hours"
        ])
        self.steps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.steps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.steps_table.verticalHeader().setVisible(False)
        self.steps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name column stretch
        for i in [0, 2, 3, 4, 5, 6, 7]:
            self.steps_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)


        self.load_production_steps()
        steps_layout.addWidget(self.steps_table)
        self.layout.addWidget(steps_group)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        self.layout.addWidget(close_button, 0, Qt.AlignRight)

    def load_production_steps(self):
        self.steps_table.setRowCount(0)
        # Ensure get_tasks_by_project_id_ordered_by_sequence is available and imported
        tasks = get_tasks_by_project_id_ordered_by_sequence(self.project_id)
        if not tasks:
            return

        self.steps_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            seq_item = QTableWidgetItem(str(task.get('sequence_order', '')))
            self.steps_table.setItem(row, 0, seq_item)

            name_item = QTableWidgetItem(task.get('task_name', 'N/A'))
            description_tooltip = task.get('description', '')
            if description_tooltip:
                name_item.setToolTip(description_tooltip)
            self.steps_table.setItem(row, 1, name_item)

            assignee_name = "Unassigned"
            assignee_id = task.get('assignee_team_member_id')
            if assignee_id:
                tm = get_team_member_by_id(assignee_id)
                if tm: assignee_name = tm.get('full_name', 'Unknown')
            self.steps_table.setItem(row, 2, QTableWidgetItem(assignee_name))

            status_text = "N/A"
            status_color_hex = "#000000"
            status_id = task.get('status_id')
            if status_id:
                stat = get_status_setting_by_id(status_id)
                if stat:
                    status_text = stat.get('status_name', 'Unknown')
                    status_color_hex = stat.get('color_hex', '#000000')
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color_hex))
            self.steps_table.setItem(row, 3, status_item)

            priority_val = task.get('priority', 0)
            priority_text = "Low"
            if priority_val == 1: priority_text = "Medium"
            elif priority_val == 2: priority_text = "High"
            self.steps_table.setItem(row, 4, QTableWidgetItem(priority_text))

            self.steps_table.setItem(row, 5, QTableWidgetItem(task.get('due_date', '')))
            self.steps_table.setItem(row, 6, QTableWidgetItem(str(task.get('estimated_duration_hours', ''))))
            self.steps_table.setItem(row, 7, QTableWidgetItem(str(task.get('actual_duration_hours', ''))))

        self.steps_table.resizeRowsToContents()
        # self.steps_table.resizeColumnsToContents() # Resize all columns
                                                  # kept specific resize from original for other columns.
                                                  # Column 1 (Name) is stretch, others are ResizeToContents.
                                                  # This should be fine.
