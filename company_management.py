import sys
import os
import shutil # For file operations
import uuid # For unique filenames
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox, QComboBox, QFileDialog, QStackedWidget,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QGridLayout
from contact_manager.sync_service import handle_contact_change_from_platform # For Google Sync

# Adjust path to import db_manager from the parent directory / current dir
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path: # for running directly if db.py is alongside
    sys.path.insert(0, current_dir)

try:
    from db import (
        add_company,
        get_company_by_id, # Though not explicitly listed as used, good for completeness if CompanyDialog uses it
        get_all_companies,
        update_company,
        delete_company,
        set_default_company,
        get_default_company, # For completeness
        add_company_personnel,
        get_personnel_for_company,
        update_company_personnel,
        delete_company_personnel,
        initialize_database
    )
    db_available = True
    print("Specific db functions imported successfully.")
except ImportError as e:
    print(f"Error importing specific db functions: {e}")
    db_available = False
    # Define fallbacks or ensure checks like 'if db_available:' are used around db calls
    def add_company(*args, **kwargs): print("DB function add_company unavailable"); return None
    def get_all_companies(*args, **kwargs): print("DB function get_all_companies unavailable"); return []
    def update_company(*args, **kwargs): print("DB function update_company unavailable"); return False
    def delete_company(*args, **kwargs): print("DB function delete_company unavailable"); return False
    def set_default_company(*args, **kwargs): print("DB function set_default_company unavailable"); return False
    def add_company_personnel(*args, **kwargs): print("DB function add_company_personnel unavailable"); return None
    def get_personnel_for_company(*args, **kwargs): print("DB function get_personnel_for_company unavailable"); return []
    def update_company_personnel(*args, **kwargs): print("DB function update_company_personnel unavailable"); return False
    def delete_company_personnel(*args, **kwargs): print("DB function delete_company_personnel unavailable"); return False
    def initialize_database(*args, **kwargs): print("DB function initialize_database unavailable"); pass

    print("Failed to import specific db functions. Some features will not work.")

# Define APP_ROOT_DIR
APP_ROOT_DIR = parent_dir

LOGO_SUBDIR = "company_logos"
DEFAULT_LOGO_SIZE = 128

ICON_PATH = os.path.join(APP_ROOT_DIR, "icons")
APP_STYLESHEET_PATH = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss")


class CompanyDialog(QDialog):
    def __init__(self, company_data=None, parent=None, app_root_dir=None):
        super().__init__(parent)
        self.company_data = company_data
        self.company_id = None
        self.logo_path_selected_for_upload = None
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR

        self.setWindowTitle(self.tr("Edit Company") if company_data else self.tr("Add Company"))
        self.setMinimumWidth(450)
        # ... (rest of CompanyDialog UI setup as before) ...
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.company_name_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setFixedHeight(60)
        self.payment_info_edit = QTextEdit()
        self.payment_info_edit.setFixedHeight(60)
        self.other_info_edit = QTextEdit()
        self.other_info_edit.setFixedHeight(60)

        self.logo_preview_label = QLabel(self.tr("No logo selected."))
        self.logo_preview_label.setFixedSize(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE)
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setObjectName("logoPreviewLabel")
        self.upload_logo_button = QPushButton(self.tr("Upload Logo"))
        self.upload_logo_button.setIcon(QIcon.fromTheme("document-open", QIcon(os.path.join(ICON_PATH, "eye.svg"))))
        self.upload_logo_button.clicked.connect(self.handle_upload_logo)

        layout.addRow(self.tr("Company Name:"), self.company_name_edit)
        layout.addRow(self.tr("Address:"), self.address_edit)
        layout.addRow(self.tr("Payment Info:"), self.payment_info_edit)
        layout.addRow(self.tr("Other Info:"), self.other_info_edit)

        logo_layout = QVBoxLayout()
        logo_layout.addWidget(self.logo_preview_label)
        logo_layout.addWidget(self.upload_logo_button)
        layout.addRow(self.tr("Logo:"), logo_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        if self.company_data:
            self.company_id = self.company_data.get('company_id')
            self.load_company_data()

    def load_company_data(self):
        # ... (load_company_data implementation as before) ...
        self.company_name_edit.setText(self.company_data.get('company_name', ''))
        self.address_edit.setPlainText(self.company_data.get('address', ''))
        self.payment_info_edit.setPlainText(self.company_data.get('payment_info', ''))
        self.other_info_edit.setPlainText(self.company_data.get('other_info', ''))
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path):
                pixmap = QPixmap(full_logo_path)
                self.logo_preview_label.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.logo_preview_label.setText(self.tr("Logo not found"))
        else:
            self.logo_preview_label.setText(self.tr("No logo"))


    def handle_upload_logo(self):
        # ... (handle_upload_logo implementation as before) ...
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Logo"), "", self.tr("Images (*.png *.jpg *.jpeg *.bmp)"))
        if file_path:
            self.logo_path_selected_for_upload = file_path
            pixmap = QPixmap(file_path)
            self.logo_preview_label.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self):
        # ... (accept implementation for CompanyDialog as before) ...
        if not db_available:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))
            return
        company_name = self.company_name_edit.text().strip()
        if not company_name:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Company name cannot be empty."))
            return
        data = {
            "company_name": company_name,
            "address": self.address_edit.toPlainText().strip(),
            "payment_info": self.payment_info_edit.toPlainText().strip(),
            "other_info": self.other_info_edit.toPlainText().strip(),
        }
        final_logo_rel_path = self.company_data.get('logo_path') if self.company_data else None
        if self.logo_path_selected_for_upload:
            logo_dir_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR)
            os.makedirs(logo_dir_full_path, exist_ok=True)
            _, ext = os.path.splitext(self.logo_path_selected_for_upload)
            identifier_for_filename = self.company_id if self.company_id else str(uuid.uuid4())
            unique_logo_filename = f"{identifier_for_filename}{ext}"
            target_logo_full_path = os.path.join(logo_dir_full_path, unique_logo_filename)
            try:
                shutil.copy(self.logo_path_selected_for_upload, target_logo_full_path)
                final_logo_rel_path = unique_logo_filename
            except Exception as e:
                QMessageBox.critical(self, self.tr("Logo Error"), self.tr("Could not save logo: {0}").format(str(e)))
                return
        data['logo_path'] = final_logo_rel_path
        if self.company_id:
            success = update_company(self.company_id, data)
            if success:
                QMessageBox.information(self, self.tr("Success"), self.tr("Company updated successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update company."))
        else:
            new_company_id = add_company(data)
            if new_company_id:
                if self.logo_path_selected_for_upload and not self.company_id:
                    temp_logo_filename = data.get('logo_path')
                    if temp_logo_filename: # Check if temp_logo_filename could be a UUID string
                        try:
                            is_uuid_filename = str(uuid.UUID(temp_logo_filename.rsplit('.',1)[0], version=4)) == temp_logo_filename.rsplit('.',1)[0]
                        except ValueError:
                            is_uuid_filename = False
                        if is_uuid_filename:
                            new_proper_filename = f"{new_company_id}{os.path.splitext(temp_logo_filename)[1]}"
                            old_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, temp_logo_filename)
                            new_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, new_proper_filename)
                            if os.path.exists(old_full_path):
                                try:
                                    os.rename(old_full_path, new_full_path)
                                    update_company(new_company_id, {'logo_path': new_proper_filename})
                                    print(f"Renamed logo from {temp_logo_filename} to {new_proper_filename}")
                                except Exception as e_rename:
                                    print(f"Error renaming logo after company creation: {e_rename}")
                QMessageBox.information(self, self.tr("Success"), self.tr("Company added successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add company."))


class PersonnelDialog(QDialog):
    def __init__(self, company_id, personnel_data=None, role_default="seller", parent=None, current_user_id=None): # Added current_user_id
        super().__init__(parent)
        self.company_id = company_id
        self.personnel_data = personnel_data
        self.personnel_id = None
        self.current_user_id = current_user_id # Store user_id for sync hooks

        self.setWindowTitle(self.tr("Edit Personnel") if personnel_data else self.tr("Add Personnel"))
        self.setMinimumWidth(350)
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["seller", "technical_manager", "other"])
        self.role_combo.setEditable(True)
        self.role_combo.setCurrentText(role_default)
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        layout.addRow(self.tr("Name:"), self.name_edit)
        layout.addRow(self.tr("Role:"), self.role_combo)
        layout.addRow(self.tr("Email:"), self.email_edit)
        layout.addRow(self.tr("Phone:"), self.phone_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        if self.personnel_data:
            self.personnel_id = self.personnel_data.get('personnel_id')
            self.load_personnel_data()

    def load_personnel_data(self):
        # ... (load_personnel_data implementation as before) ...
        self.name_edit.setText(self.personnel_data.get('name', ''))
        self.email_edit.setText(self.personnel_data.get('email', ''))
        self.phone_edit.setText(self.personnel_data.get('phone', ''))
        role = self.personnel_data.get('role', '')
        if role in ["seller", "technical_manager", "other"]:
            self.role_combo.setCurrentText(role)
        else:
            self.role_combo.setCurrentText("other")
            self.role_combo.lineEdit().setText(role)

    def accept(self):
        if not db_available:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))
            return

        name = self.name_edit.text().strip()
        role = self.role_combo.currentText().strip()
        email = self.email_edit.text().strip()
        phone = self.phone_edit.text().strip()

        if not name or not role:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Name and role cannot be empty."))
            return

        data = {"company_id": self.company_id, "name": name, "role": role, "email": email, "phone": phone}

        if self.personnel_id: # Editing
            success = update_company_personnel(self.personnel_id, data)
            if success:
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel updated successfully."))
                if hasattr(self, 'current_user_id') and self.current_user_id:
                    try:
                        handle_contact_change_from_platform(
                            user_id=str(self.current_user_id),
                            local_contact_id=str(self.personnel_id),
                            local_contact_type='company_personnel',
                            change_type='update'
                        )
                        print(f"Sync triggered for updated personnel: {self.personnel_id}")
                    except Exception as e:
                        print(f"Error triggering sync for updated personnel: {e}")
                else:
                    print("Warning: current_user_id not available in PersonnelDialog for update, sync not triggered.")
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update personnel."))
        else: # Adding
            new_personnel_id = add_company_personnel(data)
            if new_personnel_id:
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel added successfully."))
                if hasattr(self, 'current_user_id') and self.current_user_id:
                    try:
                        handle_contact_change_from_platform(
                            user_id=str(self.current_user_id),
                            local_contact_id=str(new_personnel_id),
                            local_contact_type='company_personnel',
                            change_type='create'
                        )
                        print(f"Sync triggered for new personnel: {new_personnel_id}")
                    except Exception as e:
                        print(f"Error triggering sync for new personnel: {e}")
                else:
                    print("Warning: current_user_id not available in PersonnelDialog for create, sync not triggered.")
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add personnel."))


class CompanyDetailsViewWidget(QWidget):
    # ... (CompanyDetailsViewWidget implementation as before, no changes needed for this subtask) ...
    def __init__(self, company_data, app_root_dir, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.app_root_dir = app_root_dir
        self.init_ui()
    def init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10,10,10,10); layout.setSpacing(8)
        self.name_label = QLabel(self.company_data.get('company_name', self.tr('N/A')))
        self.address_label = QLabel(self.company_data.get('address', self.tr('N/A')))
        self.payment_info_label = QLabel(self.company_data.get('payment_info', self.tr('N/A')))
        self.other_info_label = QLabel(self.company_data.get('other_info', self.tr('N/A')))
        self.logo_display = QLabel(); self.logo_display.setFixedSize(DEFAULT_LOGO_SIZE + 20, DEFAULT_LOGO_SIZE + 20)
        self.logo_display.setAlignment(Qt.AlignCenter); self.logo_display.setObjectName("logoDisplayLabel")
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path): self.logo_display.setPixmap(QPixmap(full_logo_path).scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else: self.logo_display.setText(self.tr("Logo not found"))
        else: self.logo_display.setText(self.tr("No Logo"))
        layout.addRow(self.tr("Name:"), self.name_label); layout.addRow(self.tr("Address:"), self.address_label)
        layout.addRow(self.tr("Payment Info:"), self.payment_info_label); layout.addRow(self.tr("Other Info:"), self.other_info_label)
        layout.addRow(self.tr("Logo:"), self.logo_display)
    def update_details(self, new_company_data):
        self.company_data = new_company_data
        self.name_label.setText(self.company_data.get('company_name', self.tr('N/A')))
        self.address_label.setText(self.company_data.get('address', self.tr('N/A')))
        self.payment_info_label.setText(self.company_data.get('payment_info', self.tr('N/A')))
        self.other_info_label.setText(self.company_data.get('other_info', self.tr('N/A')))
        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path): self.logo_display.setPixmap(QPixmap(full_logo_path).scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else: self.logo_display.setText(self.tr("Logo not found"))
        else: self.logo_display.setText(self.tr("No Logo"))


class CompanyTabWidget(QWidget):
    def __init__(self, parent=None, app_root_dir=None, current_user_id=None): # Added current_user_id
        super().__init__(parent)
        self.current_selected_company_id = None
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR
        self.current_user_id = current_user_id # Store user_id for sync hooks

        main_layout = QHBoxLayout(self)
        # ... (rest of CompanyTabWidget UI setup as before) ...
        left_panel_layout = QVBoxLayout()
        self.company_list_widget = QListWidget(); self.company_list_widget.itemClicked.connect(self.on_company_selected)
        self.add_company_button = QPushButton(self.tr("Add Company")); self.add_company_button.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_company_button.clicked.connect(self.handle_add_company)
        self.edit_company_button = QPushButton(self.tr("Edit Company")); self.edit_company_button.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_company_button.clicked.connect(self.handle_edit_company); self.edit_company_button.setEnabled(False)
        self.delete_company_button = QPushButton(self.tr("Delete Company")); self.delete_company_button.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_company_button.setObjectName("dangerButton"); self.delete_company_button.clicked.connect(self.handle_delete_company); self.delete_company_button.setEnabled(False)
        self.set_default_button = QPushButton(self.tr("Set as Default")); self.set_default_button.setIcon(QIcon.fromTheme("object-select", QIcon(os.path.join(ICON_PATH,"check.svg")))); self.set_default_button.clicked.connect(self.handle_set_default); self.set_default_button.setEnabled(False)
        left_panel_layout.addWidget(QLabel(self.tr("Companies:"))); left_panel_layout.addWidget(self.company_list_widget)
        company_button_grid = QGridLayout(); company_button_grid.addWidget(self.add_company_button, 0, 0); company_button_grid.addWidget(self.edit_company_button, 0, 1); company_button_grid.addWidget(self.delete_company_button, 1, 0); company_button_grid.addWidget(self.set_default_button, 1, 1)
        left_panel_layout.addLayout(company_button_grid)
        self.details_tabs = QTabWidget(); self.company_info_tab = QWidget(); self.company_info_layout = QVBoxLayout(self.company_info_tab); self.company_details_view = None; self.details_tabs.addTab(self.company_info_tab, self.tr("Company Info"))
        sellers_tab = QWidget(); sellers_layout = QVBoxLayout(sellers_tab); self.sellers_table = QTableWidget(); self.sellers_table.setColumnCount(2); self.sellers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Actions")]); self.sellers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.sellers_table.setEditTriggers(QAbstractItemView.NoEditTriggers); sellers_layout.addWidget(self.sellers_table)
        seller_btn_layout = QHBoxLayout(); self.add_seller_btn = QPushButton(self.tr("Add Seller")); self.add_seller_btn.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_seller_btn.clicked.connect(lambda: self.handle_add_personnel('seller')); self.edit_seller_btn = QPushButton(self.tr("Edit Seller")); self.edit_seller_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_seller_btn.clicked.connect(lambda: self.handle_edit_personnel('seller')); self.delete_seller_btn = QPushButton(self.tr("Delete Seller")); self.delete_seller_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_seller_btn.setObjectName("dangerButton"); self.delete_seller_btn.clicked.connect(lambda: self.handle_delete_personnel('seller'))
        seller_btn_layout.addWidget(self.add_seller_btn); seller_btn_layout.addWidget(self.edit_seller_btn); seller_btn_layout.addWidget(self.delete_seller_btn); sellers_layout.addLayout(seller_btn_layout); self.details_tabs.addTab(sellers_tab, self.tr("Sellers"))
        tech_managers_tab = QWidget(); tech_managers_layout = QVBoxLayout(tech_managers_tab); self.tech_managers_table = QTableWidget(); self.tech_managers_table.setColumnCount(2); self.tech_managers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Actions")]); self.tech_managers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.tech_managers_table.setEditTriggers(QAbstractItemView.NoEditTriggers); tech_managers_layout.addWidget(self.tech_managers_table)
        tech_btn_layout = QHBoxLayout(); self.add_tech_btn = QPushButton(self.tr("Add Manager")); self.add_tech_btn.setIcon(QIcon.fromTheme("list-add", QIcon(os.path.join(ICON_PATH,"plus.svg")))); self.add_tech_btn.clicked.connect(lambda: self.handle_add_personnel('technical_manager')); self.edit_tech_btn = QPushButton(self.tr("Edit Manager")); self.edit_tech_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg")))); self.edit_tech_btn.clicked.connect(lambda: self.handle_edit_personnel('technical_manager')); self.delete_tech_btn = QPushButton(self.tr("Delete Manager")); self.delete_tech_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); self.delete_tech_btn.setObjectName("dangerButton"); self.delete_tech_btn.clicked.connect(lambda: self.handle_delete_personnel('technical_manager'))
        tech_btn_layout.addWidget(self.add_tech_btn); tech_btn_layout.addWidget(self.edit_tech_btn); tech_btn_layout.addWidget(self.delete_tech_btn); tech_managers_layout.addLayout(tech_btn_layout); self.details_tabs.addTab(tech_managers_tab, self.tr("Technical Managers"))
        main_layout.addLayout(left_panel_layout, 1); main_layout.addWidget(self.details_tabs, 2)
        self.load_companies(); self.update_personnel_button_states(False)

    def load_companies(self):
        # ... (load_companies implementation as before) ...
        self.company_list_widget.clear()
        if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater(); self.company_details_view = None
        self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0); self.current_selected_company_id = None
        if not db_available: self.company_list_widget.addItem(QListWidgetItem(self.tr("Error: DB functions not available."))); return
        try:
            companies = get_all_companies()
            if not companies: self.company_list_widget.addItem(QListWidgetItem(self.tr("No companies found.")))
            for company in companies:
                item_text = company['company_name']
                if company.get('is_default'): item_text += self.tr(" (Default)")
                list_item = QListWidgetItem(item_text); list_item.setData(Qt.UserRole, company); self.company_list_widget.addItem(list_item)
        except Exception as e: self.company_list_widget.addItem(QListWidgetItem(self.tr("Error loading companies: {0}").format(str(e)))); print(f"Error in load_companies: {e}")
        self.update_company_button_states(); self.update_personnel_button_states(False)


    def on_company_selected(self, item):
        # ... (on_company_selected implementation as before) ...
        company_data = item.data(Qt.UserRole)
        if company_data:
            self.current_selected_company_id = company_data.get('company_id')
            if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater()
            self.company_details_view = CompanyDetailsViewWidget(company_data, self.app_root_dir); self.company_info_layout.addWidget(self.company_details_view)
            self.load_personnel(self.current_selected_company_id)
        else:
            self.current_selected_company_id = None
            if self.company_details_view: self.company_info_layout.removeWidget(self.company_details_view); self.company_details_view.deleteLater(); self.company_details_view = None
            self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0)
        self.update_company_button_states(); self.update_personnel_button_states(self.current_selected_company_id is not None)


    def handle_add_company(self):
        # ... (handle_add_company implementation as before) ...
        if not db_available: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available.")); return
        dialog = CompanyDialog(parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted: self.load_companies()

    def handle_edit_company(self):
        # ... (handle_edit_company implementation as before) ...
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Edit Company"), self.tr("Please select a company to edit.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole);
        if not company_data: return
        dialog = CompanyDialog(company_data=company_data, parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted:
            self.load_companies()
            for i in range(self.company_list_widget.count()): # Reselect
                list_item = self.company_list_widget.item(i); item_data = list_item.data(Qt.UserRole)
                if item_data and item_data.get('company_id') == self.current_selected_company_id:
                    self.company_list_widget.setCurrentItem(list_item); self.on_company_selected(list_item); break

    def handle_delete_company(self):
        # ... (handle_delete_company implementation as before) ...
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Delete Company"), self.tr("Please select a company to delete.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole)
        confirm = QMessageBox.warning(self, self.tr("Confirm Delete"), self.tr("Are you sure you want to delete {0}? This will also delete all associated personnel.").format(company_data.get('company_name')), QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if db_available:
                logo_rel_path = company_data.get('logo_path')
                if logo_rel_path:
                    full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
                    if os.path.exists(full_logo_path):
                        try: os.remove(full_logo_path); print(f"Deleted logo: {full_logo_path}")
                        except Exception as e_logo_del: QMessageBox.warning(self, self.tr("Logo Deletion Error"), self.tr("Could not delete logo file: {0}.\nPlease remove it manually.").format(str(e_logo_del)))
                if delete_company(self.current_selected_company_id): QMessageBox.information(self, self.tr("Success"), self.tr("Company deleted successfully.")); self.load_companies()
                else: QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete company from database."))
            else: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))

    def handle_set_default(self):
        # ... (handle_set_default implementation as before) ...
        if not self.current_selected_company_id: QMessageBox.information(self, self.tr("Set Default"), self.tr("Please select a company to set as default.")); return
        item = self.company_list_widget.currentItem();
        if not item: return
        company_data = item.data(Qt.UserRole)
        if db_available:
            if set_default_company(self.current_selected_company_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("'{0}' is now the default company.").format(company_data.get('company_name')))
                current_selection_row = self.company_list_widget.currentRow(); self.load_companies()
                if current_selection_row >=0 and current_selection_row < self.company_list_widget.count(): self.company_list_widget.setCurrentRow(current_selection_row); self.on_company_selected(self.company_list_widget.currentItem())
            else: QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to set default company."))
        else: QMessageBox.critical(self, self.tr("Error"), self.tr("Database functions not available."))

    def update_company_button_states(self):
        # ... (update_company_button_states implementation as before) ...
        has_selection = self.current_selected_company_id is not None
        self.edit_company_button.setEnabled(has_selection); self.delete_company_button.setEnabled(has_selection); self.set_default_button.setEnabled(has_selection)
        if has_selection:
            item = self.company_list_widget.currentItem()
            if item: company_data = item.data(Qt.UserRole)
            if company_data and company_data.get('is_default'): self.set_default_button.setEnabled(False)

    def update_personnel_button_states(self, company_selected: bool):
        # ... (update_personnel_button_states implementation as before) ...
        self.add_seller_btn.setEnabled(company_selected); self.add_tech_btn.setEnabled(company_selected)
        if not company_selected: self.edit_seller_btn.setEnabled(False); self.delete_seller_btn.setEnabled(False); self.edit_tech_btn.setEnabled(False); self.delete_tech_btn.setEnabled(False)

    def load_personnel(self, company_id):
        # ... (load_personnel implementation as before) ...
        self.sellers_table.setRowCount(0); self.tech_managers_table.setRowCount(0)
        if not db_available or not company_id: return
        try:
            sellers = get_personnel_for_company(company_id, role='seller'); self._populate_personnel_table(self.sellers_table, sellers)
            tech_managers = get_personnel_for_company(company_id, role='technical_manager'); self._populate_personnel_table(self.tech_managers_table, tech_managers)
            others_sellers = get_personnel_for_company(company_id, role='other_seller'); self._populate_personnel_table(self.sellers_table, others_sellers, append=True) # Example custom roles
            others_tech = get_personnel_for_company(company_id, role='other_technical_manager'); self._populate_personnel_table(self.tech_managers_table, others_tech, append=True)
        except Exception as e: QMessageBox.warning(self, self.tr("Personnel Error"), self.tr("Error loading personnel: {0}").format(str(e)))


    def _populate_personnel_table(self, table: QTableWidget, personnel_list: list, append=False):
        # ... (_populate_personnel_table implementation as before) ...
        if not append: table.setRowCount(0)
        for personnel in personnel_list:
            current_row = table.rowCount(); table.insertRow(current_row)
            name_item = QTableWidgetItem(personnel.get('name')); name_item.setData(Qt.UserRole, personnel); table.setItem(current_row, 0, name_item)
            btn_widget = QWidget(); btn_layout = QHBoxLayout(btn_widget)
            edit_btn = QPushButton(self.tr("Edit")); edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(os.path.join(ICON_PATH,"pencil.svg"))))
            # edit_btn.clicked.connect(...) # Connect these if actions from table rows are needed
            delete_btn = QPushButton(self.tr("Delete")); delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(os.path.join(ICON_PATH,"trash.svg")))); delete_btn.setObjectName("dangerButtonTable")
            # delete_btn.clicked.connect(...)
            btn_layout.addWidget(edit_btn); btn_layout.addWidget(delete_btn); btn_layout.setContentsMargins(0,0,0,0); table.setCellWidget(current_row, 1, btn_widget)
        table.resizeColumnsToContents()


    def handle_add_personnel(self, role_type: str):
        if not self.current_selected_company_id:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a company first."))
            return
        default_role = "seller" if role_type == 'seller' else "technical_manager"
        dialog = PersonnelDialog(
            company_id=self.current_selected_company_id,
            role_default=default_role,
            parent=self,
            current_user_id=getattr(self, 'current_user_id', None) # Pass current_user_id
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_personnel(self.current_selected_company_id)

    def handle_edit_personnel(self, role_type: str):
        table = self.sellers_table if role_type == 'seller' else self.tech_managers_table
        selected_row = table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a person to edit."))
            return
        item = table.item(selected_row, 0)
        if not item: return
        personnel_data = item.data(Qt.UserRole)
        dialog = PersonnelDialog(
            company_id=self.current_selected_company_id,
            personnel_data=personnel_data,
            parent=self,
            current_user_id=getattr(self, 'current_user_id', None) # Pass current_user_id
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_personnel(self.current_selected_company_id)

    def handle_delete_personnel(self, role_type: str):
        table = self.sellers_table if role_type == 'seller' else self.tech_managers_table
        selected_row = table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a person to delete."))
            return
        item = table.item(selected_row, 0)
        if not item: return
        personnel_data = item.data(Qt.UserRole)
        personnel_id = personnel_data.get('personnel_id')

        confirm = QMessageBox.warning(self, self.tr("Confirm Delete"),
                                      self.tr("Are you sure you want to delete {0}?").format(personnel_data.get('name')),
                                      QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            current_user_id_val = getattr(self, 'current_user_id', None)
            if current_user_id_val and personnel_id:
                try:
                    handle_contact_change_from_platform(
                        user_id=str(current_user_id_val),
                        local_contact_id=str(personnel_id),
                        local_contact_type='company_personnel',
                        change_type='delete'
                    )
                    print(f"Sync triggered for deleting personnel: {personnel_id}")
                except Exception as e:
                    print(f"Error triggering sync for deleting personnel: {e}")
            else:
                print("Warning: current_user_id or personnel_id not available in CompanyTabWidget for delete sync trigger.")

            if db_available and delete_company_personnel(personnel_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel deleted successfully."))
                self.load_personnel(self.current_selected_company_id)
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete personnel from database."))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # ... (stylesheet and db init as before) ...
    stylesheet_path_to_try = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss")
    try:
        if os.path.exists(stylesheet_path_to_try):
            with open(stylesheet_path_to_try, "r") as f: app.setStyleSheet(f.read())
        else: print(f"Stylesheet not found at {stylesheet_path_to_try}. Using default style.")
    except Exception as e: print(f"Error loading stylesheet: {e}")

    if db_available:
        try: initialize_database(); print("Database initialized by company_management.py (for testing if run directly).")
        except Exception as e: print(f"Error initializing database from company_management.py: {e}")
    else: print("db functions not available, skipping database initialization in company_management.py.")

    os.makedirs(os.path.join(APP_ROOT_DIR, LOGO_SUBDIR), exist_ok=True)

    # Example: Pass a mock current_user_id for testing CompanyTabWidget
    # main_window = CompanyTabWidget(app_root_dir=APP_ROOT_DIR, current_user_id="test_user_company_widget")
    main_window = CompanyTabWidget(app_root_dir=APP_ROOT_DIR) # Or without for basic UI
    main_window.setWindowTitle("Company Management")
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()
    sys.exit(app.exec_())
