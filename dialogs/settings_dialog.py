# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
    QFileDialog, QLabel, QHBoxLayout, QCheckBox, QMessageBox
)
# Note: QHBoxLayout was added as it's used for template/client dir browsing lines.
# Note: QCheckBox was added for the new setting.
# Note: utils_load_config was not found in use in the SettingsDialog, only utils_save_config.
import os # Added for os.path.dirname and os.path.exists in browse_db_path
from utils import save_config as utils_save_config
from company_management import CompanyTabWidget

class SettingsDialog(QDialog):
    def __init__(self, main_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = main_config
        self.CONFIG = main_config # Retained if used by CompanyTabWidget or other parts not shown
        self.save_config = utils_save_config
        self.setup_ui_settings()

    def setup_ui_settings(self):
        layout = QVBoxLayout(self); self.tabs_widget = QTabWidget(); layout.addWidget(self.tabs_widget)
        general_tab_widget = QWidget(); general_form_layout = QFormLayout(general_tab_widget)
        self.templates_dir_input = QLineEdit(self.current_config_data["templates_dir"])
        templates_browse_btn = QPushButton(self.tr("Parcourir...")); templates_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.templates_dir_input, self.tr("Sélectionner dossier modèles")))
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Modèles:"), templates_dir_layout)
        self.clients_dir_input = QLineEdit(self.current_config_data["clients_dir"])
        clients_browse_btn = QPushButton(self.tr("Parcourir...")); clients_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.clients_dir_input, self.tr("Sélectionner dossier clients")))
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Clients:"), clients_dir_layout)
        self.interface_lang_combo = QComboBox()
        self.lang_display_to_code = {
            self.tr("Français (fr)"): "fr", self.tr("English (en)"): "en",
            self.tr("العربية (ar)"): "ar", self.tr("Türkçe (tr)"): "tr",
            self.tr("Português (pt)"): "pt",
            self.tr("Русский (ru)"): "ru"
        }
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))
        current_lang_code = self.current_config_data.get("language", "fr")
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}
        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text: self.interface_lang_combo.setCurrentText(current_display_text)
        else: self.interface_lang_combo.setCurrentText(code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0]))
        general_form_layout.addRow(self.tr("Langue Interface (redémarrage requis):"), self.interface_lang_combo)
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365)
        self.reminder_days_spinbox.setValue(self.current_config_data.get("default_reminder_days", 30))
        general_form_layout.addRow(self.tr("Jours avant rappel client ancien:"), self.reminder_days_spinbox)

        # Session Timeout
        self.session_timeout_label = QLabel(self.tr("Session Timeout (minutes):"))
        self.session_timeout_spinbox = QSpinBox()
        self.session_timeout_spinbox.setRange(5, 525600) # New range: Min 5 mins, Max ~1 year
        self.session_timeout_spinbox.setSuffix(self.tr(" minutes"))
        self.session_timeout_spinbox.setToolTip(
            self.tr("Set session duration in minutes. Examples: 1440 (1 day), 10080 (1 week), 43200 (30 days), 259200 (6 months).")
        )
        default_timeout_minutes = self.current_config_data.get("session_timeout_minutes", 259200) # New default

        self.session_timeout_spinbox.setValue(default_timeout_minutes)
        general_form_layout.addRow(self.session_timeout_label, self.session_timeout_spinbox)

        # Google Maps Review URL
        self.google_maps_url_input = QLineEdit(self.current_config_data.get("google_maps_review_url", "https://maps.google.com/?cid=YOUR_CID_HERE"))
        self.google_maps_url_input.setPlaceholderText(self.tr("Entrez l'URL complète pour les avis Google Maps"))
        general_form_layout.addRow(self.tr("Lien Avis Google Maps:"), self.google_maps_url_input)

        # Show initial setup prompt checkbox
        self.show_setup_prompt_checkbox = QCheckBox()
        self.show_setup_prompt_checkbox.setChecked(self.current_config_data.get("show_initial_setup_on_startup", False))
        general_form_layout.addRow(self.tr("Show setup prompt on next start (if no company configured):"), self.show_setup_prompt_checkbox)

        # Database Path Configuration
        self.db_path_input = QLineEdit(self.current_config_data.get("database_path", ""))
        db_path_browse_btn = QPushButton(self.tr("Parcourir..."))
        db_path_browse_btn.clicked.connect(self.browse_db_path)
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path_input)
        db_path_layout.addWidget(db_path_browse_btn)
        general_form_layout.addRow(self.tr("Chemin Base de Données:"), db_path_layout)

        self.tabs_widget.addTab(general_tab_widget, self.tr("Général"))
        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget)
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", ""))
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535); self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", ""))
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", "")); self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        self.tabs_widget.addTab(email_tab_widget, self.tr("Email"))
        self.company_tab = CompanyTabWidget(self); self.tabs_widget.addTab(self.company_tab, self.tr("Company Details"))
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_settings_button = dialog_button_box.button(QDialogButtonBox.Ok); ok_settings_button.setText(self.tr("OK")); ok_settings_button.setObjectName("primaryButton")
        cancel_settings_button = dialog_button_box.button(QDialogButtonBox.Cancel); cancel_settings_button.setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)

    def browse_directory_for_input(self, line_edit_target, dialog_title):
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)

    def browse_db_path(self):
        current_path = self.db_path_input.text()
        # Try to start the dialog in the directory of the current path, if valid
        start_dir = os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else ""

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog # Uncomment for testing if native dialog causes issues
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner le fichier de base de données"),
            start_dir, # Use the directory of the current path as starting point
            self.tr("Fichiers de base de données (*.db);;Tous les fichiers (*.*)"),
            options=options
        )
        if file_path:
            self.db_path_input.setText(file_path)

    def get_config(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        config_data_to_return = {
            "templates_dir": self.templates_dir_input.text(),
            "clients_dir": self.clients_dir_input.text(),
            "language": language_code,
            "default_reminder_days": self.reminder_days_spinbox.value(),
            "session_timeout_minutes": self.session_timeout_spinbox.value(), # Added session timeout
            "database_path": self.db_path_input.text().strip(),
            "smtp_server": self.smtp_server_input_field.text(),
            "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(),
            "smtp_password": self.smtp_pass_input_field.text(),
            "google_maps_review_url": self.google_maps_url_input.text().strip(),
            "show_initial_setup_on_startup": self.show_setup_prompt_checkbox.isChecked()
        }
        # The CompanyTabWidget data needs to be retrieved and merged here
        # Assuming company_tab has a method like get_data() or get_company_config()
        if hasattr(self.company_tab, 'get_company_config_data'): # Check if the method exists
            company_config = self.company_tab.get_company_config_data()
            config_data_to_return.update(company_config) # Merge company data
        elif hasattr(self.company_tab, 'get_data'): # Alternative common method name
             company_config = self.company_tab.get_data()
             config_data_to_return.update(company_config)

        return config_data_to_return

    # Override accept to save config before closing
    def accept(self):
        old_db_path = self.current_config_data.get("database_path", "") # Get old path BEFORE new_config

        new_config = self.get_config()
        new_db_path = new_config.get("database_path", "") # Get new path from new_config
        db_path_actually_changed = old_db_path != new_db_path

        try:
            self.save_config(new_config)

            if db_path_actually_changed:
                QMessageBox.information(self,
                                        self.tr("Redémarrage Nécessaire"),
                                        self.tr("Le chemin de la base de données a été modifié. Veuillez redémarrer l'application pour que les changements prennent effet."))

            QMessageBox.information(self, self.tr("Paramètres Enregistrés"), self.tr("Les paramètres ont été enregistrés. Certains changements (comme la langue ou la base de données) peuvent nécessiter un redémarrage."))
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Sauvegarde"), self.tr("Impossible d'enregistrer les paramètres:\n{0}").format(str(e)))
            # Do not close dialog if save fails
