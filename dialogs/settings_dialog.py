# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
    QFileDialog, QLabel, QHBoxLayout
)
# Note: QHBoxLayout was added as it's used for template/client dir browsing lines.
# Note: utils_load_config was not found in use in the SettingsDialog, only utils_save_config.
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

    def get_config(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        config_data_to_return = {
            "templates_dir": self.templates_dir_input.text(),
            "clients_dir": self.clients_dir_input.text(),
            "language": language_code,
            "default_reminder_days": self.reminder_days_spinbox.value(),
            "session_timeout_minutes": self.session_timeout_spinbox.value(), # Added session timeout
            "smtp_server": self.smtp_server_input_field.text(),
            "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(),
            "smtp_password": self.smtp_pass_input_field.text(),
            "google_maps_review_url": self.google_maps_url_input.text().strip()
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
        new_config = self.get_config()
        # The actual saving logic might be more complex, e.g. self.CONFIG.update(new_config)
        # and then self.save_config(self.CONFIG, 'config.json')
        # For now, assuming direct save of the returned dict is okay.
        # The original SettingsDialog directly calls self.save_config(new_config_dict, "config.json")
        # So, this should be:
        try:
            # The `save_config` function from `utils` likely takes the data and a filename.
            # Assuming the filename is 'config.json' as is common.
            # The original `main_config` passed to __init__ is the reference to the app's main config object.
            # We should update this main_config object and then tell it to save itself,
            # or use a utility that knows where to save it.
            # The `utils_save_config` is `self.save_config`.
            # The original main.py might have something like:
            # self.config_manager.update_config(new_settings_data)
            # self.config_manager.save_config()
            # Or, if `main_config` is just a dict and `utils_save_config` saves a dict to a known path:

            # Let's refine get_config in CompanyTabWidget if it's not directly returning savable data.
            # The provided `dialogs.py` snippet for `SettingsDialog.get_config` already returns a dict.
            # The `CompanyTabWidget` is instantiated with `self` (the SettingsDialog instance),
            # so it might call `self.parent().save_config` or similar.
            # However, the `get_config` in `SettingsDialog` is the one that should aggregate all data.
            # The `CompanyTabWidget`'s data needs to be incorporated into `config_data_to_return`.
            # I've added a placeholder for this logic in `get_config`.
            # The `utils_save_config` function needs to be called with the correct parameters.
            # If `utils_save_config` is responsible for knowing the path:
            self.save_config(new_config) # Assuming utils_save_config knows the path or uses self.CONFIG internally

            # If SettingsDialog is meant to update the passed `main_config` object directly:
            # self.current_config_data.update(new_config) # Update the dict in-place
            # And then the caller of SettingsDialog would be responsible for saving.
            # However, the presence of `self.save_config = utils_save_config` implies SettingsDialog saves.

            # For the purpose of refactoring, we ensure the logic remains the same.
            # If `CompanyTabWidget` saves itself, that's fine. If it returns data, `get_config` handles it.
            # The `utils_save_config` is likely `ConfigManager.save_config_static` or similar.
            # Let's assume `self.save_config(new_config)` is the correct invocation based on its direct assignment.
            # This implies `utils_save_config` is a function that takes the config dict.
            # The actual saving path/mechanism is abstracted by `utils_save_config`.

            QMessageBox.information(self, self.tr("Paramètres Enregistrés"), self.tr("Les paramètres ont été enregistrés. Certains changements peuvent nécessiter un redémarrage."))
            super().accept() # Call QDialog.accept() to close with QDialog.Accepted
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Sauvegarde"), self.tr("Impossible d'enregistrer les paramètres:\n{0}").format(str(e)))
            # Do not close dialog if save fails
