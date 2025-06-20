# -*- coding: utf-8 -*-
import os
import sys # Ensure sys is imported for path manipulation
import types # For creating mock module objects

# --- Conditional mocking for __main__ START ---
# This MUST be before any problematic imports like 'db'
if __name__ == '__main__':
    print("MAIN_TOP: Pre-patching sys.modules for 'db' with a mock package structure.")

    # Create a mock 'db' module
    mock_db_module = types.ModuleType('db')

    # Create a mock 'db.utils' module
    mock_db_utils_module = types.ModuleType('db.utils')
    def mock_get_document_context_data(*args, **kwargs):
        print(f"MOCK db.utils.get_document_context_data called with args: {args}, kwargs: {kwargs}")
        return {}
    mock_db_utils_module.get_document_context_data = mock_get_document_context_data
    setattr(mock_db_module, 'utils', mock_db_utils_module)

    def mock_generic_db_function(func_name, *args, **kwargs):
        print(f"MOCK db.{func_name} called");
        return None

    # Generic factory for mock db functions
    def db_func_factory(name):
        return lambda *a, **kw: mock_generic_db_function(name, *a, **kw)

    mock_db_module.get_user_google_account_by_google_account_id = db_func_factory('get_user_google_account_by_google_account_id')
    mock_db_module.update_user_google_account = db_func_factory('update_user_google_account')
    mock_db_module.add_user_google_account = db_func_factory('add_user_google_account')
    mock_db_module.get_user_google_account_by_user_id = db_func_factory('get_user_google_account_by_user_id')
    mock_db_module.get_user_google_account_by_id = db_func_factory('get_user_google_account_by_id')
    mock_db_module.delete_user_google_account = db_func_factory('delete_user_google_account')
    mock_db_module.add_contact_sync_log = db_func_factory('add_contact_sync_log')
    mock_db_module.get_contact_sync_log_by_local_contact = db_func_factory('get_contact_sync_log_by_local_contact')
    mock_db_module.get_contact_sync_log_by_google_contact_id = db_func_factory('get_contact_sync_log_by_google_contact_id')
    mock_db_module.update_contact_sync_log = db_func_factory('update_contact_sync_log')
    mock_db_module.delete_contact_sync_log = db_func_factory('delete_contact_sync_log')
    mock_db_module.initialize_database = lambda: print("MOCK db.initialize_database called")
    mock_db_module.add_company_personnel = lambda *a, **kw: "mock_global_personnel_id"
    mock_db_module.get_personnel_for_company = lambda *a, **kw: []
    mock_db_module.update_company_personnel = lambda *a, **kw: True
    mock_db_module.delete_company_personnel = lambda *a, **kw: True
    sys.modules['db'] = mock_db_module

    mock_db_cruds_module = types.ModuleType('db.cruds')
    sys.modules['db.cruds'] = mock_db_cruds_module

    # Generic CRUD Mocking Factory
    def create_mock_crud_class(class_name_str, module_name_str):
        methods = [
            'get_by_id', 'get_all', 'add', 'update', 'delete', # Common ones
            'get_default_company', 'get_all_companies', 'add_company', 'update_company', 'delete_company',
            'get_company_details_by_id', 'set_default_company', 'add_personnel_to_company',
            'update_personnel_in_company', 'delete_personnel_from_company', 'get_personnel_by_company_id', 'get_company_by_id',
            'get_personnel_by_id', 'get_all_personnel_with_company_info',
            'get_all_template_categories',
            'get_distinct_template_languages', 'get_distinct_template_types', 'get_filtered_templates',
            'get_all_clients', 'get_all_products',
            'get_all_workflows', 'get_workflow_by_id', 'add_workflow', 'update_workflow', 'delete_workflow', 'set_default_workflow',
            'get_workflow_states_for_workflow', 'get_workflow_state_by_id', 'add_workflow_state', 'update_workflow_state', 'delete_workflow_state',
            'get_transitions_for_workflow', 'get_workflow_transition_by_id', 'add_workflow_transition', 'update_workflow_transition', 'delete_workflow_transition',
            'get_all_status_settings', 'get_status_setting_by_id'
        ]

        attrs = {}
        for method_name in methods:
            def make_method(name): # Closure to capture method_name
                return lambda self, *args, **kwargs: print(f"MOCK {class_name_str}.{name} called") or ([] if "all" in name or "get_workflow_states" in name or "get_transitions" in name else ({'success':True, 'id':'mock_id'} if "add" in name or "update" in name or "delete" in name or "set_default" in name else None) )
            attrs[method_name] = make_method(method_name)

        mock_class = type(class_name_str, (object,), attrs)

        mock_module = types.ModuleType(module_name_str)
        instance_name = module_name_str.split('.')[-1].replace("_crud", "") + "_crud" # e.g. companies_crud
        if "templates_crud" in module_name_str or "clients_crud" in module_name_str or "products_crud" in module_name_str:
             instance_name += "_instance" # Match existing naming

        setattr(mock_module, instance_name, mock_class())
        setattr(mock_db_cruds_module, module_name_str.split('.')[-1], mock_module) # e.g. db.cruds.companies_crud = mock_module
        sys.modules[module_name_str] = mock_module
        return getattr(mock_module, instance_name)


    # Apply generic mocking
    mock_companies_crud_instance = create_mock_crud_class('MockCompaniesCRUD', 'db.cruds.companies_crud')
    mock_company_personnel_crud = create_mock_crud_class('MockCompanyPersonnelCRUD', 'db.cruds.company_personnel_crud')
    mock_template_categories_crud = create_mock_crud_class('MockTemplateCategoriesCRUD', 'db.cruds.template_categories_crud')
    mock_templates_crud_instance = create_mock_crud_class('MockTemplatesCRUD', 'db.cruds.templates_crud')
    mock_clients_crud_instance = create_mock_crud_class('MockClientsCrud', 'db.cruds.clients_crud')
    mock_products_crud_instance = create_mock_crud_class('MockProductsCrud', 'db.cruds.products_crud')

    # Specific mocks for workflow and status settings as they have more complex data
    mock_wf_crud_module = types.ModuleType('db.cruds.workflow_cruds')
    class MockWorkflowsCrud:
        _workflows_data = [{'workflow_id': 'wf1', 'name': 'WF1', 'description': 'D1', 'is_default': 1}]
        _states_data = {'wf1': [{'workflow_state_id': 's1_1', 'status_id': 'stat1', 'name': 'State1', 'order_in_workflow':0}]}
        _transitions_data = {'wf1': [{'transition_id': 't1', 'from_workflow_state_id': 's1_1', 'to_workflow_state_id': 's1_1', 'name': 'SelfLoop'}]}
        def get_all_workflows(self, *a, **k): print("MOCK get_all_workflows"); return self._workflows_data
        def get_workflow_by_id(self, wf_id, *a, **k): print(f"MOCK get_workflow_by_id {wf_id}"); return next((w for w in self._workflows_data if w['workflow_id'] == wf_id), None)
        def add_workflow(self, data, *a, **k): print(f"MOCK add_workflow {data}"); new_id = f"wf{len(self._workflows_data)+1}"; d = {'workflow_id':new_id, **data}; self._workflows_data.append(d); return {'success':True, 'id':new_id, 'data':d}
        def update_workflow(self, wf_id, data, *a, **k): print(f"MOCK update_workflow {wf_id}"); wf=self.get_workflow_by_id(wf_id); wf.update(data); return {'success':True, 'data':wf}
        def get_workflow_states_for_workflow(self, wf_id, *a, **k): print(f"MOCK get_workflow_states_for_workflow {wf_id}"); return self._states_data.get(wf_id, [])
        def get_workflow_state_by_id(self, ws_id, *a, **k): print(f"MOCK get_workflow_state_by_id {ws_id}"); return next((s for states in self._states_data.values() for s in states if s['workflow_state_id'] == ws_id),None)
        def add_workflow_state(self, data, *a, **k): print(f"MOCK add_workflow_state {data}"); wf_id=data['workflow_id']; new_id=f"s{wf_id}_{len(self._states_data.get(wf_id,[]))+1}"; d={'workflow_state_id':new_id, **data}; self._states_data.setdefault(wf_id,[]).append(d); return {'success':True, 'id':new_id,'data':d}
        def update_workflow_state(self, ws_id, data, *a, **k): print(f"MOCK update_workflow_state {ws_id}"); s=self.get_workflow_state_by_id(ws_id); s.update(data); return {'success':True,'data':s}
        def delete_workflow_state(self, ws_id, *a, **k): print(f"MOCK delete_workflow_state {ws_id}"); for wf_id in self._states_data: self._states_data[wf_id]=[s for s in self._states_data[wf_id] if s['workflow_state_id']!=ws_id]; return {'success':True}
        def get_transitions_for_workflow(self, wf_id, *a, **k): print(f"MOCK get_transitions_for_workflow {wf_id}"); return self._transitions_data.get(wf_id, [])
        def get_workflow_transition_by_id(self, t_id, *a, **k): print(f"MOCK get_workflow_transition_by_id {t_id}"); return next((t for trans in self._transitions_data.values() for t in trans if t['transition_id'] == t_id),None)
        def add_workflow_transition(self, data, *a, **k): print(f"MOCK add_workflow_transition {data}"); wf_id=data['workflow_id']; new_id=f"t{wf_id}_{len(self._transitions_data.get(wf_id,[]))+1}"; d={'transition_id':new_id, **data}; self._transitions_data.setdefault(wf_id,[]).append(d); return {'success':True, 'id':new_id,'data':d}
        def update_workflow_transition(self, t_id, data, *a, **k): print(f"MOCK update_workflow_transition {t_id}"); t=self.get_workflow_transition_by_id(t_id); t.update(data); return {'success':True,'data':t}
        def delete_workflow_transition(self, t_id, *a, **k): print(f"MOCK delete_workflow_transition {t_id}"); for wf_id in self._transitions_data: self._transitions_data[wf_id]=[t for t in self._transitions_data[wf_id] if t['transition_id']!=t_id]; return {'success':True}

    mock_wf_crud_module.workflows_crud = MockWorkflowsCrud()
    setattr(mock_db_cruds_module, 'workflow_cruds', mock_wf_crud_module)
    sys.modules['db.cruds.workflow_cruds'] = mock_wf_crud_module

    mock_ss_crud_module = types.ModuleType('db.cruds.status_settings_crud')
    class MockStatusSettingsCrud:
        _statuses = [{'status_id': 'stat1', 'status_name': 'Open', 'status_type': 'Client'}, {'status_id': 'stat2', 'status_name': 'Closed', 'status_type': 'Client'}]
        def get_all_status_settings(self, *a, **k): print("MOCK get_all_status_settings"); return self._statuses
        def get_status_setting_by_id(self, s_id, *a, **k): print(f"MOCK get_status_setting_by_id {s_id}"); return next((s for s in self._statuses if s['status_id'] == s_id),None)
    mock_ss_crud_module.status_settings_crud = MockStatusSettingsCrud()
    setattr(mock_db_cruds_module, 'status_settings_crud', mock_ss_crud_module)
    sys.modules['db.cruds.status_settings_crud'] = mock_ss_crud_module

    sys.modules['icons_rc'] = types.ModuleType('icons_rc_mock')
# --- Conditional mocking for __main__ END ---

import csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QLabel,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QFileDialog, QCheckBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox, QDialog, QTextEdit,
    QGroupBox, QRadioButton, QHeaderView, QDialogButtonBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize

try:
    import db as db_manager
except ImportError:
    print("ERROR: Failed to import 'db' module globally.")
    db_manager = None

try:
    from db.cruds.products_crud import products_crud_instance
except ImportError:
    print("ERROR: Failed to import 'products_crud_instance'.")
    products_crud_instance = None

try:
    from db.cruds.workflow_cruds import workflows_crud
    from db.cruds.status_settings_crud import status_settings_crud
except ImportError as e:
    print(f"ERROR: Failed to import CRUD instances: {e}.")
    if __name__ == '__main__':
        workflows_crud = sys.modules.get('db.cruds.workflow_cruds', {}).get('workflows_crud')
        status_settings_crud = sys.modules.get('db.cruds.status_settings_crud', {}).get('status_settings_crud')
        if not workflows_crud: print("Critical: Mock for workflows_crud not found in __main__ (after import error).")
        if not status_settings_crud: print("Critical: Mock for status_settings_crud not found in __main__ (after import error).")
    else:
        workflows_crud = None
        status_settings_crud = None

from dialogs.transporter_dialog import TransporterDialog
from dialogs.freight_forwarder_dialog import FreightForwarderDialog
from company_management import CompanyTabWidget

# --- Workflow State Dialog ---
class WorkflowStateDialog(QDialog):
    def __init__(self, workflow_id, available_statuses, workflow_state_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Workflow State Details"))
        self.setMinimumWidth(450)

        self.workflow_id = workflow_id
        self.available_statuses = available_statuses if available_statuses else []
        self.workflow_state_data = workflow_state_data
        self._name_was_derived = False

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.status_combo = QComboBox()
        self.status_combo.addItem(self.tr("-- Select Base Status --"), None)
        for status in self.available_statuses:
            self.status_combo.addItem(f"{status.get('status_name', 'Unnamed')} ({status.get('status_type', 'N/A')})", status.get('status_id'))
        form_layout.addRow(self.tr("Base Status (from StatusSettings):"), self.status_combo)

        self.state_name_input = QLineEdit()
        self.state_name_input.setPlaceholderText(self.tr("Optional: Defaults to selected status name"))
        form_layout.addRow(self.tr("Custom State Name in Workflow:"), self.state_name_input)

        self.status_combo.currentIndexChanged.connect(self._update_default_state_name)

        self.state_description_input = QTextEdit()
        self.state_description_input.setPlaceholderText(self.tr("Optional: Describe this state's purpose or criteria"))
        self.state_description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.state_description_input)

        self.order_spinbox = QSpinBox()
        self.order_spinbox.setRange(0, 100)
        self.order_spinbox.setToolTip(self.tr("Determines the sequence of states in the workflow."))
        form_layout.addRow(self.tr("Order in Workflow:"), self.order_spinbox)

        flags_layout = QHBoxLayout()
        self.is_start_state_checkbox = QCheckBox(self.tr("Is Start State"))
        self.is_start_state_checkbox.setToolTip(self.tr("Marks this state as an initial state for the workflow."))
        flags_layout.addWidget(self.is_start_state_checkbox)

        self.is_end_state_checkbox = QCheckBox(self.tr("Is End State"))
        self.is_end_state_checkbox.setToolTip(self.tr("Marks this state as a terminal state for the workflow."))
        flags_layout.addWidget(self.is_end_state_checkbox)
        flags_layout.addStretch()
        form_layout.addRow(self.tr("Flags:"), flags_layout)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if self.workflow_state_data:
            self._populate_fields()
        else:
            self._update_default_state_name()

    def _update_default_state_name(self):
        current_name = self.state_name_input.text().strip()
        selected_status_text = self.status_combo.currentText()
        selected_status_name_only = selected_status_text.split(' (')[0] if '(' in selected_status_text else selected_status_text

        if self.status_combo.currentIndex() > 0:
            if not self.workflow_state_data or not current_name or self._name_was_derived:
                self.state_name_input.setText(selected_status_name_only)
                self._name_was_derived = True
        elif not current_name :
             self.state_name_input.clear()
             self._name_was_derived = False

    def _populate_fields(self):
        if not self.workflow_state_data:
            return

        status_id_to_select = self.workflow_state_data.get('status_id')
        selected_status_name_for_default = ""
        for i in range(self.status_combo.count()):
            if self.status_combo.itemData(i) == status_id_to_select:
                self.status_combo.setCurrentIndex(i)
                selected_status_name_for_default = self.status_combo.currentText().split(' (')[0]
                break

        current_custom_name = self.workflow_state_data.get('name', '')
        if not current_custom_name or current_custom_name == selected_status_name_for_default:
            self.state_name_input.setText(selected_status_name_for_default)
            self._name_was_derived = True
        else:
             self.state_name_input.setText(current_custom_name)
             self._name_was_derived = False

        self.state_description_input.setPlainText(self.workflow_state_data.get('description', ''))
        self.order_spinbox.setValue(self.workflow_state_data.get('order_in_workflow', 0))
        self.is_start_state_checkbox.setChecked(bool(self.workflow_state_data.get('is_start_state', 0)))
        self.is_end_state_checkbox.setChecked(bool(self.workflow_state_data.get('is_end_state', 0)))

    def get_data(self):
        name = self.state_name_input.text().strip()
        status_id = self.status_combo.currentData()

        if status_id is None:
             QMessageBox.warning(self, self.tr("Validation Error"), self.tr("A base status must be selected."))
             return None

        if not name:
            name = self.status_combo.currentText().split(' (')[0]
            if name == self.tr("-- Select Base Status --").split(' (')[0]:
                QMessageBox.warning(self, self.tr("Validation Error"), self.tr("State name cannot be empty and a base status must be selected."))
                return None
        return {
            "workflow_id": self.workflow_id, "status_id": status_id, "name": name,
            "description": self.state_description_input.toPlainText().strip(),
            "order_in_workflow": self.order_spinbox.value(),
            "is_start_state": 1 if self.is_start_state_checkbox.isChecked() else 0,
            "is_end_state": 1 if self.is_end_state_checkbox.isChecked() else 0,
        }
# --- End Workflow State Dialog ---

# --- Workflow Transition Dialog ---
class WorkflowTransitionDialog(QDialog):
    def __init__(self, workflow_id, current_workflow_states, transition_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Workflow Transition Details"))
        self.setMinimumWidth(450)

        self.workflow_id = workflow_id
        self.current_workflow_states = current_workflow_states if current_workflow_states else []
        self.transition_data = transition_data

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.from_state_combo = QComboBox()
        self.from_state_combo.addItem(self.tr("-- Select From State --"), None)
        for state in self.current_workflow_states:
            self.from_state_combo.addItem(state.get('name', 'Unnamed State'), state.get('workflow_state_id'))
        form_layout.addRow(self.tr("From State:"), self.from_state_combo)

        self.to_state_combo = QComboBox()
        self.to_state_combo.addItem(self.tr("-- Select To State --"), None)
        for state in self.current_workflow_states:
            self.to_state_combo.addItem(state.get('name', 'Unnamed State'), state.get('workflow_state_id'))
        form_layout.addRow(self.tr("To State:"), self.to_state_combo)

        self.transition_name_input = QLineEdit()
        self.transition_name_input.setPlaceholderText(self.tr("e.g., 'Qualify Lead', 'Resolve Issue'"))
        form_layout.addRow(self.tr("Transition Name:"), self.transition_name_input)

        self.transition_description_input = QTextEdit()
        self.transition_description_input.setPlaceholderText(self.tr("Optional: Describe when this transition occurs"))
        self.transition_description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.transition_description_input)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if self.transition_data:
            self._populate_fields()

    def _populate_fields(self):
        if not self.transition_data:
            return

        from_id = self.transition_data.get('from_workflow_state_id')
        for i in range(self.from_state_combo.count()):
            if self.from_state_combo.itemData(i) == from_id:
                self.from_state_combo.setCurrentIndex(i)
                break

        to_id = self.transition_data.get('to_workflow_state_id')
        for i in range(self.to_state_combo.count()):
            if self.to_state_combo.itemData(i) == to_id:
                self.to_state_combo.setCurrentIndex(i)
                break

        self.transition_name_input.setText(self.transition_data.get('name', ''))
        self.transition_description_input.setPlainText(self.transition_data.get('description', ''))

    def get_data(self):
        from_state_id = self.from_state_combo.currentData()
        to_state_id = self.to_state_combo.currentData()
        name = self.transition_name_input.text().strip()

        if not from_state_id or not to_state_id:
            QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Both 'From State' and 'To State' must be selected."))
            return None
        if not name:
            QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Transition Name cannot be empty."))
            return None

        # Optional: Prevent self-loops if not desired, though often useful
        # if from_state_id == to_state_id:
        #     QMessageBox.warning(self, self.tr("Validation Error"), self.tr("From and To states cannot be the same for this transition type."))
        #     return None

        return {
            "workflow_id": self.workflow_id,
            "from_workflow_state_id": from_state_id,
            "to_workflow_state_id": to_state_id,
            "name": name,
            "description": self.transition_description_input.toPlainText().strip(),
        }
# --- End Workflow Transition Dialog ---


class ImportInstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Product Import Instructions"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        instructions_text_edit = QTextEdit()
        instructions_text_edit.setReadOnly(True)
        instructions_html = """
        <h3>Product CSV Import Guide</h3>
        <p>Please ensure your CSV file adheres to the following format and conventions.</p>
        <h4>Expected CSV Header:</h4>
        <p><code>product_id,product_name,product_code,description,category,language_code,base_unit_price,unit_of_measure,weight,dimensions,is_active,is_deleted</code></p>
        <h4>Field Definitions:</h4>
        <ul>
            <li><b>product_id</b>: Ignored during import (new IDs are auto-generated).</li>
            <li><b>product_name</b>: Text (Required).</li>
            <li><b>product_code</b>: Text (Required). Should be unique.</li>
            <li><b>description</b>: Text (Optional).</li>
            <li><b>category</b>: Text (Optional).</li>
            <li><b>language_code</b>: Text, e.g., 'en', 'fr' (Optional, defaults to 'fr' if empty).</li>
            <li><b>base_unit_price</b>: Number, e.g., 10.99 (Required).</li>
            <li><b>unit_of_measure</b>: Text, e.g., 'pcs', 'kg' (Optional).</li>
            <li><b>weight</b>: Number (Optional).</li>
            <li><b>dimensions</b>: Text, e.g., "LxWxH" (Optional).</li>
            <li><b>is_active</b>: Boolean, 'True' or 'False' (Optional, defaults to 'True' if empty or invalid).</li>
            <li><b>is_deleted</b>: Boolean, 'True' or 'False' (Optional, defaults to 'False' if empty or invalid).</li>
        </ul>
        <h4>Sample ChatGPT Prompt for Generating Data:</h4>
        <pre><code>Generate a CSV list of 10 sample products for an e-commerce store. The CSV should have the following columns: product_name,product_code,description,category,language_code,base_unit_price,unit_of_measure,weight,dimensions,is_active,is_deleted
Ensure `base_unit_price` is a number. `language_code` should be 'en' or 'fr'. `is_active` and `is_deleted` should be 'True' or 'False'.
Example Row:
My Awesome Product,PROD001,This is a great product.,Electronics,en,29.99,pcs,0.5,10x5x2 cm,True,False</code></pre>
        """
        instructions_text_edit.setHtml(instructions_html)
        layout.addWidget(instructions_text_edit)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton(self.tr("OK"))
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

class SettingsPage(QWidget):
    def __init__(self, main_config, app_root_dir, current_user_id, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.main_config = main_config
        self.app_root_dir = app_root_dir
        self.current_user_id = current_user_id
        self.selected_workflow_id = None

        self.module_config = [
            {"key": "module_project_management_enabled", "label_text": self.tr("Project Management")},
            {"key": "module_product_management_enabled", "label_text": self.tr("Product Management")},
            {"key": "module_partner_management_enabled", "label_text": self.tr("Partner Management")},
            {"key": "module_statistics_enabled", "label_text": self.tr("Statistics")},
            {"key": "module_inventory_management_enabled", "label_text": self.tr("Inventory Management")},
            {"key": "module_botpress_integration_enabled", "label_text": self.tr("Botpress Integration")},
            {"key": "module_carrier_map_enabled", "label_text": self.tr("Carrier Map")},
            {"key": "module_camera_management_enabled", "label_text": self.tr("Camera Management")},
        ]
        self.module_radio_buttons = {}
        global db_manager
        if __name__ != '__main__':
            if db_manager is None and 'db_manager' in globals() and globals()['db_manager'] is not None:
                pass
            elif db_manager is None :
                print("WARNING: db_manager is None in SettingsPage init and not running __main__")
        else:
            if db_manager is None:
                 print("WARNING: db_manager is None in SettingsPage init even when running __main__!")

        main_layout = QVBoxLayout(self)
        title_label = QLabel(self.tr("Application Settings"))
        title_label.setObjectName("pageTitleLabel")
        title_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title_label)

        self.tabs_widget = QTabWidget()
        self.tabs_widget.setObjectName("settingsTabs")

        self._setup_general_tab()
        self._setup_email_tab()
        self._setup_download_monitor_tab()
        self._setup_modules_tab()
        self._setup_data_management_tab()

        self.company_tab = CompanyTabWidget(
            parent=self,
            app_root_dir=self.app_root_dir,
            current_user_id=self.current_user_id
        )
        self.tabs_widget.addTab(self.company_tab, self.tr("Company & Personnel"))

        self._setup_transporters_tab()
        self._setup_freight_forwarders_tab()
        self._setup_template_visibility_tab()
        self._setup_workflows_tab()

        main_layout.addWidget(self.tabs_widget)
        main_layout.addStretch(1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.reload_settings_button = QPushButton(self.tr("Reload Current"))
        self.reload_settings_button.setObjectName("secondaryButton")
        self.reload_settings_button.clicked.connect(self._load_all_settings_from_config)
        self.restore_defaults_button = QPushButton(self.tr("Restore Defaults"))
        self.restore_defaults_button.setObjectName("secondaryButton")
        self.save_settings_button = QPushButton(self.tr("Save All Settings"))
        self.save_settings_button.setObjectName("primaryButton")
        self.save_settings_button.clicked.connect(self._save_all_settings)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.reload_settings_button)
        buttons_layout.addWidget(self.restore_defaults_button)
        buttons_layout.addWidget(self.save_settings_button)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

        self._load_all_settings_from_config()
        if db_manager:
            self._load_transporters_table()
            self._load_forwarders_table()
        else:
            print("WARNING: db_manager not available. Transporter and Forwarder tables will not be loaded.")

    def _setup_general_tab(self):
        general_tab_widget = QWidget()
        general_form_layout = QFormLayout(general_tab_widget)
        general_form_layout.setContentsMargins(10, 10, 10, 10); general_form_layout.setSpacing(10)
        self.templates_dir_input = QLineEdit()
        templates_browse_btn = QPushButton(self.tr("Browse...")); templates_browse_btn.clicked.connect(lambda: self._browse_directory(self.templates_dir_input, self.tr("Select Templates Directory")))
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn)
        general_form_layout.addRow(self.tr("Templates Directory:"), templates_dir_layout)
        self.clients_dir_input = QLineEdit()
        clients_browse_btn = QPushButton(self.tr("Browse...")); clients_browse_btn.clicked.connect(lambda: self._browse_directory(self.clients_dir_input, self.tr("Select Clients Directory")))
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn)
        general_form_layout.addRow(self.tr("Clients Directory:"), clients_dir_layout)
        self.interface_lang_combo = QComboBox()
        self.lang_display_to_code = {self.tr("French (fr)"): "fr", self.tr("English (en)"): "en", self.tr("Arabic (ar)"): "ar", self.tr("Turkish (tr)"): "tr", self.tr("Portuguese (pt)"): "pt", self.tr("Russian (ru)"): "ru"}
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))
        general_form_layout.addRow(self.tr("Interface Language (restart required):"), self.interface_lang_combo)
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365)
        general_form_layout.addRow(self.tr("Old Client Reminder (days):"), self.reminder_days_spinbox)
        self.session_timeout_spinbox = QSpinBox(); self.session_timeout_spinbox.setRange(5, 525600); self.session_timeout_spinbox.setSuffix(self.tr(" minutes"))
        self.session_timeout_spinbox.setToolTip(self.tr("Set session duration. Examples: 1440 (1 day), 10080 (1 week), 43200 (30 days)."))
        general_form_layout.addRow(self.tr("Session Timeout (minutes):"), self.session_timeout_spinbox)
        self.google_maps_url_input = QLineEdit(); self.google_maps_url_input.setPlaceholderText(self.tr("Enter full Google Maps review URL"))
        general_form_layout.addRow(self.tr("Google Maps Review Link:"), self.google_maps_url_input)
        self.show_setup_prompt_checkbox = QCheckBox()
        general_form_layout.addRow(self.tr("Show setup prompt on next start (if no company):"), self.show_setup_prompt_checkbox)
        self.db_path_input = QLineEdit()
        db_path_browse_btn = QPushButton(self.tr("Browse...")); db_path_browse_btn.clicked.connect(lambda: self._browse_db_file(self.db_path_input))
        db_path_layout = QHBoxLayout(); db_path_layout.addWidget(self.db_path_input); db_path_layout.addWidget(db_path_browse_btn)
        general_form_layout.addRow(self.tr("Database Path:"), db_path_layout)
        general_tab_widget.setLayout(general_form_layout)
        self.tabs_widget.addTab(general_tab_widget, self.tr("General"))

    def _setup_email_tab(self):
        email_tab_widget = QWidget()
        email_form_layout = QFormLayout(email_tab_widget)
        email_form_layout.setContentsMargins(10, 10, 10, 10); email_form_layout.setSpacing(10)
        self.smtp_server_input = QLineEdit()
        email_form_layout.addRow(self.tr("SMTP Server:"), self.smtp_server_input)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535)
        email_form_layout.addRow(self.tr("SMTP Port:"), self.smtp_port_spinbox)
        self.smtp_user_input = QLineEdit()
        email_form_layout.addRow(self.tr("SMTP Username:"), self.smtp_user_input)
        self.smtp_pass_input = QLineEdit(); self.smtp_pass_input.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("SMTP Password:"), self.smtp_pass_input)
        email_tab_widget.setLayout(email_form_layout)
        self.tabs_widget.addTab(email_tab_widget, self.tr("Email"))

    def _setup_download_monitor_tab(self):
        download_monitor_tab_widget = QWidget()
        download_monitor_form_layout = QFormLayout(download_monitor_tab_widget)
        download_monitor_form_layout.setContentsMargins(10, 10, 10, 10)
        download_monitor_form_layout.setSpacing(10)
        self.download_monitor_enabled_checkbox = QCheckBox(self.tr("Enable download monitoring"))
        download_monitor_form_layout.addRow(self.download_monitor_enabled_checkbox)
        self.download_monitor_path_input = QLineEdit()
        self.download_monitor_path_input.setPlaceholderText(self.tr("Select folder to monitor for new downloads"))
        browse_button = QPushButton(self.tr("Browse..."))
        browse_button.clicked.connect(self._browse_download_monitor_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.download_monitor_path_input)
        path_layout.addWidget(browse_button)
        download_monitor_form_layout.addRow(self.tr("Monitored Folder:"), path_layout)
        download_monitor_tab_widget.setLayout(download_monitor_form_layout)
        self.tabs_widget.addTab(download_monitor_tab_widget, self.tr("Download Monitoring"))

    def _browse_download_monitor_path(self):
        start_dir = self.download_monitor_path_input.text()
        if not os.path.isdir(start_dir): start_dir = os.path.expanduser('~')
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select Monitored Folder"), start_dir)
        if dir_path: self.download_monitor_path_input.setText(dir_path)

    def _setup_transporters_tab(self):
        transporters_tab = QWidget()
        transporters_layout = QVBoxLayout(transporters_tab)
        self.transporters_table = QTableWidget()
        self.transporters_table.setColumnCount(6)
        self.transporters_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Name"), self.tr("Contact Person"), self.tr("Phone"), self.tr("Email"), self.tr("Service Area")])
        self.transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transporters_table.horizontalHeader().setStretchLastSection(True)
        self.transporters_table.hideColumn(0)
        self.transporters_table.itemSelectionChanged.connect(self._update_transporter_button_states)
        transporters_layout.addWidget(self.transporters_table)
        btns_layout = QHBoxLayout()
        self.add_transporter_btn = QPushButton(self.tr("Add Transporter")); self.add_transporter_btn.setIcon(QIcon(":/icons/plus.svg"))
        self.add_transporter_btn.clicked.connect(self._handle_add_transporter)
        self.edit_transporter_btn = QPushButton(self.tr("Edit Transporter")); self.edit_transporter_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_transporter_btn.setEnabled(False)
        self.edit_transporter_btn.clicked.connect(self._handle_edit_transporter)
        self.delete_transporter_btn = QPushButton(self.tr("Delete Transporter")); self.delete_transporter_btn.setIcon(QIcon(":/icons/trash.svg")); self.delete_transporter_btn.setObjectName("dangerButton"); self.delete_transporter_btn.setEnabled(False)
        self.delete_transporter_btn.clicked.connect(self._handle_delete_transporter)
        btns_layout.addWidget(self.add_transporter_btn); btns_layout.addWidget(self.edit_transporter_btn); btns_layout.addWidget(self.delete_transporter_btn)
        transporters_layout.addLayout(btns_layout)
        self.tabs_widget.addTab(transporters_tab, self.tr("Transporters"))

    def _load_transporters_table(self):
        if not db_manager: return
        self.transporters_table.setRowCount(0)
        self.transporters_table.setSortingEnabled(False)
        try:
            transporters = db_manager.get_all_transporters() or []
            for row_idx, t_data in enumerate(transporters):
                self.transporters_table.insertRow(row_idx)
                id_item = QTableWidgetItem(str(t_data.get('transporter_id')))
                self.transporters_table.setItem(row_idx, 0, id_item)
                name_item = QTableWidgetItem(t_data.get('name'))
                name_item.setData(Qt.UserRole, t_data.get('transporter_id'))
                self.transporters_table.setItem(row_idx, 1, name_item)
                self.transporters_table.setItem(row_idx, 2, QTableWidgetItem(t_data.get('contact_person')))
                self.transporters_table.setItem(row_idx, 3, QTableWidgetItem(t_data.get('phone')))
                self.transporters_table.setItem(row_idx, 4, QTableWidgetItem(t_data.get('email')))
                self.transporters_table.setItem(row_idx, 5, QTableWidgetItem(t_data.get('service_area')))
        except Exception as e:
            QMessageBox.warning(self, self.tr("DB Error"), self.tr("Error loading transporters: {0}").format(str(e)))
        self.transporters_table.setSortingEnabled(True)
        self._update_transporter_button_states()

    def _handle_add_transporter(self):
        if not db_manager: return
        dialog = TransporterDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted: self._load_transporters_table()

    def _handle_edit_transporter(self):
        if not db_manager: return
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        transporter_id = self.transporters_table.item(selected_items[0].row(), 0).text()
        transporter_data = db_manager.get_transporter_by_id(transporter_id)
        if transporter_data:
            dialog = TransporterDialog(transporter_data=transporter_data, parent=self)
            if dialog.exec_() == QDialog.Accepted: self._load_transporters_table()
        else: QMessageBox.warning(self, self.tr("Error"), self.tr("Transporter not found."))

    def _handle_delete_transporter(self):
        if not db_manager: return
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        transporter_id = self.transporters_table.item(selected_items[0].row(), 0).text()
        transporter_name = self.transporters_table.item(selected_items[0].row(), 1).text()
        reply = QMessageBox.question(self, self.tr("Confirm Delete"), self.tr("Are you sure you want to delete transporter '{0}'?").format(transporter_name), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_transporter(transporter_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Transporter deleted."))
                self._load_transporters_table()
            else: QMessageBox.warning(self, self.tr("DB Error"), self.tr("Could not delete transporter."))

    def _update_transporter_button_states(self):
        has_selection = bool(self.transporters_table.selectedItems())
        self.edit_transporter_btn.setEnabled(has_selection)
        self.delete_transporter_btn.setEnabled(has_selection)

    def _setup_freight_forwarders_tab(self):
        forwarders_tab = QWidget()
        forwarders_layout = QVBoxLayout(forwarders_tab)
        self.forwarders_table = QTableWidget()
        self.forwarders_table.setColumnCount(6)
        self.forwarders_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Name"), self.tr("Contact Person"), self.tr("Phone"), self.tr("Email"), self.tr("Services Offered")])
        self.forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.forwarders_table.horizontalHeader().setStretchLastSection(True)
        self.forwarders_table.hideColumn(0)
        self.forwarders_table.itemSelectionChanged.connect(self._update_forwarder_button_states)
        forwarders_layout.addWidget(self.forwarders_table)
        btns_layout = QHBoxLayout()
        self.add_forwarder_btn = QPushButton(self.tr("Add Freight Forwarder")); self.add_forwarder_btn.setIcon(QIcon(":/icons/plus.svg"))
        self.add_forwarder_btn.clicked.connect(self._handle_add_forwarder)
        self.edit_forwarder_btn = QPushButton(self.tr("Edit Freight Forwarder")); self.edit_forwarder_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_forwarder_btn.setEnabled(False)
        self.edit_forwarder_btn.clicked.connect(self._handle_edit_forwarder)
        self.delete_forwarder_btn = QPushButton(self.tr("Delete Freight Forwarder")); self.delete_forwarder_btn.setIcon(QIcon(":/icons/trash.svg")); self.delete_forwarder_btn.setObjectName("dangerButton"); self.delete_forwarder_btn.setEnabled(False)
        self.delete_forwarder_btn.clicked.connect(self._handle_delete_forwarder)
        btns_layout.addWidget(self.add_forwarder_btn); btns_layout.addWidget(self.edit_forwarder_btn); btns_layout.addWidget(self.delete_forwarder_btn)
        forwarders_layout.addLayout(btns_layout)
        self.tabs_widget.addTab(forwarders_tab, self.tr("Freight Forwarders"))

    def _load_forwarders_table(self):
        if not db_manager: return
        self.forwarders_table.setRowCount(0)
        self.forwarders_table.setSortingEnabled(False)
        try:
            forwarders = db_manager.get_all_freight_forwarders() or []
            for row_idx, f_data in enumerate(forwarders):
                self.forwarders_table.insertRow(row_idx)
                id_item = QTableWidgetItem(str(f_data.get('forwarder_id')))
                self.forwarders_table.setItem(row_idx, 0, id_item)
                name_item = QTableWidgetItem(f_data.get('name'))
                name_item.setData(Qt.UserRole, f_data.get('forwarder_id'))
                self.forwarders_table.setItem(row_idx, 1, name_item)
                self.forwarders_table.setItem(row_idx, 2, QTableWidgetItem(f_data.get('contact_person')))
                self.forwarders_table.setItem(row_idx, 3, QTableWidgetItem(f_data.get('phone')))
                self.forwarders_table.setItem(row_idx, 4, QTableWidgetItem(f_data.get('email')))
                self.forwarders_table.setItem(row_idx, 5, QTableWidgetItem(f_data.get('services_offered')))
        except Exception as e:
            QMessageBox.warning(self, self.tr("DB Error"), self.tr("Error loading freight forwarders: {0}").format(str(e)))
        self.forwarders_table.setSortingEnabled(True)
        self._update_forwarder_button_states()

    def _handle_add_forwarder(self):
        if not db_manager: return
        dialog = FreightForwarderDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted: self._load_forwarders_table()

    def _handle_edit_forwarder(self):
        if not db_manager: return
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        forwarder_id = self.forwarders_table.item(selected_items[0].row(), 0).text()
        forwarder_data = db_manager.get_freight_forwarder_by_id(forwarder_id)
        if forwarder_data:
            dialog = FreightForwarderDialog(forwarder_data=forwarder_data, parent=self)
            if dialog.exec_() == QDialog.Accepted: self._load_forwarders_table()
        else: QMessageBox.warning(self, self.tr("Error"), self.tr("Freight Forwarder not found."))

    def _handle_delete_forwarder(self):
        if not db_manager: return
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        forwarder_id = self.forwarders_table.item(selected_items[0].row(), 0).text()
        forwarder_name = self.forwarders_table.item(selected_items[0].row(), 1).text()
        reply = QMessageBox.question(self, self.tr("Confirm Delete"), self.tr("Are you sure you want to delete freight forwarder '{0}'?").format(forwarder_name), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_freight_forwarder(forwarder_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Freight Forwarder deleted."))
                self._load_forwarders_table()
            else: QMessageBox.warning(self, self.tr("DB Error"), self.tr("Could not delete freight forwarder."))

    def _update_forwarder_button_states(self):
        has_selection = bool(self.forwarders_table.selectedItems())
        self.edit_forwarder_btn.setEnabled(has_selection)
        self.delete_forwarder_btn.setEnabled(has_selection)

    def _setup_data_management_tab(self):
        data_management_tab_widget = QWidget()
        layout = QVBoxLayout(data_management_tab_widget)
        self.import_products_btn = QPushButton(self.tr("Import Products"))
        self.import_products_btn.clicked.connect(self._handle_import_products)
        layout.addWidget(self.import_products_btn)
        self.export_products_btn = QPushButton(self.tr("Export Products"))
        self.export_products_btn.clicked.connect(self._handle_export_products)
        layout.addWidget(self.export_products_btn)
        instructions_label = QLabel(self.tr("Instructions for import/export format and ChatGPT prompt will be displayed here."))
        instructions_label.setWordWrap(True)
        instructions_label.setStyleSheet("font-style: italic; color: grey;")
        layout.addWidget(instructions_label)
        layout.addStretch(1)
        data_management_tab_widget.setLayout(layout)
        self.tabs_widget.addTab(data_management_tab_widget, self.tr("Data Management"))

    def _handle_export_products(self):
        if not products_crud_instance: QMessageBox.critical(self, self.tr("Error"), self.tr("Product data module is not available. Cannot export products.")); return
        try: products = products_crud_instance.get_all_products(include_deleted=True, limit=None, offset=0)
        except Exception as e: QMessageBox.critical(self, self.tr("Database Error"), self.tr("Failed to retrieve products from the database: {0}").format(str(e))); return
        if not products: QMessageBox.information(self, self.tr("No Products"), self.tr("There are no products to export.")); return
        default_filename = "products_export.csv"
        default_dir = os.path.join(os.path.expanduser('~'), 'Documents')
        if not os.path.exists(default_dir): default_dir = os.path.expanduser('~')
        suggested_filepath = os.path.join(default_dir, default_filename)
        options = QFileDialog.Options(); options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, self.tr("Save Product Export"), suggested_filepath, self.tr("CSV Files (*.csv);;All Files (*)"), options=options)
        if filePath:
            if not filePath.lower().endswith(".csv"): filePath += ".csv"
            header = ["product_id", "product_name", "product_code", "description", "category", "language_code", "base_unit_price", "unit_of_measure", "weight", "dimensions", "is_active", "is_deleted"]
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=header, extrasaction='ignore')
                    writer.writeheader()
                    for product in products:
                        row_data = {field: getattr(product, field, '') for field in header}
                        if isinstance(row_data['dimensions'], (dict, list)): row_data['dimensions'] = str(row_data['dimensions'])
                        row_data['is_active'] = str(row_data['is_active'])
                        row_data['is_deleted'] = str(row_data['is_deleted'])
                        writer.writerow(row_data)
                QMessageBox.information(self, self.tr("Export Successful"), self.tr("Products exported successfully to: {0}").format(filePath))
            except IOError as e: QMessageBox.critical(self, self.tr("Export Error"), self.tr("Failed to write to file: {0}\nError: {1}").format(filePath, str(e)))
            except Exception as e: QMessageBox.critical(self, self.tr("Export Error"), self.tr("An unexpected error occurred during export: {0}").format(str(e)))

    def _handle_import_products(self):
        if not products_crud_instance: QMessageBox.critical(self, self.tr("Error"), self.tr("Product data module is not available. Cannot import products.")); return
        instructions_dialog = ImportInstructionsDialog(self)
        if not instructions_dialog.exec_() == QDialog.Accepted: return
        options = QFileDialog.Options(); options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getOpenFileName(self, self.tr("Open Product CSV File"), os.path.expanduser('~'), self.tr("CSV Files (*.csv);;All Files (*)"), options=options)
        if not filePath: return
        successful_imports = 0; failed_imports = 0; error_details = []
        try:
            with open(filePath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames or not all(header in reader.fieldnames for header in ["product_name", "product_code", "base_unit_price"]):
                    QMessageBox.critical(self, self.tr("Invalid CSV Format"), self.tr("The CSV file is missing one or more required headers (product_name, product_code, base_unit_price) or is not a valid CSV.")); return
                for i, row in enumerate(reader):
                    line_num = i + 2; product_data = {}
                    product_name = row.get("product_name", "").strip(); product_code = row.get("product_code", "").strip(); base_unit_price_str = row.get("base_unit_price", "").strip()
                    if not product_name: error_details.append(self.tr("Line {0}: Missing required field 'product_name'.").format(line_num)); failed_imports += 1; continue
                    if not product_code: error_details.append(self.tr("Line {0}: Missing required field 'product_code' for product '{1}'.").format(line_num, product_name)); failed_imports += 1; continue
                    if not base_unit_price_str: error_details.append(self.tr("Line {0}: Missing required field 'base_unit_price' for product '{1}'.").format(line_num, product_name)); failed_imports += 1; continue
                    try: product_data["base_unit_price"] = float(base_unit_price_str)
                    except ValueError: error_details.append(self.tr("Line {0}: Invalid format for 'base_unit_price' (must be a number) for product '{1}'.").format(line_num, product_name)); failed_imports += 1; continue
                    product_data["product_name"] = product_name; product_data["product_code"] = product_code
                    product_data["description"] = row.get("description", "").strip(); product_data["category"] = row.get("category", "").strip()
                    product_data["language_code"] = row.get("language_code", "fr").strip() or "fr"
                    product_data["unit_of_measure"] = row.get("unit_of_measure", "").strip(); product_data["weight"] = row.get("weight", "").strip()
                    product_data["dimensions"] = row.get("dimensions", "").strip()
                    is_active_str = row.get("is_active", "True").strip().lower(); product_data["is_active"] = is_active_str in ['true', '1', 'yes']
                    is_deleted_str = row.get("is_deleted", "False").strip().lower(); product_data["is_deleted"] = is_deleted_str in ['true', '1', 'yes']
                    try: products_crud_instance.add_product(product_data); successful_imports += 1
                    except Exception as e: error_details.append(self.tr("Line {0}: Error importing product '{1}': {2}").format(line_num, product_name, str(e))); failed_imports += 1
        except FileNotFoundError: QMessageBox.critical(self, self.tr("Error"), self.tr("The selected file was not found: {0}").format(filePath)); return
        except Exception as e: QMessageBox.critical(self, self.tr("Import Error"), self.tr("An unexpected error occurred during import: {0}").format(str(e))); return
        summary_message = self.tr("Import complete.\nSuccessfully imported: {0} products.\nFailed to import: {1} products.").format(successful_imports, failed_imports)
        if error_details:
            detailed_errors = "\n\n" + self.tr("Error Details (first 5 shown):") + "\n" + "\n".join(error_details[:5])
            if len(error_details) > 5: detailed_errors += "\n" + self.tr("...and {0} more errors.").format(len(error_details) - 5)
            if len(summary_message + detailed_errors) > 1000: detailed_errors = "\n\n" + self.tr("Numerous errors occurred. Please check data integrity. First few errors:\n") + "\n".join(error_details[:3])
            summary_message += detailed_errors
        if failed_imports > 0: QMessageBox.warning(self, self.tr("Import Partially Successful"), summary_message)
        else: QMessageBox.information(self, self.tr("Import Successful"), summary_message)

    def _load_general_tab_data(self):
        self.templates_dir_input.setText(self.main_config.get("templates_dir", ""))
        self.clients_dir_input.setText(self.main_config.get("clients_dir", ""))
        self.main_config.setdefault("download_monitor_enabled", False)
        self.main_config.setdefault("download_monitor_path", os.path.join(os.path.expanduser('~'), 'Downloads'))
        current_lang_code = self.main_config.get("language", "fr")
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}
        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text: self.interface_lang_combo.setCurrentText(current_display_text)
        else: self.interface_lang_combo.setCurrentText(code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0]))
        self.reminder_days_spinbox.setValue(self.main_config.get("default_reminder_days", 30))
        self.session_timeout_spinbox.setValue(self.main_config.get("session_timeout_minutes", 259200))
        self.google_maps_url_input.setText(self.main_config.get("google_maps_review_url", "https://maps.google.com/?cid=YOUR_CID_HERE"))
        self.show_setup_prompt_checkbox.setChecked(self.main_config.get("show_initial_setup_on_startup", False))
        self.db_path_input.setText(self.main_config.get("database_path", os.path.join(os.getcwd(), "app_data.db")))

    def _load_email_tab_data(self):
        self.smtp_server_input.setText(self.main_config.get("smtp_server", ""))
        self.smtp_port_spinbox.setValue(self.main_config.get("smtp_port", 587))
        self.smtp_user_input.setText(self.main_config.get("smtp_user", ""))
        self.smtp_pass_input.setText(self.main_config.get("smtp_password", ""))

    def _load_download_monitor_tab_data(self):
        self.download_monitor_enabled_checkbox.setChecked(self.main_config.get("download_monitor_enabled", False))
        default_download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.download_monitor_path_input.setText(self.main_config.get("download_monitor_path", default_download_path))

    def _browse_directory(self, line_edit_target, dialog_title):
        start_dir = line_edit_target.text();
        if not os.path.isdir(start_dir): start_dir = os.getcwd()
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, start_dir)
        if dir_path: line_edit_target.setText(dir_path)

    def _browse_db_file(self, line_edit_target):
        current_path = line_edit_target.text()
        start_dir = os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else os.getcwd()
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Database File"), start_dir, self.tr("Database Files (*.db *.sqlite *.sqlite3);;All Files (*.*)"))
        if file_path: line_edit_target.setText(file_path)

    def get_general_settings_data(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        return {"templates_dir": self.templates_dir_input.text().strip(), "clients_dir": self.clients_dir_input.text().strip(), "language": language_code, "default_reminder_days": self.reminder_days_spinbox.value(), "session_timeout_minutes": self.session_timeout_spinbox.value(), "google_maps_review_url": self.google_maps_url_input.text().strip(), "show_initial_setup_on_startup": self.show_setup_prompt_checkbox.isChecked(), "database_path": self.db_path_input.text().strip()}

    def get_email_settings_data(self):
        return {"smtp_server": self.smtp_server_input.text().strip(), "smtp_port": self.smtp_port_spinbox.value(), "smtp_user": self.smtp_user_input.text().strip(), "smtp_password": self.smtp_pass_input.text()}

    def get_download_monitor_settings_data(self):
        return { "download_monitor_enabled": self.download_monitor_enabled_checkbox.isChecked(), "download_monitor_path": self.download_monitor_path_input.text().strip()}

    def _load_all_settings_from_config(self):
        self._load_general_tab_data(); self._load_email_tab_data(); self._load_download_monitor_tab_data(); self._load_modules_tab_data()
        print("SettingsPage: All settings reloaded.")

    def _save_all_settings(self):
        general_settings = self.get_general_settings_data(); email_settings = self.get_email_settings_data(); download_monitor_settings = self.get_download_monitor_settings_data()
        for d in [general_settings, email_settings, download_monitor_settings]:
            for key, value in d.items(): self.main_config[key] = value
        self._save_modules_tab_data()
        QMessageBox.information(self, self.tr("Settings Saved"), self.tr("All settings have been updated. Some changes may require an application restart to take full effect."))
        print("All settings saved (main_config updated, modules saved to DB).")

    def _setup_modules_tab(self):
        modules_tab_widget = QWidget()
        modules_form_layout = QFormLayout(modules_tab_widget)
        modules_form_layout.setContentsMargins(10, 10, 10, 10); modules_form_layout.setSpacing(10)
        for module_info in self.module_config:
            key = module_info["key"]; label_text = module_info["label_text"]
            module_label = QLabel(label_text); radio_group_box = QGroupBox(); radio_layout = QHBoxLayout()
            radio_enabled = QRadioButton(self.tr("Activé")); radio_disabled = QRadioButton(self.tr("Désactivé"))
            radio_layout.addWidget(radio_enabled); radio_layout.addWidget(radio_disabled); radio_group_box.setLayout(radio_layout)
            self.module_radio_buttons[key] = {"enabled": radio_enabled, "disabled": radio_disabled}
            modules_form_layout.addRow(module_label, radio_group_box)
        restart_notice_label = QLabel(self.tr("Un redémarrage de l'application est nécessaire pour que les modifications des modules prennent pleinement effet."))
        restart_notice_label.setWordWrap(True); restart_notice_label.setStyleSheet("font-style: italic; color: grey;")
        modules_form_layout.addRow(restart_notice_label)
        modules_tab_widget.setLayout(modules_form_layout)
        self.tabs_widget.addTab(modules_tab_widget, self.tr("Gestion des Modules"))

    def _load_modules_tab_data(self):
        if not db_manager: print("WARNING: db_manager not available. Cannot load module settings."); return
        for module_info in self.module_config:
            key = module_info["key"]
            is_enabled_str = db_manager.get_setting(key, default='True')
            is_enabled = isinstance(is_enabled_str, bool) and is_enabled_str or is_enabled_str.lower() == 'true'
            if key in self.module_radio_buttons:
                radios = self.module_radio_buttons[key]
                if is_enabled: radios["enabled"].setChecked(True)
                else: radios["disabled"].setChecked(True)
            else: print(f"Warning: Radio buttons for module key '{key}' not found.")
        print("Module settings loaded from DB.")

    def _save_modules_tab_data(self):
        if not db_manager: QMessageBox.warning(self, self.tr("Database Error"), self.tr("Database connection is not available. Module settings cannot be saved.")); return
        for module_info in self.module_config:
            key = module_info["key"]
            if key in self.module_radio_buttons:
                value_to_save = 'True' if self.module_radio_buttons[key]["enabled"].isChecked() else 'False'
                try: db_manager.set_setting(key, value_to_save)
                except Exception as e: print(f"Error saving module setting {key}: {e}"); QMessageBox.critical(self, self.tr("Error Saving Module"), self.tr("Could not save setting for {0}: {1}").format(module_info["label_text"], str(e)))
            else: print(f"Warning: Radio buttons for module key '{key}' not found during save.")
        print("Module settings saved to DB.")

    def _setup_template_visibility_tab(self):
        self.template_visibility_tab = QWidget()
        layout = QVBoxLayout(self.template_visibility_tab)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)
        self.template_visibility_table = QTableWidget()
        self.template_visibility_table.setColumnCount(5)
        self.template_visibility_table.setHorizontalHeaderLabels([self.tr("Template Name"), self.tr("Description"), self.tr("Type"), self.tr("Language"), self.tr("Visible")])
        self.template_visibility_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.template_visibility_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.template_visibility_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.template_visibility_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.template_visibility_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.template_visibility_table)
        buttons_layout = QHBoxLayout()
        self.refresh_template_visibility_btn = QPushButton(self.tr("Refresh List")); self.refresh_template_visibility_btn.setIcon(QIcon(":/icons/refresh.svg"))
        self.refresh_template_visibility_btn.clicked.connect(self._load_template_visibility_data)
        buttons_layout.addWidget(self.refresh_template_visibility_btn)
        buttons_layout.addStretch(1)
        self.save_template_visibility_btn = QPushButton(self.tr("Save Visibility Settings")); self.save_template_visibility_btn.setIcon(QIcon(":/icons/save.svg"))
        self.save_template_visibility_btn.clicked.connect(self._save_template_visibility_data)
        buttons_layout.addWidget(self.save_template_visibility_btn)
        layout.addLayout(buttons_layout)
        self.tabs_widget.addTab(self.template_visibility_tab, self.tr("Template Visibility"))
        self._load_template_visibility_data()

    def _load_template_visibility_data(self):
        print("SettingsPage: _load_template_visibility_data called (mocked).")
        sample_data = [{"template_id": 101, "template_name": "Proforma Invoice (Basic)", "description": "Standard proforma template.", "template_type": "proforma_invoice_html", "language_code": "fr", "is_visible": True}, {"template_id": 102, "template_name": "Cover Page (Modern)", "description": "Modern style cover page.", "template_type": "html_cover_page", "language_code": "fr", "is_visible": True}, {"template_id": 103, "template_name": "Sales Quote (EN)", "description": "Standard sales quote in English.", "template_type": "document_word", "language_code": "en", "is_visible": False}, {"template_id": 104, "template_name": "Product Catalog (Compact)", "description": "Compact product catalog.", "template_type": "document_pdf", "language_code": "fr", "is_visible": True}, {"template_id": 105, "template_name": self.tr("Affichage Images Produit FR"), "description": self.tr("Affiche les images des produits, leur nom et leur code."), "template_type": "document_html", "language_code": "fr", "is_visible": True}]
        self.template_visibility_table.setRowCount(0); self.template_visibility_table.setSortingEnabled(False)
        for row_idx, t_data in enumerate(sample_data):
            self.template_visibility_table.insertRow(row_idx)
            name_item = QTableWidgetItem(t_data.get("template_name", "N/A")); name_item.setData(Qt.UserRole, t_data.get("template_id"))
            self.template_visibility_table.setItem(row_idx, 0, name_item)
            self.template_visibility_table.setItem(row_idx, 1, QTableWidgetItem(t_data.get("description", "")))
            self.template_visibility_table.setItem(row_idx, 2, QTableWidgetItem(t_data.get("template_type", "")))
            self.template_visibility_table.setItem(row_idx, 3, QTableWidgetItem(t_data.get("language_code", "")))
            checkbox_widget = QWidget(); checkbox_layout = QHBoxLayout(checkbox_widget); checkbox_layout.setContentsMargins(0,0,0,0); checkbox_layout.setAlignment(Qt.AlignCenter)
            visibility_checkbox = QCheckBox(); visibility_checkbox.setChecked(t_data.get("is_visible", True)); visibility_checkbox.setProperty("template_id", t_data.get("template_id"))
            checkbox_layout.addWidget(visibility_checkbox); self.template_visibility_table.setCellWidget(row_idx, 4, checkbox_widget)
        self.template_visibility_table.setSortingEnabled(True)
        print(f"SettingsPage: Template visibility table populated with {len(sample_data)} items (mocked).")

    def _save_template_visibility_data(self):
        print("SettingsPage: _save_template_visibility_data called (mocked).")
        payload_items = []
        for row_idx in range(self.template_visibility_table.rowCount()):
            template_id_item = self.template_visibility_table.item(row_idx, 0)
            template_id = template_id_item.data(Qt.UserRole) if template_id_item else None
            visibility_cell_widget = self.template_visibility_table.cellWidget(row_idx, 4)
            if not (template_id and visibility_cell_widget): print(f"Warning: Missing data for row {row_idx}. Skipping."); continue
            visibility_checkbox = visibility_cell_widget.findChild(QCheckBox)
            if not visibility_checkbox: print(f"Warning: QCheckBox not found in cell for row {row_idx}, template_id {template_id}. Skipping."); continue
            is_visible = visibility_checkbox.isChecked()
            payload_items.append({"template_id": template_id, "is_visible": is_visible})
        payload = {"preferences": payload_items}
        print(f"SettingsPage: Payload for POST /api/templates/visibility_settings (mocked): {payload}")
        QMessageBox.information(self, self.tr("Mock Save"), self.tr("Template visibility data (mocked) prepared. Check console for payload."))

if __name__ == '__main__':
    print(f"Running in __main__ block. Current sys.path: {sys.path}") # Debug print
    from PyQt5.QtWidgets import QApplication
    # sys and os are already imported at the top

    # Mock db_manager for standalone testing
    # The global 'db_manager' will be replaced by an instance of this class.
    class MockDBManager:
        def get_all_transporters(self): print("MOCKDB: get_all_transporters"); return [{"transporter_id": "t1", "name": "Mock Transporter 1", "contact_person": "John T", "phone": "123", "email": "jt@example.com", "service_area": "Local"}, {"transporter_id": "t2", "name": "Mock Transporter 2", "contact_person": "Alice T", "phone": "456", "email": "at@example.com", "service_area": "National"}]
        def get_transporter_by_id(self, tid): print(f"MOCKDB: get_transporter_by_id {tid}"); return {"transporter_id": tid, "name": f"Mock Transporter {tid}", "contact_person":"Test", "phone":"Test", "email":"Test", "service_area":"Test"} if tid in ["t1", "t2"] else None
        def add_transporter(self, data): print(f"MOCKDB: add_transporter: {data}"); return "t_new_mock_id"
        def update_transporter(self, tid, data): print(f"MOCKDB: update_transporter {tid}: {data}"); return True
        def delete_transporter(self, tid): print(f"MOCKDB: delete_transporter {tid}"); return True

        def get_all_freight_forwarders(self): print("MOCKDB: get_all_freight_forwarders"); return [{"forwarder_id": "f1", "name": "Mock Forwarder 1", "contact_person": "Jane F", "phone": "456", "email": "jf@example.com", "services_offered": "Global"}, {"forwarder_id": "f2", "name": "Mock Forwarder 2", "contact_person": "Bob F", "phone": "789", "email": "bf@example.com", "services_offered": "Air, Sea"}]
        def get_freight_forwarder_by_id(self, fid): print(f"MOCKDB: get_freight_forwarder_by_id {fid}"); return {"forwarder_id": fid, "name": f"Mock Forwarder {fid}", "contact_person":"Test", "phone":"Test", "email":"Test", "services_offered":"Test"} if fid in ["f1", "f2"] else None
        def add_freight_forwarder(self, data): print(f"MOCKDB: add_freight_forwarder: {data}"); return "f_new_mock_id"
        def update_freight_forwarder(self, fid, data): print(f"MOCKDB: update_freight_forwarder {fid}: {data}"); return True
        def delete_freight_forwarder(self, fid): print(f"MOCKDB: delete_freight_forwarder {fid}"); return True

        def get_all_companies(self): print("MOCKDB: get_all_companies"); return [{"company_id": "c1", "company_name": "Mock Company Inc.", "is_default": True}]
        def get_personnel_for_company(self, cid, role=None): print(f"MOCKDB: get_personnel_for_company {cid}"); return [{"personnel_id": "p1", "name": "Mock User", "role": "Admin"}]
        def get_company_details(self, cid): print(f"MOCKDB: get_company_details {cid}"); return {"company_id": "c1", "company_name": "Mock Company Inc."}
        def initialize_database(self): print("MOCKDB: initialize_database")

        # Mock methods for module settings
        def __init__(self):
            print("MOCKDB: __init__")
            self.settings_cache = {} # Simple cache for mock settings

        def get_setting(self, key, default=None):
            print(f"MOCKDB: get_setting called for {key}, default: {default}")
            return self.settings_cache.get(key, default)

        def set_setting(self, key, value):
            print(f"MOCKDB: set_setting called for {key} with value {value}")
            self.settings_cache[key] = value
            return True

    # Crucially, make the global 'db_manager' this mock instance
    # This ensures SettingsPage uses this mock if its own 'import db' failed or was pre-empted.
    db_manager = MockDBManager()
    # print(f"MAIN_MID: Global db_manager is now {type(db_manager)}")

    # Mock dialogs to prevent them from trying to use real db_manager if they import it themselves
    class MockTransporterDialog(QDialog):
        def __init__(self, transporter_data=None, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Mock Transporter Dialog")
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("This is a Mock Transporter Dialog." + (" Editing mode." if transporter_data else " Adding mode.")))
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(self.accept)
            layout.addWidget(ok_button)
            print(f"MockTransporterDialog initialized. Data: {transporter_data}")
        # exec_ is inherited

    class MockFreightForwarderDialog(QDialog):
        def __init__(self, forwarder_data=None, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Mock Freight Forwarder Dialog")
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("This is a Mock Freight Forwarder Dialog." + (" Editing mode." if forwarder_data else " Adding mode.")))
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(self.accept)
            layout.addWidget(ok_button)
            print(f"MockFreightForwarderDialog initialized. Data: {forwarder_data}")

    # Monkey-patch the actual dialog imports if they are problematic during test
    # This is tricky because 'from X import Y' has already been processed for SettingsPage class
    # For this to work reliably for SettingsPage, these names would need to be re-resolved,
    # or SettingsPage imported *after* these patches.
    # However, if 'dialogs' itself isn't found, this won't help that part.
    # For now, let's assume the sys.path fix + db mock will allow 'dialogs' to be found.
    # If ModuleNotFoundError for 'dialogs' persists, then these patches are insufficient.
    # Corrected way to create mock modules for dialogs:
    mock_transporter_module = types.ModuleType(__name__ + '.mock_transporter_dialog')
    mock_transporter_module.TransporterDialog = MockTransporterDialog
    sys.modules['dialogs.transporter_dialog'] = mock_transporter_module

    mock_freight_forwarder_module = types.ModuleType(__name__ + '.mock_freight_forwarder_dialog')
    mock_freight_forwarder_module.FreightForwarderDialog = MockFreightForwarderDialog
    sys.modules['dialogs.freight_forwarder_dialog'] = mock_freight_forwarder_module

    # We also need to mock CompanyTabWidget if its import is failing or causing issues
    # from company_management import CompanyTabWidget
    class MockCompanyTabWidget(QWidget): # Ensure it's a QWidget
        def __init__(self, parent=None, app_root_dir=None, current_user_id=None):
            super().__init__(parent)
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(QLabel("Mock Company Tab Widget"))
            print("MOCK_COMPANY_TAB: Initialized")

    # If 'company_management' module itself failed to load, this global needs to be our mock:
    # This is highly dependent on how 'company_management' is imported and used.
    # For now, if 'from company_management import CompanyTabWidget' failed, this won't fix it
    # unless we also patch 'company_management' in sys.modules.
    # Let's assume 'company_management' module loads but we want to mock the class.
    # This is more for replacing the class rather than fixing ModuleNotFoundError for the module.
    # To fix ModuleNotFoundError for 'company_management', sys.path must be correct.
    # For now, we are assuming the script will find 'company_management' due to sys.path.
    # The global name 'CompanyTabWidget' will be used by SettingsPage.
    # We are not explicitly overriding the global 'CompanyTabWidget' here yet, relying on MockDBManager
    # and hoping the dialogs issue gets resolved first.


    app = QApplication(sys.argv)
    mock_config = {
        "templates_dir": "./templates_mock", "clients_dir": "./clients_mock", "language": "en",
        "default_reminder_days": 15, "session_timeout_minutes": 60, "database_path": "mock_app.db",
        "google_maps_review_url": "https://maps.google.com/mock", "show_initial_setup_on_startup": True,
        "smtp_server": "smtp.mock.com", "smtp_port": 587, "smtp_user": "mock_user", "smtp_password": "mock_password",
        "download_monitor_enabled": False,
        "download_monitor_path": os.path.join(os.path.expanduser('~'), 'Downloads_mock')
    }
    # Add default module settings to mock_config for testing _load_modules_tab_data if it were to use main_config
    # However, our implementation uses db_manager.get_setting, so we'll pre-populate the MockDBManager's cache.
    if db_manager: # Ensure db_manager (MockDBManager instance) exists
        # Pre-populate module settings for testing _load_modules_tab_data
        print("MAIN: Pre-populating MockDBManager with initial module states...")
        db_manager.set_setting("module_project_management_enabled", "True")  # String 'True'
        db_manager.set_setting("module_product_management_enabled", "False") # String 'False'
        db_manager.set_setting("module_partner_management_enabled", "True")
        db_manager.set_setting("module_statistics_enabled", "False")
        # module_inventory_management_enabled will use the default 'True' from _load_modules_tab_data
        db_manager.set_setting("module_botpress_integration_enabled", "True")
        # module_carrier_map_enabled will use the default 'True'
        db_manager.set_setting("module_camera_management_enabled", "True") # For testing the new module

    mock_app_root_dir = os.path.abspath(os.path.dirname(__file__))
    mock_current_user_id = "test_user_settings_main"

    # For CompanyTabWidget, ensure its db calls are also covered by MockDBManager
    # CompanyTabWidget might also need specific setup or its own mocks if it's complex.

    settings_window = SettingsPage(
        main_config=mock_config,
        app_root_dir=mock_app_root_dir,
        current_user_id=mock_current_user_id
    )
    settings_window.setGeometry(100, 100, 950, 750)
    settings_window.setWindowTitle("Settings Page Test - Transporters & Forwarders")
    settings_window.show()
    sys.exit(app.exec_())
