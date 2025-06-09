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

# Adjust path to import db_manager from the parent directory / current dir
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path: # for running directly if db.py is alongside
    sys.path.insert(0, current_dir)

try:
    import db as db_manager
    print("db_manager imported successfully.")
except ImportError as e:
    print(f"Error importing db_manager: {e}")
    # Fallback for direct execution if db.py is in the same directory (e.g., during development)
    if parent_dir not in sys.path: # Redundant check but safe
        try:
            import db as db_manager
            print("db_manager imported successfully using direct path.")
        except ImportError:
            db_manager = None
            print("Failed to import db_manager. Some features will not work.")

# Define APP_ROOT_DIR, assuming this script is in a subdirectory of the app root
# For robust path handling, this might be better passed from main.py or configured globally
APP_ROOT_DIR = parent_dir # Default assumption
if not os.path.basename(APP_ROOT_DIR) == os.path.basename(os.path.dirname(os.path.realpath(sys.argv[0]))) and os.path.basename(current_dir) != os.path.basename(APP_ROOT_DIR):
    # This check is a bit heuristic. If main.py is in APP_ROOT_DIR, and this is in a subdir, parent_dir is correct.
    # If this script is run directly from its own directory, parent_dir might be one level too high if db.py is also there.
    # However, for imports, parent_dir is generally what we want for db.py if it's in APP_ROOT_DIR.
    # Let's assume main.py sets up a global APP_ROOT_DIR if needed, or this is okay for now.
    pass


LOGO_SUBDIR = "company_logos"
DEFAULT_LOGO_SIZE = 128 # For preview

# Placeholder for paths, adapt as needed if these are centralized
ICON_PATH = os.path.join(APP_ROOT_DIR, "icons") # Adjusted to use APP_ROOT_DIR
APP_STYLESHEET_PATH = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss") # Adjusted


class CompanyDialog(QDialog):
    def __init__(self, company_data=None, parent=None, app_root_dir=None):
        super().__init__(parent)
        self.company_data = company_data
        self.company_id = None
        self.logo_path_selected_for_upload = None # Temp storage for new logo path
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR # Use passed or default

        self.setWindowTitle(self.tr("Edit Company") if company_data else self.tr("Add Company"))
        self.setMinimumWidth(450)

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
        # self.logo_preview_label.setStyleSheet("border: 1px solid #ccc;") # Moved to QSS
        self.logo_preview_label.setObjectName("logoPreviewLabel")
        self.upload_logo_button = QPushButton(self.tr("Upload Logo"))
        self.upload_logo_button.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/eye.svg"))) # Example icon
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
        self.button_box.accepted.connect(self.accept) # Connected to self.accept
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        if self.company_data:
            self.company_id = self.company_data.get('company_id')
            self.load_company_data()

    def load_company_data(self):
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
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Logo"), "",
                                                   self.tr("Images (*.png *.jpg *.jpeg *.bmp)"))
        if file_path:
            self.logo_path_selected_for_upload = file_path
            pixmap = QPixmap(file_path)
            self.logo_preview_label.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self): # Overriding accept
        if not db_manager:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database manager not available."))
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
            # logo_path will be handled separately
        }

        final_logo_rel_path = self.company_data.get('logo_path') if self.company_data else None

        if self.logo_path_selected_for_upload:
            # Ensure logo directory exists
            logo_dir_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR)
            os.makedirs(logo_dir_full_path, exist_ok=True)

            # Create a unique filename for the logo
            _, ext = os.path.splitext(self.logo_path_selected_for_upload)
            # Use company_id if editing, or new uuid if adding, to ensure filename is unique and somewhat related
            identifier_for_filename = self.company_id if self.company_id else str(uuid.uuid4())
            unique_logo_filename = f"{identifier_for_filename}{ext}"
            target_logo_full_path = os.path.join(logo_dir_full_path, unique_logo_filename)

            try:
                shutil.copy(self.logo_path_selected_for_upload, target_logo_full_path)
                final_logo_rel_path = unique_logo_filename # Store relative path
            except Exception as e:
                QMessageBox.critical(self, self.tr("Logo Error"), self.tr("Could not save logo: {0}").format(str(e)))
                return # Or proceed without logo

        data['logo_path'] = final_logo_rel_path

        if self.company_id: # Editing existing company
            success = db_manager.update_company(self.company_id, data)
            if success:
                QMessageBox.information(self, self.tr("Success"), self.tr("Company updated successfully."))
                super().accept() # Call QDialog.accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update company."))
        else: # Adding new company
            new_company_id = db_manager.add_company(data)
            if new_company_id:
                # If a logo was uploaded and its name depended on company_id, rename it now if it used a placeholder
                if self.logo_path_selected_for_upload and not self.company_id: # means it was a new company
                    # Check if the logo was saved with a temporary UUID name and if data['logo_path'] reflects that
                    temp_logo_filename = data.get('logo_path')
                    if temp_logo_filename and str(uuid.UUID(temp_logo_filename.rsplit('.',1)[0], version=4)): # Heuristic check for UUID filename
                        new_proper_filename = f"{new_company_id}{os.path.splitext(temp_logo_filename)[1]}"
                        old_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, temp_logo_filename)
                        new_full_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, new_proper_filename)
                        if os.path.exists(old_full_path):
                            try:
                                os.rename(old_full_path, new_full_path)
                                db_manager.update_company(new_company_id, {'logo_path': new_proper_filename}) # Update DB with correct filename
                                print(f"Renamed logo from {temp_logo_filename} to {new_proper_filename}")
                            except Exception as e_rename:
                                print(f"Error renaming logo after company creation: {e_rename}")

                QMessageBox.information(self, self.tr("Success"), self.tr("Company added successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add company."))

    # get_data method is not strictly needed if accept() handles saving
    # but can be kept if dialog data is needed externally before accept (unlikely for this pattern)


class PersonnelDialog(QDialog):
    def __init__(self, company_id, personnel_data=None, role_default="seller", parent=None):
        super().__init__(parent)
        self.company_id = company_id # company_id of the company this personnel belongs to
        self.personnel_data = personnel_data
        self.personnel_id = None # For editing existing personnel

        self.setWindowTitle(self.tr("Edit Personnel") if personnel_data else self.tr("Add Personnel"))
        self.setMinimumWidth(350)
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.name_edit = QLineEdit()

        self.role_combo = QComboBox()
        self.role_combo.addItems(["seller", "technical_manager", "other"]) # Predefined roles
        self.role_combo.setEditable(True) # Allow custom roles
        self.role_combo.setCurrentText(role_default)


        layout.addRow(self.tr("Name:"), self.name_edit)
        layout.addRow(self.tr("Role:"), self.role_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept) # Connected to self.accept
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        if self.personnel_data:
            self.personnel_id = self.personnel_data.get('personnel_id')
            self.load_personnel_data()

    def load_personnel_data(self):
        self.name_edit.setText(self.personnel_data.get('name', ''))
        role = self.personnel_data.get('role', '')
        if role in ["seller", "technical_manager", "other"]:
            self.role_combo.setCurrentText(role)
        else:
            self.role_combo.setCurrentText("other") # Or set to the custom role directly
            self.role_combo.lineEdit().setText(role) # If it's a custom role not in list


    def accept(self): # Overriding accept
        if not db_manager:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database manager not available."))
            return

        name = self.name_edit.text().strip()
        role = self.role_combo.currentText().strip()

        if not name or not role:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Name and role cannot be empty."))
            return

        data = {
            "company_id": self.company_id,
            "name": name,
            "role": role
        }

        if self.personnel_id: # Editing
            success = db_manager.update_company_personnel(self.personnel_id, data)
            if success:
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel updated successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update personnel."))
        else: # Adding
            new_personnel_id = db_manager.add_company_personnel(data)
            if new_personnel_id:
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel added successfully."))
                super().accept()
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add personnel."))

    # get_data method is not strictly needed if accept() handles saving


class CompanyDetailsViewWidget(QWidget):
    """Displays company details and logo."""
    def __init__(self, company_data, app_root_dir, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.app_root_dir = app_root_dir
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(8)

        self.name_label = QLabel(self.company_data.get('company_name', self.tr('N/A')))
        self.address_label = QLabel(self.company_data.get('address', self.tr('N/A')))
        self.payment_info_label = QLabel(self.company_data.get('payment_info', self.tr('N/A')))
        self.other_info_label = QLabel(self.company_data.get('other_info', self.tr('N/A')))

        self.logo_display = QLabel()
        self.logo_display.setFixedSize(DEFAULT_LOGO_SIZE + 20, DEFAULT_LOGO_SIZE + 20) # Slightly larger for padding
        self.logo_display.setAlignment(Qt.AlignCenter)
        # self.logo_display.setStyleSheet("border: 1px solid #ddd; padding: 5px;") # Moved to QSS
        self.logo_display.setObjectName("logoDisplayLabel")

        logo_rel_path = self.company_data.get('logo_path')
        if logo_rel_path:
            full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
            if os.path.exists(full_logo_path):
                pixmap = QPixmap(full_logo_path)
                self.logo_display.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.logo_display.setText(self.tr("Logo not found"))
        else:
            self.logo_display.setText(self.tr("No Logo"))

        layout.addRow(self.tr("Name:"), self.name_label)
        layout.addRow(self.tr("Address:"), self.address_label)
        layout.addRow(self.tr("Payment Info:"), self.payment_info_label)
        layout.addRow(self.tr("Other Info:"), self.other_info_label)
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
            if os.path.exists(full_logo_path):
                pixmap = QPixmap(full_logo_path)
                self.logo_display.setPixmap(pixmap.scaled(DEFAULT_LOGO_SIZE, DEFAULT_LOGO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.logo_display.setText(self.tr("Logo not found"))
        else:
            self.logo_display.setText(self.tr("No Logo"))


class CompanyTabWidget(QWidget):
    def __init__(self, parent=None, app_root_dir=None): # app_root_dir can be passed from main
        super().__init__(parent)
        self.current_selected_company_id = None
        self.app_root_dir = app_root_dir if app_root_dir else APP_ROOT_DIR # Use passed or default

        main_layout = QHBoxLayout(self)

        # Left Panel
        left_panel_layout = QVBoxLayout()

        self.company_list_widget = QListWidget()
        self.company_list_widget.itemClicked.connect(self.on_company_selected) # Renamed for clarity

        self.add_company_button = QPushButton(self.tr("Add Company"))
        self.add_company_button.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg")))
        self.add_company_button.clicked.connect(self.handle_add_company)

        self.edit_company_button = QPushButton(self.tr("Edit Company"))
        self.edit_company_button.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
        self.edit_company_button.clicked.connect(self.handle_edit_company)
        self.edit_company_button.setEnabled(False)

        self.delete_company_button = QPushButton(self.tr("Delete Company"))
        self.delete_company_button.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg")))
        self.delete_company_button.setObjectName("dangerButton")
        self.delete_company_button.clicked.connect(self.handle_delete_company)
        self.delete_company_button.setEnabled(False)

        self.set_default_button = QPushButton(self.tr("Set as Default"))
        self.set_default_button.setIcon(QIcon.fromTheme("object-select", QIcon(":/icons/check.svg"))) # Example, could be star
        self.set_default_button.clicked.connect(self.handle_set_default)
        self.set_default_button.setEnabled(False)

        left_panel_layout.addWidget(QLabel(self.tr("Companies:")))
        left_panel_layout.addWidget(self.company_list_widget)

        company_button_grid = QGridLayout()
        company_button_grid.addWidget(self.add_company_button, 0, 0)
        company_button_grid.addWidget(self.edit_company_button, 0, 1)
        company_button_grid.addWidget(self.delete_company_button, 1, 0)
        company_button_grid.addWidget(self.set_default_button, 1, 1)
        left_panel_layout.addLayout(company_button_grid)


        # Right Panel - Tabbed Interface
        self.details_tabs = QTabWidget()

        # Company Info Tab
        self.company_info_tab = QWidget()
        # self.company_details_view will be an instance of CompanyDetailsViewWidget or similar
        self.company_info_layout = QVBoxLayout(self.company_info_tab)
        self.company_details_view = None # Will be created on company selection
        self.details_tabs.addTab(self.company_info_tab, self.tr("Company Info"))

        # Sellers Tab
        sellers_tab = QWidget()
        sellers_layout = QVBoxLayout(sellers_tab)
        self.sellers_table = QTableWidget()
        self.sellers_table.setColumnCount(2) # Name, Actions
        self.sellers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Actions")])
        self.sellers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sellers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        sellers_layout.addWidget(self.sellers_table)
        seller_btn_layout = QHBoxLayout()
        self.add_seller_btn = QPushButton(self.tr("Add Seller")); self.add_seller_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg"))); self.add_seller_btn.clicked.connect(lambda: self.handle_add_personnel('seller'))
        self.edit_seller_btn = QPushButton(self.tr("Edit Seller")); self.edit_seller_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg"))); self.edit_seller_btn.clicked.connect(lambda: self.handle_edit_personnel('seller'))
        self.delete_seller_btn = QPushButton(self.tr("Delete Seller")); self.delete_seller_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg"))); self.delete_seller_btn.setObjectName("dangerButton"); self.delete_seller_btn.clicked.connect(lambda: self.handle_delete_personnel('seller'))
        seller_btn_layout.addWidget(self.add_seller_btn); seller_btn_layout.addWidget(self.edit_seller_btn); seller_btn_layout.addWidget(self.delete_seller_btn)
        sellers_layout.addLayout(seller_btn_layout)
        self.details_tabs.addTab(sellers_tab, self.tr("Sellers"))

        # Technical Managers Tab
        tech_managers_tab = QWidget()
        tech_managers_layout = QVBoxLayout(tech_managers_tab)
        self.tech_managers_table = QTableWidget()
        self.tech_managers_table.setColumnCount(2) # Name, Actions
        self.tech_managers_table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Actions")])
        self.tech_managers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tech_managers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tech_managers_layout.addWidget(self.tech_managers_table)
        tech_btn_layout = QHBoxLayout()
        self.add_tech_btn = QPushButton(self.tr("Add Manager")); self.add_tech_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg"))); self.add_tech_btn.clicked.connect(lambda: self.handle_add_personnel('technical_manager'))
        self.edit_tech_btn = QPushButton(self.tr("Edit Manager")); self.edit_tech_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg"))); self.edit_tech_btn.clicked.connect(lambda: self.handle_edit_personnel('technical_manager'))
        self.delete_tech_btn = QPushButton(self.tr("Delete Manager")); self.delete_tech_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg"))); self.delete_tech_btn.setObjectName("dangerButton"); self.delete_tech_btn.clicked.connect(lambda: self.handle_delete_personnel('technical_manager'))
        tech_btn_layout.addWidget(self.add_tech_btn); tech_btn_layout.addWidget(self.edit_tech_btn); tech_btn_layout.addWidget(self.delete_tech_btn)
        tech_managers_layout.addLayout(tech_btn_layout)
        self.details_tabs.addTab(tech_managers_tab, self.tr("Technical Managers"))

        # Add panels to main layout
        main_layout.addLayout(left_panel_layout, 1)
        main_layout.addWidget(self.details_tabs, 2)

        self.load_companies()
        self.update_personnel_button_states(False) # Disable personnel buttons initially

    def load_companies(self):
        self.company_list_widget.clear()
        # Clear right panel if no company is selected after reload
        if self.company_details_view:
            self.company_info_layout.removeWidget(self.company_details_view)
            self.company_details_view.deleteLater()
            self.company_details_view = None
        self.sellers_table.setRowCount(0)
        self.tech_managers_table.setRowCount(0)
        self.current_selected_company_id = None


        if not db_manager:
            self.company_list_widget.addItem(QListWidgetItem(self.tr("Error: DB Manager not loaded.")))
            return
        try:
            companies = db_manager.get_all_companies()
            if not companies:
                self.company_list_widget.addItem(QListWidgetItem(self.tr("No companies found.")))
            for company in companies:
                item_text = company['company_name']
                if company.get('is_default'):
                    item_text += self.tr(" (Default)")
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, company)
                self.company_list_widget.addItem(list_item)
        except Exception as e:
            self.company_list_widget.addItem(QListWidgetItem(self.tr("Error loading companies: {0}").format(str(e))))
            print(f"Error in load_companies: {e}")

        self.update_company_button_states()
        self.update_personnel_button_states(False)


    def on_company_selected(self, item):
        company_data = item.data(Qt.UserRole)
        if company_data:
            self.current_selected_company_id = company_data.get('company_id')

            # Update Company Info Tab
            if self.company_details_view: # Remove old view if exists
                self.company_info_layout.removeWidget(self.company_details_view)
                self.company_details_view.deleteLater()

            self.company_details_view = CompanyDetailsViewWidget(company_data, self.app_root_dir)
            self.company_info_layout.addWidget(self.company_details_view)

            self.load_personnel(self.current_selected_company_id)

        else:
            self.current_selected_company_id = None
            if self.company_details_view:
                self.company_info_layout.removeWidget(self.company_details_view)
                self.company_details_view.deleteLater()
                self.company_details_view = None
            self.sellers_table.setRowCount(0)
            self.tech_managers_table.setRowCount(0)

        self.update_company_button_states()
        self.update_personnel_button_states(self.current_selected_company_id is not None)


    def handle_add_company(self):
        if not db_manager:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Database manager not available."))
            return

        dialog = CompanyDialog(parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted: # dialog.accept() now handles saving
            self.load_companies()
            # Optionally, select the newly added company if its ID is returned/known

    def handle_edit_company(self):
        if not self.current_selected_company_id:
            QMessageBox.information(self, self.tr("Edit Company"), self.tr("Please select a company to edit."))
            return

        item = self.company_list_widget.currentItem()
        if not item: return

        company_data = item.data(Qt.UserRole)
        if not company_data: return

        dialog = CompanyDialog(company_data=company_data, parent=self, app_root_dir=self.app_root_dir)
        if dialog.exec_() == QDialog.Accepted:
            self.load_companies()
            # Re-select or refresh details for the edited company
            # This might require finding the item by ID again if list order changes
            for i in range(self.company_list_widget.count()):
                list_item = self.company_list_widget.item(i)
                item_data = list_item.data(Qt.UserRole)
                if item_data and item_data.get('company_id') == self.current_selected_company_id:
                    self.company_list_widget.setCurrentItem(list_item)
                    self.on_company_selected(list_item) # Refresh details
                    break


    def handle_delete_company(self):
        if not self.current_selected_company_id:
            QMessageBox.information(self, self.tr("Delete Company"), self.tr("Please select a company to delete."))
            return
        item = self.company_list_widget.currentItem()
        if not item: return
        company_data = item.data(Qt.UserRole)

        confirm = QMessageBox.warning(self, self.tr("Confirm Delete"),
                                      self.tr("Are you sure you want to delete {0}? This will also delete all associated personnel.").format(company_data.get('company_name')),
                                      QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if db_manager:
                # Attempt to delete logo file first
                logo_rel_path = company_data.get('logo_path')
                if logo_rel_path:
                    full_logo_path = os.path.join(self.app_root_dir, LOGO_SUBDIR, logo_rel_path)
                    if os.path.exists(full_logo_path):
                        try:
                            os.remove(full_logo_path)
                            print(f"Deleted logo: {full_logo_path}")
                        except Exception as e_logo_del:
                            QMessageBox.warning(self, self.tr("Logo Deletion Error"), self.tr("Could not delete logo file: {0}.\nPlease remove it manually.").format(str(e_logo_del)))

                if db_manager.delete_company(self.current_selected_company_id):
                    QMessageBox.information(self, self.tr("Success"), self.tr("Company deleted successfully."))
                    self.load_companies() # This will clear selection and details
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete company from database."))
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Database manager not available."))


    def handle_set_default(self):
        if not self.current_selected_company_id:
            QMessageBox.information(self, self.tr("Set Default"), self.tr("Please select a company to set as default."))
            return
        item = self.company_list_widget.currentItem()
        if not item: return
        company_data = item.data(Qt.UserRole)

        if db_manager:
            if db_manager.set_default_company(self.current_selected_company_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("'{0}' is now the default company.").format(company_data.get('company_name')))
                current_selection_row = self.company_list_widget.currentRow()
                self.load_companies()
                if current_selection_row >=0 and current_selection_row < self.company_list_widget.count():
                     self.company_list_widget.setCurrentRow(current_selection_row) # Try to reselect
                     self.on_company_selected(self.company_list_widget.currentItem())

            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to set default company."))
        else:
             QMessageBox.critical(self, self.tr("Error"), self.tr("Database manager not available."))

    def update_company_button_states(self):
        has_selection = self.current_selected_company_id is not None
        self.edit_company_button.setEnabled(has_selection)
        self.delete_company_button.setEnabled(has_selection)
        self.set_default_button.setEnabled(has_selection)

        if has_selection:
            item = self.company_list_widget.currentItem()
            if item:
                company_data = item.data(Qt.UserRole)
                if company_data and company_data.get('is_default'):
                    self.set_default_button.setEnabled(False)

    def update_personnel_button_states(self, company_selected: bool):
        # Enable Add buttons if a company is selected
        self.add_seller_btn.setEnabled(company_selected)
        self.add_tech_btn.setEnabled(company_selected)

        # Edit/Delete depend on table selection, handle in table selection changed signals
        # For now, disable them if no company is selected
        if not company_selected:
            self.edit_seller_btn.setEnabled(False)
            self.delete_seller_btn.setEnabled(False)
            self.edit_tech_btn.setEnabled(False)
            self.delete_tech_btn.setEnabled(False)


    def load_personnel(self, company_id):
        self.sellers_table.setRowCount(0)
        self.tech_managers_table.setRowCount(0)
        if not db_manager or not company_id:
            return

        try:
            sellers = db_manager.get_personnel_for_company(company_id, role='seller')
            self._populate_personnel_table(self.sellers_table, sellers)

            tech_managers = db_manager.get_personnel_for_company(company_id, role='technical_manager')
            self._populate_personnel_table(self.tech_managers_table, tech_managers)

            # Also load 'other' roles into one of the tables or a separate one if needed
            others_sellers = db_manager.get_personnel_for_company(company_id, role='other_seller') # Example for custom roles
            self._populate_personnel_table(self.sellers_table, others_sellers, append=True)
            others_tech = db_manager.get_personnel_for_company(company_id, role='other_technical_manager')
            self._populate_personnel_table(self.tech_managers_table, others_tech, append=True)


        except Exception as e:
            QMessageBox.warning(self, self.tr("Personnel Error"), self.tr("Error loading personnel: {0}").format(str(e)))

    def _populate_personnel_table(self, table: QTableWidget, personnel_list: list, append=False):
        if not append:
            table.setRowCount(0)

        for personnel in personnel_list:
            current_row = table.rowCount()
            table.insertRow(current_row)

            name_item = QTableWidgetItem(personnel.get('name'))
            name_item.setData(Qt.UserRole, personnel) # Store full data
            table.setItem(current_row, 0, name_item)

            # Placeholder for action buttons in personnel table
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            edit_btn = QPushButton(self.tr("Edit")); edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            # edit_btn.clicked.connect(lambda checked, p=personnel, t=table: self.handle_edit_personnel_from_table(p, t))
            delete_btn = QPushButton(self.tr("Delete")); delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg"))); delete_btn.setObjectName("dangerButtonTable") # Different object name for specific table button styling if needed
            # delete_btn.clicked.connect(lambda checked, pid=personnel.get('personnel_id'), t=table: self.handle_delete_personnel_from_table(pid, t))
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(current_row, 1, btn_widget)
        table.resizeColumnsToContents()

    def handle_add_personnel(self, role_type: str):
        if not self.current_selected_company_id:
            QMessageBox.warning(self, self.tr("Selection Error"), self.tr("Please select a company first."))
            return

        default_role = "seller"
        if role_type == 'technical_manager':
            default_role = "technical_manager"

        dialog = PersonnelDialog(company_id=self.current_selected_company_id, role_default=default_role, parent=self)
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

        dialog = PersonnelDialog(company_id=self.current_selected_company_id, personnel_data=personnel_data, parent=self)
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
            if db_manager and db_manager.delete_company_personnel(personnel_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Personnel deleted successfully."))
                self.load_personnel(self.current_selected_company_id)
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete personnel."))


if __name__ == '__main__':
    # This basic setup is for testing CompanyTabWidget independently.
    # For full APP_ROOT_DIR consistency, run from main.py or ensure paths are correctly set.
    if APP_ROOT_DIR == parent_dir and os.path.basename(current_dir) != os.path.basename(APP_ROOT_DIR) : # If APP_ROOT_DIR is parent, use current_dir for local test files
        # This is a heuristic: if db.py is in current_dir, and APP_ROOT_DIR was set to parent_dir
        # then for local resource loading (like a dummy DB), current_dir might be more appropriate.
        # This is tricky. Best is to have a robust global config for APP_ROOT_DIR.
        # For now, we'll assume APP_ROOT_DIR calculation is okay for loading db.py from parent.
        pass

    app = QApplication(sys.argv)

    # Attempt to load stylesheet
    stylesheet_path_to_try = os.path.join(APP_ROOT_DIR, "styles", "stylesheet.qss") # Use APP_ROOT_DIR
    try:
        if os.path.exists(stylesheet_path_to_try):
            with open(stylesheet_path_to_try, "r") as f:
                app.setStyleSheet(f.read())
        else:
            print(f"Stylesheet not found at {stylesheet_path_to_try}. Using default style.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    # Initialize database if db_manager is available
    if db_manager:
        try:
            db_manager.initialize_database()
            print("Database initialized by company_management.py (for testing if run directly).")
        except Exception as e:
            print(f"Error initializing database from company_management.py: {e}")
    else:
        print("db_manager not available, skipping database initialization in company_management.py.")

    # Create the company_logos directory for standalone testing
    os.makedirs(os.path.join(APP_ROOT_DIR, LOGO_SUBDIR), exist_ok=True)

    main_window = CompanyTabWidget(app_root_dir=APP_ROOT_DIR) # Pass APP_ROOT_DIR
    main_window.setWindowTitle("Company Management")
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()

    sys.exit(app.exec_())
