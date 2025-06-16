from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
                             QComboBox, QDateEdit, QDoubleSpinBox, QGroupBox,
                             QListWidget, QAbstractItemView, QHBoxLayout,
                             QPushButton, QDialogButtonBox)
from PyQt5.QtCore import QDate, Qt # Qt might not be used directly
from PyQt5.QtGui import QIcon # If icons are used with buttons

# Assuming db.py is discoverable
from db import (
    get_all_status_settings,
    get_all_team_members,
    get_all_clients
)

class AddProductionOrderDialog(QDialog):
    def __init__(self, parent=None, template_manager=None): # template_manager not used currently
        super().__init__(parent)
        self.setWindowTitle("New Production Order")
        self.setMinimumSize(550, 650)

        self.layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("E.g., Custom Furniture Batch A")

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Detailed description of the production order...")
        self.desc_edit.setMinimumHeight(80)

        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")

        self.deadline_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")

        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 10000000)
        self.budget_spin.setPrefix("€ ")
        self.budget_spin.setValue(0)

        self.status_combo = QComboBox()
        project_statuses = get_all_status_settings(type_filter='Project')
        if project_statuses:
            for ps in project_statuses:
                if not ps.get('is_archival_status') and not ps.get('is_completion_status'):
                    self.status_combo.addItem(ps['status_name'], ps['status_id'])
        if self.status_combo.count() == 0:
            self.status_combo.addItem("Planning", None)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        self.priority_combo.setCurrentIndex(1)

        self.manager_combo = QComboBox()
        self.manager_combo.addItem("Unassigned", None)
        active_team_members = get_all_team_members(filters={'is_active': True})
        if active_team_members:
            for tm in active_team_members:
                self.manager_combo.addItem(tm['full_name'], tm['team_member_id'])

        self.client_combo = QComboBox()
        self.client_combo.addItem("No Client Associated", None)
        all_clients_list = get_all_clients() # Renamed to avoid conflict
        if all_clients_list:
            for client_item in all_clients_list: # Renamed to avoid conflict
                self.client_combo.addItem(client_item['client_name'], client_item['client_id'])

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

        steps_group = QGroupBox("Initial Production Steps (Tasks)")
        steps_group_layout_inner = QVBoxLayout(steps_group) # Renamed

        self.steps_list_widget = QListWidget()
        self.steps_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.steps_list_widget.setAlternatingRowColors(True)

        steps_buttons_layout = QHBoxLayout()
        add_conception_btn = QPushButton("Add 'Conception'")
        add_conception_btn.clicked.connect(lambda: self.add_step("Conception"))
        add_realization_btn = QPushButton("Add 'Realization'")
        add_realization_btn.clicked.connect(lambda: self.add_step("Realization"))
        add_assembly_btn = QPushButton("Add 'Assembly'")
        add_assembly_btn.clicked.connect(lambda: self.add_step("Assembly"))
        add_qc_btn = QPushButton("Add 'Quality Control'")
        add_qc_btn.clicked.connect(lambda: self.add_step("Quality Control"))

        steps_buttons_layout.addWidget(add_conception_btn)
        steps_buttons_layout.addWidget(add_realization_btn)
        steps_buttons_layout.addWidget(add_assembly_btn)
        steps_buttons_layout.addWidget(add_qc_btn)
        steps_buttons_layout.addStretch()

        custom_step_layout = QHBoxLayout()
        self.custom_step_edit = QLineEdit()
        self.custom_step_edit.setPlaceholderText("Enter custom step name...")
        add_custom_step_btn = QPushButton("Add Custom")
        add_custom_step_btn.clicked.connect(self.add_custom_step_from_input)
        custom_step_layout.addWidget(self.custom_step_edit, 1)
        custom_step_layout.addWidget(add_custom_step_btn)

        remove_step_btn = QPushButton("Remove Selected")
        # Assuming icons are available via resource system or path
        remove_step_btn.setIcon(QIcon(":/icons/trash.svg"))
        remove_step_btn.clicked.connect(self.remove_selected_step)

        steps_group_layout_inner.addLayout(steps_buttons_layout)
        steps_group_layout_inner.addLayout(custom_step_layout)
        steps_group_layout_inner.addWidget(self.steps_list_widget)
        steps_group_layout_inner.addWidget(remove_step_btn)

        self.layout.addWidget(steps_group)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Create Order")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def add_step(self, step_name):
        if step_name and step_name.strip():
            items = [self.steps_list_widget.item(i).text() for i in range(self.steps_list_widget.count())]
            if step_name not in items:
                self.steps_list_widget.addItem(step_name.strip())

    def add_custom_step_from_input(self):
        step_name = self.custom_step_edit.text().strip()
        if step_name:
            self.add_step(step_name)
            self.custom_step_edit.clear()

    def remove_selected_step(self):
        current_item = self.steps_list_widget.currentItem()
        if current_item:
            row = self.steps_list_widget.row(current_item)
            self.steps_list_widget.takeItem(row)

    def get_data(self):
        priority_text = self.priority_combo.currentText()
        priority_val = 0
        if priority_text == "Medium": priority_val = 1
        elif priority_text == "High": priority_val = 2

        order_data = {
            'project_name': self.name_edit.text().strip(),
            'client_id': self.client_combo.currentData(),
            'description': self.desc_edit.toPlainText().strip(),
            'start_date': self.start_date_edit.date().toString("yyyy-MM-dd"),
            'deadline_date': self.deadline_edit.date().toString("yyyy-MM-dd"),
            'budget': self.budget_spin.value(),
            'status_id': self.status_combo.currentData(),
            'progress_percentage': 0, # New orders start at 0 progress
            'manager_team_member_id': self.manager_combo.currentData(),
            'priority': priority_val,
            'project_type': 'PRODUCTION' # Explicitly set for production orders
        }

        steps_data = []
        for i in range(self.steps_list_widget.count()):
            steps_data.append(self.steps_list_widget.item(i).text())

        return order_data, steps_data
