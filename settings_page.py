# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QLabel,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QFileDialog, QCheckBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox, QDialog # Added QDialog for dialog.exec_()
)
from PyQt5.QtGui import QIcon # Added for icons on buttons
from PyQt5.QtCore import Qt

# Assuming db_manager provides the necessary functions directly or via submodules
# This import will be problematic if 'db' is not in sys.path or structured as expected.
# For the __main__ block, we'll mock it.
try:
    import db as db_manager
except ImportError:
    db_manager = None # Will be replaced by mock in __main__ if None

from dialogs.transporter_dialog import TransporterDialog
from dialogs.freight_forwarder_dialog import FreightForwarderDialog
from company_management import CompanyTabWidget

class SettingsPage(QWidget):
    def __init__(self, main_config, app_root_dir, current_user_id, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.main_config = main_config
        self.app_root_dir = app_root_dir
        self.current_user_id = current_user_id

        # This is important if db_manager was not imported successfully above
        # And we are not running the __main__ block (e.g. in actual app)
        # It relies on the global db_manager being set by the main application
        global db_manager
        if db_manager is None and 'db_manager' in globals() and globals()['db_manager'] is not None:
             # Potentially set by main_app.py or similar if running integrated
            pass # db_manager already set globally
        elif db_manager is None :
            # This will cause issues if not mocked and not running __main__
            print("WARNING: db_manager is None in SettingsPage init and not running __main__")


        main_layout = QVBoxLayout(self)
        title_label = QLabel(self.tr("Application Settings"))
        title_label.setObjectName("pageTitleLabel")
        title_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title_label)

        self.tabs_widget = QTabWidget()
        self.tabs_widget.setObjectName("settingsTabs")

        self._setup_general_tab()
        self._setup_email_tab()
        self._setup_download_monitor_tab() # New Download Monitor Tab

        self.company_tab = CompanyTabWidget(
            parent=self,
            app_root_dir=self.app_root_dir,
            current_user_id=self.current_user_id
        )
        self.tabs_widget.addTab(self.company_tab, self.tr("Company & Personnel"))

        self._setup_transporters_tab() # New
        self._setup_freight_forwarders_tab() # New

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
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.reload_settings_button)
        buttons_layout.addWidget(self.restore_defaults_button)
        buttons_layout.addWidget(self.save_settings_button)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

        self._load_all_settings_from_config()
        if db_manager: # Only load if db_manager is available (real or mocked)
            self._load_transporters_table() # Initial load
            self._load_forwarders_table() # Initial load
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
        if not os.path.isdir(start_dir):
            start_dir = os.path.expanduser('~') # Default to home or a sensible default

        dir_path = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Monitored Folder"),
            start_dir
        )
        if dir_path:
            self.download_monitor_path_input.setText(dir_path)

    def _setup_transporters_tab(self):
        transporters_tab = QWidget()
        transporters_layout = QVBoxLayout(transporters_tab)
        self.transporters_table = QTableWidget()
        self.transporters_table.setColumnCount(6) # ID, Name, Contact, Phone, Email, Service Area
        self.transporters_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Name"), self.tr("Contact Person"), self.tr("Phone"), self.tr("Email"), self.tr("Service Area")])
        self.transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transporters_table.horizontalHeader().setStretchLastSection(True)
        self.transporters_table.hideColumn(0) # Hide ID column
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
        dialog = TransporterDialog(parent=self) # db_manager is used inside the dialog
        if dialog.exec_() == QDialog.Accepted:
            self._load_transporters_table()

    def _handle_edit_transporter(self):
        if not db_manager: return
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        transporter_id = self.transporters_table.item(selected_items[0].row(), 0).text()
        transporter_data = db_manager.get_transporter_by_id(transporter_id)
        if transporter_data:
            dialog = TransporterDialog(transporter_data=transporter_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self._load_transporters_table()
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Transporter not found."))

    def _handle_delete_transporter(self):
        if not db_manager: return
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        transporter_id = self.transporters_table.item(selected_items[0].row(), 0).text()
        transporter_name = self.transporters_table.item(selected_items[0].row(), 1).text()

        reply = QMessageBox.question(self, self.tr("Confirm Delete"),
                                     self.tr("Are you sure you want to delete transporter '{0}'?").format(transporter_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_transporter(transporter_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Transporter deleted."))
                self._load_transporters_table()
            else:
                QMessageBox.warning(self, self.tr("DB Error"), self.tr("Could not delete transporter."))

    def _update_transporter_button_states(self):
        has_selection = bool(self.transporters_table.selectedItems())
        self.edit_transporter_btn.setEnabled(has_selection)
        self.delete_transporter_btn.setEnabled(has_selection)

    def _setup_freight_forwarders_tab(self):
        forwarders_tab = QWidget()
        forwarders_layout = QVBoxLayout(forwarders_tab)
        self.forwarders_table = QTableWidget()
        self.forwarders_table.setColumnCount(6) # ID, Name, Contact, Phone, Email, Services Offered
        self.forwarders_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Name"), self.tr("Contact Person"), self.tr("Phone"), self.tr("Email"), self.tr("Services Offered")])
        self.forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.forwarders_table.horizontalHeader().setStretchLastSection(True)
        self.forwarders_table.hideColumn(0) # Hide ID column
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
        if dialog.exec_() == QDialog.Accepted:
            self._load_forwarders_table()

    def _handle_edit_forwarder(self):
        if not db_manager: return
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        forwarder_id = self.forwarders_table.item(selected_items[0].row(), 0).text()
        forwarder_data = db_manager.get_freight_forwarder_by_id(forwarder_id)
        if forwarder_data:
            dialog = FreightForwarderDialog(forwarder_data=forwarder_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self._load_forwarders_table()
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Freight Forwarder not found."))

    def _handle_delete_forwarder(self):
        if not db_manager: return
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        forwarder_id = self.forwarders_table.item(selected_items[0].row(), 0).text()
        forwarder_name = self.forwarders_table.item(selected_items[0].row(), 1).text()

        reply = QMessageBox.question(self, self.tr("Confirm Delete"),
                                     self.tr("Are you sure you want to delete freight forwarder '{0}'?").format(forwarder_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_freight_forwarder(forwarder_id):
                QMessageBox.information(self, self.tr("Success"), self.tr("Freight Forwarder deleted."))
                self._load_forwarders_table()
            else:
                QMessageBox.warning(self, self.tr("DB Error"), self.tr("Could not delete freight forwarder."))

    def _update_forwarder_button_states(self):
        has_selection = bool(self.forwarders_table.selectedItems())
        self.edit_forwarder_btn.setEnabled(has_selection)
        self.delete_forwarder_btn.setEnabled(has_selection)

    def _load_general_tab_data(self):
        self.templates_dir_input.setText(self.main_config.get("templates_dir", ""))
        self.clients_dir_input.setText(self.main_config.get("clients_dir", ""))
        # Ensure new keys are present with defaults if missing from config
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
        return {
            "download_monitor_enabled": self.download_monitor_enabled_checkbox.isChecked(),
            "download_monitor_path": self.download_monitor_path_input.text().strip()
        }

    def _load_all_settings_from_config(self):
        self._load_general_tab_data() # This now also ensures defaults for download monitor keys
        self._load_email_tab_data()
        self._load_download_monitor_tab_data() # Load the data for the new tab
        # Transporter and Forwarder data are loaded from DB directly, not from main_config.
        # Reloading them here would mean re-querying the DB. This might be desired if underlying DB could change.
        # For now, let's assume their initial load in __init__ is sufficient unless explicitly reloaded.
        # If a "refresh data" button was present on those tabs, it would call their respective _load_*_table methods.
        print("SettingsPage: General and Email settings reloaded from main_config.")

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # Mock db_manager for standalone testing
    class MockDBManager:
        def get_all_transporters(self): return [{"transporter_id": "t1", "name": "Mock Transporter 1", "contact_person": "John T", "phone": "123", "email": "jt@example.com", "service_area": "Local"}, {"transporter_id": "t2", "name": "Mock Transporter 2", "contact_person": "Alice T", "phone": "456", "email": "at@example.com", "service_area": "National"}]
        def get_transporter_by_id(self, tid): return {"transporter_id": tid, "name": f"Mock Transporter {tid}", "contact_person":"Test", "phone":"Test", "email":"Test", "service_area":"Test"} if tid in ["t1", "t2"] else None
        def add_transporter(self, data): print(f"Mock add_transporter: {data}"); return "t_new_mock_id" # In reality, this would return the ID from the DB
        def update_transporter(self, tid, data): print(f"Mock update_transporter {tid}: {data}"); return True
        def delete_transporter(self, tid): print(f"Mock delete_transporter {tid}"); return True

        def get_all_freight_forwarders(self): return [{"forwarder_id": "f1", "name": "Mock Forwarder 1", "contact_person": "Jane F", "phone": "456", "email": "jf@example.com", "services_offered": "Global"}, {"forwarder_id": "f2", "name": "Mock Forwarder 2", "contact_person": "Bob F", "phone": "789", "email": "bf@example.com", "services_offered": "Air, Sea"}]
        def get_freight_forwarder_by_id(self, fid): return {"forwarder_id": fid, "name": f"Mock Forwarder {fid}", "contact_person":"Test", "phone":"Test", "email":"Test", "services_offered":"Test"} if fid in ["f1", "f2"] else None
        def add_freight_forwarder(self, data): print(f"Mock add_freight_forwarder: {data}"); return "f_new_mock_id"
        def update_freight_forwarder(self, fid, data): print(f"Mock update_freight_forwarder {fid}: {data}"); return True
        def delete_freight_forwarder(self, fid): print(f"Mock delete_freight_forwarder {fid}"); return True

        def get_all_companies(self): return [{"company_id": "c1", "company_name": "Mock Company Inc.", "is_default": True}]
        def get_personnel_for_company(self, cid, role=None): return [{"personnel_id": "p1", "name": "Mock User", "role": "Admin"}]
        def get_company_details(self, cid): return {"company_id": "c1", "company_name": "Mock Company Inc."} # For CompanyTabWidget
        def initialize_database(self): pass

    db_manager = MockDBManager() # Override the global db_manager with our mock

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
    sys.modules['dialogs.transporter_dialog'] = type('module', (), {'TransporterDialog': MockTransporterDialog})
    sys.modules['dialogs.freight_forwarder_dialog'] = type('module', (), {'FreightForwarderDialog': MockFreightForwarderDialog})


    app = QApplication(sys.argv)
    mock_config = {
        "templates_dir": "./templates_mock", "clients_dir": "./clients_mock", "language": "en",
        "default_reminder_days": 15, "session_timeout_minutes": 60, "database_path": "mock_app.db",
        "google_maps_review_url": "https://maps.google.com/mock", "show_initial_setup_on_startup": True,
        "smtp_server": "smtp.mock.com", "smtp_port": 587, "smtp_user": "mock_user", "smtp_password": "mock_password",
        "download_monitor_enabled": False, # Add mock data for new settings
        "download_monitor_path": os.path.join(os.path.expanduser('~'), 'Downloads_mock') # Add mock data
    }
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
