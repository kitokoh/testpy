# -*- coding: utf-8 -*-
import os
import json
import logging
import shutil
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import io

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QTextEdit,
    QInputDialog, QMessageBox, QFrame, QLabel, QListWidget, QListWidgetItem, QCheckBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QDoubleSpinBox,
    QGridLayout, QGroupBox, QCompleter
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QBrush, QPixmap
from PyQt5.QtCore import Qt, QUrl, QCoreApplication, QDate

import pandas as pd
from docx import Document
from PyPDF2 import PdfMerger
from reportlab.pdfgen import canvas

import db as db_manager
from company_management import CompanyTabWidget
from excel_editor import ExcelEditor
from html_editor import HtmlEditor
from pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGRDE_APP_CONFIG
from utils import populate_docx_template, load_config as utils_load_config, save_config as utils_save_config

# APP_ROOT_DIR is now passed to CompilePdfDialog constructor where needed.
import shutil # Ensure shutil is imported

# The global import from main is removed.

# Forward declaration for type hinting if needed, or ensure ProductDimensionUIDialog is defined before use.
# class ProductDimensionUIDialog(QDialog): pass


class AddNewClientDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Ajouter un Nouveau Client"))
        self.setMinimumSize(500, 400) # Adjust as needed
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignRight)
        self.form_layout.setSpacing(10)

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText(self.tr("Nom du client"))
        self.form_layout.addRow(self.tr("Nom Client:"), self.client_name_input)

        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText(self.tr("Nom entreprise (optionnel)"))
        self.form_layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)

        self.client_need_input = QLineEdit()
        self.client_need_input.setPlaceholderText(self.tr("Besoin principal du client"))
        self.form_layout.addRow(self.tr("Besoin Client:"), self.client_need_input)

        country_hbox_layout = QHBoxLayout()
        self.country_select_combo = QComboBox()
        self.country_select_combo.setEditable(True)
        self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country)
        country_hbox_layout.addWidget(self.country_select_combo)
        self.add_country_button = QPushButton("+")
        self.add_country_button.setFixedSize(30, 30)
        self.add_country_button.setToolTip(self.tr("Ajouter un nouveau pays"))
        self.add_country_button.clicked.connect(self.add_new_country_dialog)
        country_hbox_layout.addWidget(self.add_country_button)
        self.form_layout.addRow(self.tr("Pays Client:"), country_hbox_layout)

        city_hbox_layout = QHBoxLayout()
        self.city_select_combo = QComboBox()
        self.city_select_combo.setEditable(True)
        self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)
        self.add_city_button = QPushButton("+")
        self.add_city_button.setFixedSize(30, 30)
        self.add_city_button.setToolTip(self.tr("Ajouter une nouvelle ville"))
        self.add_city_button.clicked.connect(self.add_new_city_dialog)
        city_hbox_layout.addWidget(self.add_city_button)
        self.form_layout.addRow(self.tr("Ville Client:"), city_hbox_layout)

        self.project_id_input_field = QLineEdit()
        self.project_id_input_field.setPlaceholderText(self.tr("Identifiant unique du projet"))
        self.form_layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)

        self.language_select_combo = QComboBox()
        self.language_select_combo.setToolTip(self.tr("Sélectionnez les langues pour lesquelles les dossiers de documents seront créés et qui seront utilisées pour la génération de modèles."))
        # Language options should be consistent with main_window.py's original setup
        self.language_options_map = {
            self.tr("English only (en)"): ["en"],
            self.tr("French only (fr)"): ["fr"],
            self.tr("Arabic only (ar)"): ["ar"],
            self.tr("Turkish only (tr)"): ["tr"],
            self.tr("Portuguese only (pt)"): ["pt"],
            self.tr("All supported languages (en, fr, ar, tr, pt)"): ["en", "fr", "ar", "tr", "pt"]
        }
        self.language_select_combo.addItems(list(self.language_options_map.keys()))
        self.form_layout.addRow(self.tr("Langues:"), self.language_select_combo)

        layout.addLayout(self.form_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(self.tr("Créer Client"))
        self.buttons.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.load_countries_into_combo()

    def load_countries_into_combo(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))

    def load_cities_for_country(self, country_name_str):
        self.city_select_combo.clear()
        if not country_name_str: return
        selected_country_id = self.country_select_combo.currentData()
        if selected_country_id is None:
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name: selected_country_id = country_obj_by_name['country_id']
            else: return
        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                returned_country_id = db_manager.add_country({'country_name': country_text.strip()})
                if returned_country_id is not None:
                    self.load_countries_into_combo()
                    index = self.country_select_combo.findText(country_text.strip())
                    if index >= 0: self.country_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def add_new_city_dialog(self):
        current_country_name = self.country_select_combo.currentText()
        current_country_id = self.country_select_combo.currentData()
        if not current_country_id:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner un pays valide."))
            return
        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                returned_city_id = db_manager.add_city({'country_id': current_country_id, 'city_name': city_text.strip()})
                if returned_city_id is not None:
                    self.load_cities_for_country(current_country_name)
                    index = self.city_select_combo.findText(city_text.strip())
                    if index >= 0: self.city_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout de la ville. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def get_data(self):
        client_name = self.client_name_input.text().strip()
        company_name = self.company_name_input.text().strip()
        client_need = self.client_need_input.text().strip()
        country_id = self.country_select_combo.currentData()
        country_name = self.country_select_combo.currentText().strip()
        city_id = self.city_select_combo.currentData()
        city_name = self.city_select_combo.currentText().strip()
        project_id_text = self.project_id_input_field.text().strip()

        selected_lang_display_text = self.language_select_combo.currentText()
        selected_languages = self.language_options_map.get(selected_lang_display_text, ["fr"]) # Default to French if mapping fails

        # Handle cases where country/city might be new and not have an ID yet
        if country_id is None and country_name:
            # Attempt to get or create country if it was manually entered
            country_obj = db_manager.get_country_by_name(country_name)
            if country_obj:
                country_id = country_obj['country_id']
            # else: # Optionally, auto-add new country or handle as error
            #     QMessageBox.warning(self, self.tr("Pays Invalide"), self.tr("Le pays '{0}' n'est pas valide.").format(country_name))
            #     return None # Indicate error

        if city_id is None and city_name and country_id:
            # Attempt to get or create city if it was manually entered
            city_obj = db_manager.get_city_by_name_and_country_id(city_name, country_id)
            if city_obj:
                city_id = city_obj['city_id']
            # else: # Optionally, auto-add new city or handle as error
            #    QMessageBox.warning(self, self.tr("Ville Invalide"), self.tr("La ville '{0}' pour le pays '{1}' n'est pas valide.").format(city_name, country_name))
            #    return None # Indicate error

        return {
            "client_name": client_name,
            "company_name": company_name,
            "primary_need_description": client_need, # Matching EditClientDialog's get_data
            "country_id": country_id,
            "country_name": country_name, # For display or if ID is None
            "city_id": city_id,
            "city_name": city_name, # For display or if ID is None
            "project_identifier": project_id_text, # Matching EditClientDialog's get_data
            "selected_languages": ",".join(selected_languages) # Store as comma-separated string
        }


class SettingsDialog(QDialog):
    def __init__(self, main_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = main_config
        self.CONFIG = main_config
        self.save_config = utils_save_config
        self.setup_ui_settings()

    def setup_ui_settings(self):
        layout = QVBoxLayout(self); tabs_widget = QTabWidget(); layout.addWidget(tabs_widget)
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

        tabs_widget.addTab(general_tab_widget, self.tr("Général"))
        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget)
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", ""))
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535); self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", ""))
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", "")); self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, self.tr("Email"))
        self.company_tab = CompanyTabWidget(self); tabs_widget.addTab(self.company_tab, self.tr("Company Details"))
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
            "smtp_password": self.smtp_pass_input_field.text()
        }
        return config_data_to_return

class TemplateDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestion des Modèles"))
        self.setMinimumSize(800, 500)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        main_hbox_layout = QHBoxLayout(self); left_vbox_layout = QVBoxLayout(); left_vbox_layout.setSpacing(10)

        # Filter UI Elements
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)

        self.category_filter_label = QLabel(self.tr("Category:"))
        self.category_filter_combo = QComboBox()
        filter_layout.addWidget(self.category_filter_label, 0, 0)
        filter_layout.addWidget(self.category_filter_combo, 0, 1)

        self.language_filter_label = QLabel(self.tr("Language:"))
        self.language_filter_combo = QComboBox()
        filter_layout.addWidget(self.language_filter_label, 0, 2)
        filter_layout.addWidget(self.language_filter_combo, 0, 3)

        self.doc_type_filter_label = QLabel(self.tr("Document Type:"))
        self.doc_type_filter_combo = QComboBox()
        filter_layout.addWidget(self.doc_type_filter_label, 0, 4)
        filter_layout.addWidget(self.doc_type_filter_combo, 0, 5)

        # Add some stretch to push filters to the left if needed, or set column stretch factors
        filter_layout.setColumnStretch(6, 1) # Add stretch to the right of filters

        left_vbox_layout.addLayout(filter_layout)

        self.template_list = QTreeWidget(); self.template_list.setColumnCount(4)
        self.template_list.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Language"), self.tr("Default Status")])
        header = self.template_list.header(); header.setSectionResizeMode(0, QHeaderView.Stretch); header.setSectionResizeMode(1, QHeaderView.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.ResizeToContents); header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.template_list.setAlternatingRowColors(True); font = self.template_list.font(); font.setPointSize(font.pointSize() + 1); self.template_list.setFont(font)
        left_vbox_layout.addWidget(self.template_list)
        btn_layout = QHBoxLayout(); btn_layout.setSpacing(8)
        self.add_btn = QPushButton(self.tr("Ajouter")); self.add_btn.setIcon(QIcon(":/icons/plus.svg")); self.add_btn.setToolTip(self.tr("Ajouter un nouveau modèle")); self.add_btn.setObjectName("primaryButton"); self.add_btn.clicked.connect(self.add_template); btn_layout.addWidget(self.add_btn)
        self.edit_btn = QPushButton(self.tr("Modifier")); self.edit_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_btn.setToolTip(self.tr("Modifier le modèle sélectionné (ouvre le fichier externe)")); self.edit_btn.clicked.connect(self.edit_template); self.edit_btn.setEnabled(False); btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QPushButton(self.tr("Supprimer")); self.delete_btn.setIcon(QIcon(":/icons/trash.svg")); self.delete_btn.setToolTip(self.tr("Supprimer le modèle sélectionné")); self.delete_btn.setObjectName("dangerButton"); self.delete_btn.clicked.connect(self.delete_template); self.delete_btn.setEnabled(False); btn_layout.addWidget(self.delete_btn)
        self.default_btn = QPushButton(self.tr("Par Défaut")); self.default_btn.setIcon(QIcon.fromTheme("emblem-default")); self.default_btn.setToolTip(self.tr("Définir le modèle sélectionné comme modèle par défaut pour sa catégorie et langue")); self.default_btn.clicked.connect(self.set_default_template); self.default_btn.setEnabled(False); btn_layout.addWidget(self.default_btn) # emblem-default not in list yet
        left_vbox_layout.addLayout(btn_layout); main_hbox_layout.addLayout(left_vbox_layout, 1)
        self.preview_area = QTextEdit(); self.preview_area.setReadOnly(True); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        self.preview_area.setObjectName("templatePreviewArea")
        main_hbox_layout.addWidget(self.preview_area, 3); main_hbox_layout.setContentsMargins(15,15,15,15)

        self.populate_category_filter()
        self.populate_language_filter()
        self.populate_doc_type_filter()

        # Connect filter signals
        self.category_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)
        self.language_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)
        self.doc_type_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)

        self.load_templates(); self.template_list.currentItemChanged.connect(self.handle_tree_item_selection)

    def handle_filter_changed(self):
        category_id = self.category_filter_combo.currentData()
        language_code = self.language_filter_combo.currentData()
        doc_type = self.doc_type_filter_combo.currentData() # This is the DB value

        # Ensure "all" is treated as None or a special value if your load_templates expects that
        # For now, load_templates is designed to handle "all" string directly.
        self.load_templates(category_filter=category_id, language_filter=language_code, type_filter=doc_type)

    def populate_category_filter(self):
        self.category_filter_combo.addItem(self.tr("All Categories"), "all")
        try:
            categories = db_manager.get_all_template_categories()
            if categories:
                for category in categories:
                    self.category_filter_combo.addItem(category['category_name'], category['category_id'])
        except Exception as e:
            print(f"Error populating category filter: {e}") # Log error
            QMessageBox.warning(self, self.tr("Filter Error"), self.tr("Could not load template categories for filtering."))

    def populate_language_filter(self):
        self.language_filter_combo.addItem(self.tr("All Languages"), "all")
        try:
            # Assuming db_manager.get_distinct_template_languages() returns a list of language code strings
            languages = db_manager.get_distinct_template_languages()
            if languages:
                for lang_code_tuple in languages: # get_distinct_template_languages might return list of tuples
                    lang_code = lang_code_tuple[0]
                    self.language_filter_combo.addItem(lang_code, lang_code)
        except Exception as e:
            print(f"Error populating language filter: {e}") # Log error
            QMessageBox.warning(self, self.tr("Filter Error"), self.tr("Could not load template languages for filtering."))

    def populate_doc_type_filter(self):
        self.doc_type_filter_combo.addItem(self.tr("All Types"), "all")
        # Mapping from DB type to user-friendly name
        self.doc_type_map = {
            "document_excel": self.tr("Excel"),
            "document_word": self.tr("Word"),
            "document_html": self.tr("HTML"),
            "document_other": self.tr("Other"),
            # Add more types as needed
        }
        try:
            # Assuming db_manager.get_distinct_template_types() returns a list of type strings
            doc_types = db_manager.get_distinct_template_types()
            if doc_types:
                for type_tuple in doc_types: # get_distinct_template_types might return list of tuples
                    db_type = type_tuple[0]
                    display_name = self.doc_type_map.get(db_type, db_type) # Fallback to db_type if not in map
                    self.doc_type_filter_combo.addItem(display_name, db_type)
        except Exception as e:
            print(f"Error populating document type filter: {e}") # Log error
            QMessageBox.warning(self, self.tr("Filter Error"), self.tr("Could not load template document types for filtering."))

    def handle_tree_item_selection(self,current_item,previous_item):
        if current_item is not None and current_item.parent() is not None: self.show_template_preview(current_item); self.edit_btn.setEnabled(True); self.delete_btn.setEnabled(True); self.default_btn.setEnabled(True)
        else: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def show_template_preview(self, item):
        if not item: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        template_id=item.data(0,Qt.UserRole);
        if template_id is None: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        try:
            details=db_manager.get_template_details_for_preview(template_id)
            if details:
                base_file_name=details['base_file_name']; language_code=details['language_code']; template_file_path=os.path.join(self.config["templates_dir"],language_code,base_file_name)
                self.preview_area.clear()
                if os.path.exists(template_file_path):
                    _,file_extension=os.path.splitext(template_file_path); file_extension=file_extension.lower()
                    if file_extension==".xlsx":
                        try:
                            df=pd.read_excel(template_file_path,sheet_name=0); html_content=f"""<style>table {{ border-collapse: collapse; width: 95%; font-family: Arial, sans-serif; margin: 10px; }} th, td {{ border: 1px solid #cccccc; padding: 6px; text-align: left; }} th {{ background-color: #e0e0e0; font-weight: bold; }} td {{ text-align: right; }} tr:nth-child(even) {{ background-color: #f9f9f9; }} tr:hover {{ background-color: #e6f7ff; }}</style>{df.to_html(escape=False,index=False,border=0)}"""; self.preview_area.setHtml(html_content)
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Excel:\n{0}").format(str(e)))
                    elif file_extension==".docx":
                        try: doc=Document(template_file_path); full_text=[para.text for para in doc.paragraphs]; self.preview_area.setPlainText("\n".join(full_text))
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Word:\n{0}").format(str(e)))
                    elif file_extension==".html":
                        try:
                            with open(template_file_path,"r",encoding="utf-8") as f: self.preview_area.setHtml(f.read())
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier HTML:\n{0}").format(str(e)))
                    else: self.preview_area.setPlainText(self.tr("Aperçu non disponible pour ce type de fichier."))
                else: self.preview_area.setPlainText(self.tr("Fichier modèle introuvable."))
            else: self.preview_area.setPlainText(self.tr("Détails du modèle non trouvés dans la base de données."))
        except Exception as e_general: self.preview_area.setPlainText(self.tr("Une erreur est survenue lors de la récupération des détails du modèle:\n{0}").format(str(e_general)))

    def load_templates(self, category_filter=None, language_filter=None, type_filter=None):
        self.template_list.clear()
        self.preview_area.clear()
        self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))

        effective_category_id = category_filter if category_filter != "all" else None
        effective_language_code = language_filter if language_filter != "all" else None
        effective_template_type = type_filter if type_filter != "all" else None

        all_templates_from_db = db_manager.get_filtered_templates(
            category_id=effective_category_id,
            language_code=effective_language_code,
            template_type=effective_template_type
        )

        if not all_templates_from_db:
            # No templates match the filters, or an error occurred (already logged by db_manager)
            self.template_list.expandAll() # Keep it consistent
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.default_btn.setEnabled(False)
            return

        if effective_category_id is not None:
            # Specific category was selected, create one top-level item for it
            category_details = db_manager.get_template_category_details(effective_category_id)
            if category_details:
                category_item = QTreeWidgetItem(self.template_list, [category_details['category_name']])
                for template_dict in all_templates_from_db: # These are already filtered correctly
                    template_name = template_dict['template_name']
                    template_db_type = template_dict.get('template_type', 'N/A')
                    display_type_name = self.doc_type_map.get(template_db_type, template_db_type)
                    language = template_dict['language_code']
                    is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                    template_item = QTreeWidgetItem(category_item, [template_name, display_type_name, language, is_default])
                    template_item.setData(0, Qt.UserRole, template_dict['template_id'])
            else:
                # Category details not found, this might indicate an issue or just no templates for this specific category
                # This case should ideally be handled based on whether get_filtered_templates returned anything
                pass
        else:
            # "All Categories" selected, group templates by category
            all_db_categories = db_manager.get_all_template_categories()
            if not all_db_categories: # Should not happen if there are templates
                self.template_list.expandAll()
                self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)
                return

            categories_map = {cat['category_id']: cat for cat in all_db_categories}
            templates_by_category = {}
            for template in all_templates_from_db:
                cat_id = template.get('category_id')
                if cat_id not in templates_by_category:
                    templates_by_category[cat_id] = []
                templates_by_category[cat_id].append(template)

            for cat_id, category_details_dict in categories_map.items():
                if cat_id in templates_by_category: # Only add category if it has matching templates
                    category_item = QTreeWidgetItem(self.template_list, [category_details_dict['category_name']])
                    for template_dict in templates_by_category[cat_id]:
                        template_name = template_dict['template_name']
                        template_db_type = template_dict.get('template_type', 'N/A')
                        display_type_name = self.doc_type_map.get(template_db_type, template_db_type)
                        language = template_dict['language_code']
                        is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                        template_item = QTreeWidgetItem(category_item, [template_name, display_type_name, language, is_default])
                        template_item.setData(0, Qt.UserRole, template_dict['template_id'])

        self.template_list.expandAll()
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.default_btn.setEnabled(False)

    def add_template(self):
        file_path,_=QFileDialog.getOpenFileName(self,self.tr("Sélectionner un modèle"),self.config["templates_dir"],self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Tous les fichiers (*)"))
        if not file_path:return
        name,ok=QInputDialog.getText(self,self.tr("Nom du Modèle"),self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip():return
        existing_categories=db_manager.get_all_template_categories(); existing_categories=existing_categories if existing_categories else []
        category_display_list=[cat['category_name'] for cat in existing_categories]; create_new_option=self.tr("[Create New Category...]"); category_display_list.append(create_new_option)
        selected_category_name,ok=QInputDialog.getItem(self,self.tr("Select Template Category"),self.tr("Category:"),category_display_list,0,False)
        if not ok:return
        final_category_id=None
        if selected_category_name==create_new_option:
            new_category_text,ok_new=QInputDialog.getText(self,self.tr("New Category"),self.tr("Enter name for new category:"))
            if ok_new and new_category_text.strip(): final_category_id=db_manager.add_template_category(new_category_text.strip());
            if not final_category_id:QMessageBox.warning(self,self.tr("Error"),self.tr("Could not create or find category: {0}").format(new_category_text.strip()));return
            else:return
        else:
            found_cat=next((cat for cat in existing_categories if cat['category_name']==selected_category_name),None)
            if found_cat:final_category_id=found_cat['category_id']
            else:QMessageBox.critical(self,self.tr("Error"),self.tr("Selected category not found internally."));return
        languages=["fr","en","ar","tr","pt"]; lang,ok=QInputDialog.getItem(self,self.tr("Langue du Modèle"),self.tr("Sélectionnez la langue:"),languages,0,False)
        if not ok:return
        target_dir=os.path.join(self.config["templates_dir"],lang); os.makedirs(target_dir,exist_ok=True)
        base_file_name=os.path.basename(file_path); target_path=os.path.join(target_dir,base_file_name)
        file_ext=os.path.splitext(base_file_name)[1].lower(); template_type_for_db="document_other"
        if file_ext==".xlsx":template_type_for_db="document_excel"
        elif file_ext==".docx":template_type_for_db="document_word"
        elif file_ext==".html":template_type_for_db="document_html"
        template_metadata={'template_name':name.strip(),'template_type':template_type_for_db,'language_code':lang,'base_file_name':base_file_name,'description':f"Modèle {name.strip()} en {lang} ({base_file_name})",'category_id':final_category_id,'is_default_for_type_lang':False}
        try:
            shutil.copy(file_path,target_path); new_template_id=db_manager.add_template(template_metadata)
            if new_template_id:self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle ajouté avec succès."))
            else:QMessageBox.critical(self,self.tr("Erreur DB"),self.tr("Erreur lors de l'enregistrement du modèle dans la base de données."))
        except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur lors de l'ajout du modèle (fichier ou DB):\n{0}").format(str(e)))

    def edit_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à modifier."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            path_info=db_manager.get_template_path_info(template_id)
            if path_info:template_file_path=os.path.join(self.config["templates_dir"],path_info['language'],path_info['file_name']); QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
            else:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Impossible de récupérer les informations du modèle."))
        except Exception as e:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Erreur lors de l'ouverture du modèle:\n{0}").format(str(e)))

    def delete_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à supprimer."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        reply=QMessageBox.question(self,self.tr("Confirmer Suppression"),self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if reply==QMessageBox.Yes:
            try:
                file_info=db_manager.delete_template_and_get_file_info(template_id)
                if file_info:
                    file_path_to_delete=os.path.join(self.config["templates_dir"],file_info['language'],file_info['file_name'])
                    if os.path.exists(file_path_to_delete):os.remove(file_path_to_delete)
                    self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle supprimé avec succès."))
                else:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur de suppression du modèle."))
            except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur de suppression du modèle:\n{0}").format(str(e)))

    def set_default_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à définir par défaut."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            success=db_manager.set_default_template_by_id(template_id)
            if success:self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle défini comme modèle par défaut."))
            else:QMessageBox.critical(self,self.tr("Erreur DB"),self.tr("Erreur de mise à jour du modèle."))
        except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur lors de la définition du modèle par défaut:\n{0}").format(str(e)))

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id; self.contact_data = contact_data or {}
        self.setWindowTitle(self.tr("Modifier Contact") if self.contact_data else self.tr("Ajouter Contact"))
        self.setMinimumSize(450,550); self.setup_ui() # Increased min height for new group

    def _create_icon_label_widget(self,icon_name,label_text):
        widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
        icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget

    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(15)
        header_label=QLabel(self.tr("Ajouter Nouveau Contact") if not self.contact_data else self.tr("Modifier Détails Contact")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)
        form_layout=QFormLayout();form_layout.setSpacing(10);form_layout.setContentsMargins(10,0,10,0)
        # self.setStyleSheet("QLineEdit, QCheckBox { padding: 3px; }") # Prefer global styles
        self.name_input=QLineEdit(self.contact_data.get("name",""));form_layout.addRow(self._create_icon_label_widget("user",self.tr("Nom complet (ou affichage):")),self.name_input) # Changed label slightly
        self.email_input=QLineEdit(self.contact_data.get("email",""));form_layout.addRow(self._create_icon_label_widget("mail-message-new",self.tr("Email:")),self.email_input)
        self.phone_input=QLineEdit(self.contact_data.get("phone",""));form_layout.addRow(self._create_icon_label_widget("phone",self.tr("Téléphone (principal):")),self.phone_input) # Changed label slightly
        self.position_input=QLineEdit(self.contact_data.get("position",""));form_layout.addRow(self._create_icon_label_widget("preferences-desktop-user",self.tr("Poste (général):")),self.position_input) # Changed label slightly
        self.primary_check=QCheckBox(self.tr("Contact principal pour le client"));self.primary_check.setChecked(bool(self.contact_data.get("is_primary_for_client", self.contact_data.get("is_primary",0))));self.primary_check.stateChanged.connect(self.update_primary_contact_visuals);form_layout.addRow(self._create_icon_label_widget("emblem-important",self.tr("Principal:")),self.primary_check)
        main_layout.addLayout(form_layout)

        # Additional Fields GroupBox
        self.additional_fields_group = QGroupBox(self.tr("Champs supplémentaires"))
        self.additional_fields_group.setCheckable(True)
        self.additional_fields_group.setChecked(False) # Default to collapsed
        additional_form_layout = QFormLayout(self.additional_fields_group)
        additional_form_layout.setSpacing(10)

        self.givenName_input = QLineEdit(self.contact_data.get("givenName", ""))
        additional_form_layout.addRow(self.tr("Prénom:"), self.givenName_input)
        self.familyName_input = QLineEdit(self.contact_data.get("familyName", ""))
        additional_form_layout.addRow(self.tr("Nom de famille:"), self.familyName_input)
        self.displayName_input = QLineEdit(self.contact_data.get("displayName", ""))
        additional_form_layout.addRow(self.tr("Nom affiché:"), self.displayName_input)
        self.phone_type_input = QLineEdit(self.contact_data.get("phone_type", ""))
        additional_form_layout.addRow(self.tr("Type téléphone (principal):"), self.phone_type_input)
        self.email_type_input = QLineEdit(self.contact_data.get("email_type", ""))
        additional_form_layout.addRow(self.tr("Type email (principal):"), self.email_type_input)
        self.address_formattedValue_input = QLineEdit(self.contact_data.get("address_formattedValue", ""))
        additional_form_layout.addRow(self.tr("Adresse complète formatée:"), self.address_formattedValue_input)
        self.address_streetAddress_input = QLineEdit(self.contact_data.get("address_streetAddress", ""))
        additional_form_layout.addRow(self.tr("Rue:"), self.address_streetAddress_input)
        self.address_city_input = QLineEdit(self.contact_data.get("address_city", ""))
        additional_form_layout.addRow(self.tr("Ville:"), self.address_city_input)
        self.address_region_input = QLineEdit(self.contact_data.get("address_region", ""))
        additional_form_layout.addRow(self.tr("Région/État:"), self.address_region_input)
        self.address_postalCode_input = QLineEdit(self.contact_data.get("address_postalCode", ""))
        additional_form_layout.addRow(self.tr("Code Postal:"), self.address_postalCode_input)
        self.address_country_input = QLineEdit(self.contact_data.get("address_country", ""))
        additional_form_layout.addRow(self.tr("Pays:"), self.address_country_input)
        self.organization_name_input = QLineEdit(self.contact_data.get("organization_name", self.contact_data.get("company_name", ""))) # Fallback to general company_name
        additional_form_layout.addRow(self.tr("Nom Organisation:"), self.organization_name_input)
        self.organization_title_input = QLineEdit(self.contact_data.get("organization_title", self.contact_data.get("position", ""))) # Fallback to general position
        additional_form_layout.addRow(self.tr("Titre dans l'organisation:"), self.organization_title_input)
        self.birthday_date_input = QLineEdit(self.contact_data.get("birthday_date", "")) # Using QLineEdit for now
        self.birthday_date_input.setPlaceholderText(self.tr("AAAA-MM-JJ ou MM-JJ"))
        additional_form_layout.addRow(self.tr("Date de naissance:"), self.birthday_date_input)

        self.notes_input = QTextEdit(self.contact_data.get("notes", ""))
        self.notes_input.setFixedHeight(60)
        additional_form_layout.addRow(self.tr("Notes:"), self.notes_input)

        main_layout.addWidget(self.additional_fields_group)

        # Check if any additional field has data to expand the group box
        additional_fields_keys = [
            "givenName", "familyName", "displayName", "phone_type", "email_type",
            "address_formattedValue", "address_streetAddress", "address_city",
            "address_region", "address_postalCode", "address_country",
            "organization_name", "organization_title", "birthday_date", "notes"
        ]
        # Also consider company_name and position if they were used as fallbacks and are different
        # from the main company_name/position fields, or if the specific fields are present.
        if any(self.contact_data.get(key) for key in additional_fields_keys) or \
           (self.contact_data.get("company_name") and self.organization_name_input.text() != self.contact_data.get("company_name")) or \
           (self.contact_data.get("position") and self.organization_title_input.text() != self.contact_data.get("position")):
            self.additional_fields_group.setChecked(True)

        main_layout.addStretch()
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame") # Style in QSS
        button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0)
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton")
        cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)
        self.update_primary_contact_visuals(self.primary_check.checkState())

    def update_primary_contact_visuals(self,state):
        # Dynamic style based on state - kept inline
        # Padding will be inherited from global QLineEdit style
        if state==Qt.Checked:
            self.name_input.setStyleSheet("background-color: #E8F5E9;") # Light Green from palette
        else:
            self.name_input.setStyleSheet("") # Reset to default QSS

    def get_data(self):
        data = {
            "name": self.name_input.text().strip(), # Fallback name or displayName
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(), # Primary phone
            "position": self.position_input.text().strip(), # General position
            "is_primary_for_client": 1 if self.primary_check.isChecked() else 0,
            # notes from main dialog is not here, assumed to be handled by ClientWidget's direct save for general notes.
            # If notes were part of this dialog, it would be: "notes": self.notes_input.toPlainText().strip(),
        }
        if self.additional_fields_group.isChecked():
            data.update({
                "givenName": self.givenName_input.text().strip(),
                "familyName": self.familyName_input.text().strip(),
                "displayName": self.displayName_input.text().strip(),
                "phone_type": self.phone_type_input.text().strip(),
                "email_type": self.email_type_input.text().strip(),
                "address_formattedValue": self.address_formattedValue_input.text().strip(),
                "address_streetAddress": self.address_streetAddress_input.text().strip(),
                "address_city": self.address_city_input.text().strip(),
                "address_region": self.address_region_input.text().strip(),
                "address_postalCode": self.address_postalCode_input.text().strip(),
                "address_country": self.address_country_input.text().strip(),
                "organization_name": self.organization_name_input.text().strip(),
                "organization_title": self.organization_title_input.text().strip(),
                "birthday_date": self.birthday_date_input.text().strip(),
                "notes": self.notes_input.toPlainText().strip(),
            })
            # If displayName has content and main 'name' is different or empty, prioritize displayName for 'name' field in DB
            if data.get("displayName") and data.get("displayName") != data.get("name"):
                data["name"] = data["displayName"]
            elif not data.get("name") and data.get("displayName"): # if name was empty but displayname is not
                 data["name"] = data["displayName"]


        # If the group is not checked, we might still want to save specific fields if they were pre-filled
        # and are now different from their original values (e.g. user unchecked after editing).
        # However, current logic is simpler: if unchecked, only main fields are saved.
        # If a more nuanced save is needed (e.g. save if field ever had data), this logic would need expansion.
        return data

    def accept(self):
        contact_details_to_save = self.get_data()
        if not contact_details_to_save.get("name") and not contact_details_to_save.get("displayName"): # Either name or displayName must be present
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom complet ou le nom affiché du contact est requis."))
            self.name_input.setFocus()
            return

        # If displayName is provided and name is empty, use displayName for name.
        if contact_details_to_save.get("displayName") and not contact_details_to_save.get("name"):
            contact_details_to_save["name"] = contact_details_to_save["displayName"]


        if self.contact_data and self.contact_data.get('contact_id'): # Editing existing contact
            success = db_manager.update_contact(self.contact_data['contact_id'], contact_details_to_save)
            if success:
                # If client_id is present, also update the link details (is_primary)
                if self.client_id:
                    link_details = db_manager.get_specific_client_contact_link_details(self.client_id, self.contact_data['contact_id'])
                    if link_details:
                        client_contact_id = link_details['client_contact_id']
                        update_link_data = {'is_primary_for_client': contact_details_to_save.get("is_primary_for_client", False)}
                        db_manager.update_client_contact_link(client_contact_id, update_link_data)
                    # Else: If no link exists, should we create one? Current behavior is no.
                QMessageBox.information(self, self.tr("Succès"), self.tr("Contact mis à jour avec succès."))
            else:
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour le contact."))
                return # Do not accept dialog if update failed
        else: # Adding new contact
            new_contact_id = db_manager.add_contact(contact_details_to_save)
            if new_contact_id and self.client_id:
                # Link the contact to the client
                is_primary_from_form = contact_details_to_save.get("is_primary_for_client", False)
                link_contact_to_client_result = db_manager.link_contact_to_client(
                    self.client_id,
                    new_contact_id, # The ID of the contact just added
                    is_primary=is_primary_from_form,
                    can_receive_documents=True # Default or from form
                )

                if link_contact_to_client_result:
                    contact_count = db_manager.get_contacts_for_client_count(self.client_id)
                    if contact_count == 1:
                        # If it's the only contact, ensure it's primary, overriding form if it was false
                        db_manager.update_client_contact_link(
                            link_contact_to_client_result,
                            {'is_primary_for_client': True}
                        )
                        print(f"Contact {new_contact_id} set as primary for client {self.client_id} as it's the only contact.")
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Contact ajouté et lié au client avec succès."))
                else:
                     QMessageBox.warning(self, self.tr("Échec"), self.tr("Contact ajouté mais échec de la liaison avec le client."))
            elif new_contact_id:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Contact ajouté avec succès (non lié à un client)."))
            else:
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter le contact."))
                return # Do not accept dialog if add failed
        super().accept() # Proceed to close dialog


class ProductDialog(QDialog):
    def __init__(self,client_id, app_root_dir, product_data=None,parent=None): # Added app_root_dir
        super().__init__(parent)
        self.client_id=client_id
        self.app_root_dir = app_root_dir # Store app_root_dir
        if not self.app_root_dir or not isinstance(self.app_root_dir, str) or not self.app_root_dir.strip():
            logging.warning("ProductDialog initialized with invalid or empty app_root_dir: %s", self.app_root_dir)
        self.current_selected_global_product_id = None
        self.setWindowTitle(self.tr("Ajouter Produits au Client"))
        self.setMinimumSize(900,800)
        self.client_info=db_manager.get_client_by_id(self.client_id)
        self.setup_ui()
        self._set_initial_language_filter()
        self._filter_products_by_language_and_search()

    def _set_initial_language_filter(self):
        client_langs = None
        primary_language=None
        if self.client_info:client_langs=self.client_info.get('selected_languages');
        if client_langs:primary_language=client_langs.split(',')[0].strip()
        if primary_language:
            for i in range(self.product_language_filter_combo.count()):
                if self.product_language_filter_combo.itemText(i)==primary_language:self.product_language_filter_combo.setCurrentText(primary_language);break
    def _filter_products_by_language_and_search(self):
        self.existing_products_list.clear();selected_language=self.product_language_filter_combo.currentText();language_code_for_db=None if selected_language==self.tr("All") else selected_language;search_text=self.search_existing_product_input.text().lower();name_pattern_for_db=f"%{search_text}%" if search_text else None
        try:
            products=db_manager.get_all_products_for_selection_filtered(language_code=language_code_for_db,name_pattern=name_pattern_for_db)
            if products is None:products=[]
            for product_data in products:
                product_name=product_data.get('product_name','N/A');description=product_data.get('description','');base_unit_price=product_data.get('base_unit_price',0.0)
                if base_unit_price is None:base_unit_price=0.0
                desc_snippet=(description[:30]+'...') if len(description)>30 else description;display_text=f"{product_name} (Desc: {desc_snippet}, Prix: {base_unit_price:.2f} €)"
                item=QListWidgetItem(display_text);item.setData(Qt.UserRole,product_data);self.existing_products_list.addItem(item)
        except Exception as e:print(f"Error loading existing products: {e}");QMessageBox.warning(self,self.tr("Erreur Chargement Produits"),self.tr("Impossible de charger la liste des produits existants:\n{0}").format(str(e)))
    def _populate_form_from_selected_product(self,item):
        product_data=item.data(Qt.UserRole)
        if product_data:
            self.name_input.setText(product_data.get('product_name',''));self.description_input.setPlainText(product_data.get('description',''));base_price=product_data.get('base_unit_price',0.0)
            try:self.unit_price_input.setValue(float(base_price))
            except(ValueError,TypeError):self.unit_price_input.setValue(0.0)
            self.quantity_input.setValue(1.0)
            self.quantity_input.setFocus()

            # Populate new weight and dimensions input fields
            product_weight = product_data.get('weight', 0.0) # Default to 0.0 if not present
            self.weight_input.setValue(float(product_weight) if product_weight is not None else 0.0)

            product_dimensions = product_data.get('dimensions', '') # Default to empty string
            self.dimensions_input.setText(product_dimensions if product_dimensions is not None else "")

            # Update global display labels (renamed ones)
            self.global_weight_display_label.setText(f"{product_weight} kg" if product_weight is not None else self.tr("N/A"))
            self.global_dimensions_display_label.setText(product_dimensions if product_dimensions else self.tr("N/A"))

            self._update_current_line_total_preview()
            # Store product_id and enable detailed dimensions button
            self.current_selected_global_product_id = product_data.get('product_id')
            self.view_detailed_dimensions_button.setEnabled(bool(self.current_selected_global_product_id))
        else: # This else block handles when the selection is cleared or no product data
            self.current_selected_global_product_id = None
            self.view_detailed_dimensions_button.setEnabled(False)
            # Clear new input fields and global display labels if no product is selected
            self.weight_input.setValue(0.0)
            self.dimensions_input.clear()
            self.global_weight_display_label.setText(self.tr("N/A"))
            self.global_dimensions_display_label.setText(self.tr("N/A"))

    def _create_icon_label_widget(self,icon_name,label_text):widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5);icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget
    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(15);header_label=QLabel(self.tr("Ajouter Lignes de Produits")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)
        two_columns_layout=QHBoxLayout();search_group_box=QGroupBox(self.tr("Rechercher Produit Existant"));search_layout=QVBoxLayout(search_group_box)
        self.product_language_filter_label=QLabel(self.tr("Filtrer par langue:"));search_layout.addWidget(self.product_language_filter_label);self.product_language_filter_combo=QComboBox();self.product_language_filter_combo.addItems([self.tr("All"),"fr","en","ar","tr","pt"]);self.product_language_filter_combo.currentTextChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.product_language_filter_combo)
        self.search_existing_product_input=QLineEdit();self.search_existing_product_input.setPlaceholderText(self.tr("Tapez pour rechercher..."));self.search_existing_product_input.textChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.search_existing_product_input)
        self.existing_products_list=QListWidget();self.existing_products_list.setMinimumHeight(150);self.existing_products_list.itemDoubleClicked.connect(self._populate_form_from_selected_product);search_layout.addWidget(self.existing_products_list);two_columns_layout.addWidget(search_group_box,1)
        input_group_box=QGroupBox(self.tr("Détails de la Ligne de Produit Actuelle (ou Produit Sélectionné)"));form_layout=QFormLayout(input_group_box);form_layout.setSpacing(10); # self.setStyleSheet("QLineEdit, QTextEdit, QDoubleSpinBox { padding: 3px; }") # Prefer global
        self.name_input=QLineEdit();form_layout.addRow(self._create_icon_label_widget("package-x-generic",self.tr("Nom du Produit:")),self.name_input);self.description_input=QTextEdit();self.description_input.setFixedHeight(80);form_layout.addRow(self.tr("Description:"),self.description_input)
        self.quantity_input=QDoubleSpinBox();self.quantity_input.setRange(0,1000000);self.quantity_input.setValue(0.0);self.quantity_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("format-list-numbered",self.tr("Quantité:")),self.quantity_input)
        self.unit_price_input=QDoubleSpinBox();self.unit_price_input.setRange(0,10000000);self.unit_price_input.setPrefix("€ ");self.unit_price_input.setValue(0.0);self.unit_price_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("cash",self.tr("Prix Unitaire:")),self.unit_price_input)

        # Input for Weight (overridable)
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0.0, 10000.0) # Example range, adjust as needed
        self.weight_input.setSuffix(" kg")
        self.weight_input.setDecimals(2) # Example decimals
        self.weight_input.setValue(0.0)
        # self.weight_input.valueChanged.connect(self._update_current_line_total_preview) # If weight affects total
        form_layout.addRow(self.tr("Poids (Ligne):"), self.weight_input)

        # Input for Dimensions (overridable)
        self.dimensions_input = QLineEdit()
        self.dimensions_input.setPlaceholderText(self.tr("LxlxH cm")) # Example placeholder
        form_layout.addRow(self.tr("Dimensions (Ligne):"), self.dimensions_input)

        # Display for Weight and Dimensions (read-only from selected global product)
        self.global_weight_display_label = QLabel(self.tr("N/A")) # Renamed for clarity
        form_layout.addRow(self.tr("Poids (Global Produit):"), self.global_weight_display_label) # Updated label text
        self.global_dimensions_display_label = QLabel(self.tr("N/A")) # Renamed for clarity
        form_layout.addRow(self.tr("Dimensions (Global Produit):"), self.global_dimensions_display_label) # Updated label text

        # Button for detailed dimensions
        self.view_detailed_dimensions_button = QPushButton(self.tr("Voir Dimensions Détaillées (Global Produit)")) # Updated button text
        self.view_detailed_dimensions_button.setIcon(QIcon.fromTheme("view-fullscreen")) # Example icon
        self.view_detailed_dimensions_button.setEnabled(False) # Disabled initially
        self.view_detailed_dimensions_button.clicked.connect(self.on_view_detailed_dimensions)
        form_layout.addRow(self.view_detailed_dimensions_button)

        current_line_total_title_label=QLabel(self.tr("Total Ligne Actuelle:"));self.current_line_total_label=QLabel("€ 0.00");font=self.current_line_total_label.font();font.setBold(True);self.current_line_total_label.setFont(font);form_layout.addRow(current_line_total_title_label,self.current_line_total_label);two_columns_layout.addWidget(input_group_box,2);main_layout.addLayout(two_columns_layout)
        self.add_line_btn=QPushButton(self.tr("Ajouter Produit à la Liste"));self.add_line_btn.setIcon(QIcon(":/icons/plus-circle.svg"));self.add_line_btn.setObjectName("primaryButton");self.add_line_btn.clicked.connect(self._add_current_line_to_table);main_layout.addWidget(self.add_line_btn)
        self.products_table=QTableWidget();self.products_table.setColumnCount(5);self.products_table.setHorizontalHeaderLabels([self.tr("Nom Produit"),self.tr("Description"),self.tr("Qté"),self.tr("Prix Unitaire"),self.tr("Total Ligne")]);self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows);self.products_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeToContents);main_layout.addWidget(self.products_table)
        self.remove_line_btn=QPushButton(self.tr("Supprimer Produit Sélectionné"));self.remove_line_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_line_btn.setObjectName("removeProductLineButton"); self.remove_line_btn.clicked.connect(self._remove_selected_line_from_table);main_layout.addWidget(self.remove_line_btn) # Added objectName
        self.overall_total_label=QLabel(self.tr("Total Général: € 0.00")); font=self.overall_total_label.font();font.setPointSize(font.pointSize()+3);font.setBold(True);self.overall_total_label.setFont(font); self.overall_total_label.setObjectName("overallTotalLabel"); self.overall_total_label.setAlignment(Qt.AlignRight);main_layout.addWidget(self.overall_total_label);main_layout.addStretch()
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame"); button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0) # Style in QSS
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton");cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"));button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)
    def _update_current_line_total_preview(self):quantity=self.quantity_input.value();unit_price=self.unit_price_input.value();current_quantity=quantity if isinstance(quantity,(int,float)) else 0.0;current_unit_price=unit_price if isinstance(unit_price,(int,float)) else 0.0;line_total=current_quantity*current_unit_price;self.current_line_total_label.setText(f"€ {line_total:.2f}")
    def _add_current_line_to_table(self):
        name=self.name_input.text().strip();description=self.description_input.toPlainText().strip();quantity=self.quantity_input.value();unit_price=self.unit_price_input.value()
        current_weight = self.weight_input.value()
        current_dimensions = self.dimensions_input.text().strip()

        if not name:QMessageBox.warning(self,self.tr("Champ Requis"),self.tr("Le nom du produit est requis."));self.name_input.setFocus();return
        if quantity<=0:QMessageBox.warning(self,self.tr("Quantité Invalide"),self.tr("La quantité doit être supérieure à zéro."));self.quantity_input.setFocus();return
        line_total=quantity*unit_price;row_position=self.products_table.rowCount();self.products_table.insertRow(row_position);name_item=QTableWidgetItem(name);current_lang_code=self.product_language_filter_combo.currentText()
        if current_lang_code==self.tr("All"):current_lang_code="fr"
        name_item.setData(Qt.UserRole+1,current_lang_code)
        name_item.setData(Qt.UserRole+2, current_weight) # Store weight
        name_item.setData(Qt.UserRole+3, current_dimensions) # Store dimensions
        # Store the global product ID if one was selected, for later use in EditProductLineDialog or other features
        if self.current_selected_global_product_id is not None: # This ID comes from _populate_form_from_selected_product
            name_item.setData(Qt.UserRole + 4, self.current_selected_global_product_id)
        else: # Ensure UserRole+4 is explicitly None if no global product was selected for this line item
            name_item.setData(Qt.UserRole + 4, None)


        self.products_table.setItem(row_position,0,name_item);self.products_table.setItem(row_position,1,QTableWidgetItem(description));qty_item=QTableWidgetItem(f"{quantity:.2f}");qty_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,2,qty_item);price_item=QTableWidgetItem(f"€ {unit_price:.2f}");price_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,3,price_item);total_item=QTableWidgetItem(f"€ {line_total:.2f}");total_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,4,total_item)

        # Clear form and disable detailed dimensions button after adding line
        self.name_input.clear();self.description_input.clear();self.quantity_input.setValue(0.0);self.unit_price_input.setValue(0.0)
        self.weight_input.setValue(0.0) # Clear new weight input
        self.dimensions_input.clear() # Clear new dimensions input

        self.current_selected_global_product_id = None # Reset the stored global product ID for the form
        self.view_detailed_dimensions_button.setEnabled(False)
        self.global_weight_display_label.setText(self.tr("N/A")) # Reset global display labels (renamed ones)
        self.global_dimensions_display_label.setText(self.tr("N/A")) # Reset global display labels (renamed ones)

        self._update_current_line_total_preview();self._update_overall_total();self.name_input.setFocus()

    def on_view_detailed_dimensions(self):
        if self.current_selected_global_product_id is not None:
            dialog = ProductDimensionUIDialog(self.current_selected_global_product_id, self.app_root_dir, self, read_only=True)
            dialog.exec_()
        else:
            QMessageBox.information(self, self.tr("Aucun Produit Sélectionné"), self.tr("Veuillez d'abord sélectionner un produit dans la liste de recherche."))

    def _remove_selected_line_from_table(self):
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, self.tr("Aucune Sélection"), self.tr("Veuillez sélectionner une ligne à supprimer."))
            return
        for index in sorted(selected_rows, reverse=True):
            self.products_table.removeRow(index.row())
        self._update_overall_total()
    def _update_overall_total(self):
        total_sum=0.0
        for row in range(self.products_table.rowCount()):
            item=self.products_table.item(row,4)
            if item and item.text():
                try:value_str=item.text().replace("€","").replace(",",".").strip();total_sum+=float(value_str)
                except ValueError:print(f"Warning: Could not parse float from table cell: {item.text()}")
        self.overall_total_label.setText(self.tr("Total Général: € {0:.2f}").format(total_sum))
    def get_data(self):
        products_list=[]
        for row in range(self.products_table.rowCount()):
            name_item=self.products_table.item(row,0) # This is the QTableWidgetItem for the name column
            name=name_item.text()
            description=self.products_table.item(row,1).text()
            qty_str=self.products_table.item(row,2).text().replace(",",".");quantity=float(qty_str) if qty_str else 0.0
            unit_price_str=self.products_table.item(row,3).text().replace("€","").replace(",",".").strip();unit_price=float(unit_price_str) if unit_price_str else 0.0
            line_total_str=self.products_table.item(row,4).text().replace("€","").replace(",",".").strip();line_total=float(line_total_str) if line_total_str else 0.0

            language_code=name_item.data(Qt.UserRole+1) if name_item else "fr" # Default to 'fr' if no data
            retrieved_weight = name_item.data(Qt.UserRole+2) # Retrieve weight
            retrieved_dimensions = name_item.data(Qt.UserRole+3) # Retrieve dimensions
            retrieved_global_product_id = name_item.data(Qt.UserRole+4) # Retrieve global product ID for this line

            products_list.append({
                "client_id":self.client_id,
                "name":name,
                "description":description,
                "quantity":quantity,
                "unit_price":unit_price,
                "total_price":line_total,
                "language_code":language_code,
                "weight": float(retrieved_weight) if retrieved_weight is not None else 0.0, # Add weight to dict
                "dimensions": str(retrieved_dimensions) if retrieved_dimensions is not None else "", # Add dimensions to dict
                "product_id": retrieved_global_product_id # Add global product_id (can be None)
            })
        return products_list

class EditProductLineDialog(QDialog):
    def __init__(self, product_data, app_root_dir, parent=None): # Added app_root_dir
        super().__init__(parent)
        self.product_data = product_data
        self.app_root_dir = app_root_dir # Store app_root_dir
        self.setWindowTitle(self.tr("Modifier Ligne de Produit"))
        self.setMinimumSize(450, 300) # Adjusted for new button
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout(); form_layout.setSpacing(10)
        self.name_input = QLineEdit(self.product_data.get('name', ''))
        form_layout.addRow(self.tr("Nom du Produit:"), self.name_input)
        self.description_input = QTextEdit(self.product_data.get('description', ''))
        self.description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.description_input)

        # Editable Weight and Dimensions for the specific client product line
        self.weight_input_edit = QDoubleSpinBox()
        self.weight_input_edit.setSuffix(" kg")
        self.weight_input_edit.setRange(0.0, 10000.0) # Adjust range as needed
        self.weight_input_edit.setDecimals(2) # Adjust decimals as needed
        retrieved_weight = self.product_data.get('weight', 0.0)
        self.weight_input_edit.setValue(float(retrieved_weight) if retrieved_weight is not None else 0.0)
        form_layout.addRow(self.tr("Poids (Ligne):"), self.weight_input_edit)

        self.dimensions_input_edit = QLineEdit(self.product_data.get('dimensions', ''))
        self.dimensions_input_edit.setPlaceholderText(self.tr("LxlxH cm"))
        form_layout.addRow(self.tr("Dimensions (Ligne):"), self.dimensions_input_edit)

        # Add View Detailed Dimensions Button (references global product)
        self.view_detailed_dimensions_button = QPushButton(self.tr("Voir Dimensions Détaillées (Global Produit)"))
        self.view_detailed_dimensions_button.setIcon(QIcon.fromTheme("view-fullscreen")) # Example icon
        self.view_detailed_dimensions_button.clicked.connect(self.on_view_detailed_dimensions)
        if not self.product_data.get('product_id'): # Disable if no product_id
            self.view_detailed_dimensions_button.setEnabled(False)
        form_layout.addRow(self.view_detailed_dimensions_button)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.01, 1000000)
        self.quantity_input.setValue(float(self.product_data.get('quantity', 1.0)))
        form_layout.addRow(self.tr("Quantité:"), self.quantity_input)
        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0.00, 10000000); self.unit_price_input.setPrefix("€ "); self.unit_price_input.setDecimals(2)
        self.unit_price_input.setValue(float(self.product_data.get('unit_price', 0.0)))
        form_layout.addRow(self.tr("Prix Unitaire:"), self.unit_price_input)
        layout.addLayout(form_layout); layout.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK")); button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box); self.setLayout(layout)

    def on_view_detailed_dimensions(self):
        product_id = self.product_data.get('product_id')
        if product_id is not None:
            dialog = ProductDimensionUIDialog(product_id, self.app_root_dir, self, read_only=True)
            dialog.exec_()
        else:
            QMessageBox.information(self, self.tr("ID Produit Manquant"), self.tr("Aucun ID de produit global associé à cette ligne."))

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "quantity": self.quantity_input.value(),
            "unit_price": self.unit_price_input.value(),
            "weight": self.weight_input_edit.value(), # Get value from new QDoubleSpinBox
            "dimensions": self.dimensions_input_edit.text().strip(), # Get text from new QLineEdit
            "product_id": self.product_data.get('product_id'), # This is the global product ID
            "client_project_product_id": self.product_data.get('client_project_product_id') # ID of this specific client product line
        }

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config passed from main
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 500)
        self._initial_load_complete = False
        self.setup_ui()

    def _create_icon_label_widget(self, icon_name, label_text):
        widget = QWidget(); layout = QHBoxLayout(widget); layout.setContentsMargins(0,0,0,0); layout.setSpacing(5)
        icon_label = QLabel(); icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16)); layout.addWidget(icon_label); layout.addWidget(QLabel(label_text))
        return widget

    def setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setSpacing(15)
        header_label = QLabel(self.tr("Sélectionner Documents à Créer")); header_label.setObjectName("dialogHeaderLabel")
        main_layout.addWidget(header_label)
        # self.setStyleSheet("QComboBox, QListWidget, QLineEdit { padding: 3px; } QListWidget::item:hover { background-color: #e6f7ff; }") # Prefer global styles
        filters_layout = QGridLayout(); filters_layout.setSpacing(10)
        self.language_filter_label = QLabel(self.tr("Langue:")); self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"]); self.language_filter_combo.setCurrentText(self.tr("All"))
        filters_layout.addWidget(self.language_filter_label, 0, 0); filters_layout.addWidget(self.language_filter_combo, 0, 1)
        self.extension_filter_label = QLabel(self.tr("Extension:")); self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([self.tr("All"), "HTML", "XLSX", "DOCX"]); self.extension_filter_combo.setCurrentText("HTML")
        filters_layout.addWidget(self.extension_filter_label, 0, 2); filters_layout.addWidget(self.extension_filter_combo, 0, 3)
        self.search_bar_label = QLabel(self.tr("Rechercher:")); self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText(self.tr("Filtrer par nom..."))
        filters_layout.addWidget(self.search_bar_label, 1, 0); filters_layout.addWidget(self.search_bar, 1, 1, 1, 3)
        main_layout.addLayout(filters_layout)
        templates_list_label = self._create_icon_label_widget("document-multiple", self.tr("Modèles disponibles:")); main_layout.addWidget(templates_list_label)
        self.templates_list = QListWidget(); self.templates_list.setSelectionMode(QListWidget.MultiSelection); main_layout.addWidget(self.templates_list)
        self.language_filter_combo.currentTextChanged.connect(self.load_templates)
        self.extension_filter_combo.currentTextChanged.connect(self.load_templates)
        self.search_bar.textChanged.connect(self.load_templates)
        self.load_templates(); main_layout.addStretch()
        button_frame = QFrame(self); button_frame.setObjectName("buttonFrame") # Style in QSS
        button_frame_layout = QHBoxLayout(button_frame); button_frame_layout.setContentsMargins(0,0,0,0)
        create_btn = QPushButton(self.tr("Créer Documents")); create_btn.setIcon(QIcon(":/icons/file-plus.svg")); create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(self.create_documents); button_frame_layout.addWidget(create_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        cancel_btn.clicked.connect(self.reject); button_frame_layout.addWidget(cancel_btn)
        main_layout.addWidget(button_frame)

    def load_templates(self):
        self.templates_list.clear()
        if not self._initial_load_complete:
            primary_language = None; client_langs = self.client_info.get('selected_languages')
            if client_langs:
                if isinstance(client_langs, list) and client_langs: primary_language = client_langs[0]
                elif isinstance(client_langs, str) and client_langs.strip(): primary_language = client_langs.split(',')[0].strip()
            if primary_language and self.language_filter_combo.currentText() == self.tr("All"):
                for i in range(self.language_filter_combo.count()):
                    if self.language_filter_combo.itemText(i) == primary_language: self.language_filter_combo.setCurrentText(primary_language); break
            self._initial_load_complete = True
        selected_lang = self.language_filter_combo.currentText(); selected_ext_display = self.extension_filter_combo.currentText(); search_text = self.search_bar.text().lower()
        ext_map = {"HTML": ".html", "XLSX": ".xlsx", "DOCX": ".docx"}; selected_ext = ext_map.get(selected_ext_display)
        try:
            all_file_templates = db_manager.get_all_file_based_templates();
            if all_file_templates is None: all_file_templates = []
            filtered_templates = []
            for template_dict in all_file_templates:
                name = template_dict.get('template_name', 'N/A'); lang_code = template_dict.get('language_code', 'N/A'); base_file_name = template_dict.get('base_file_name', 'N/A')
                if selected_lang != self.tr("All") and lang_code != selected_lang: continue
                file_actual_ext = os.path.splitext(base_file_name)[1].lower()
                if selected_ext_display != self.tr("All"):
                    if not selected_ext or file_actual_ext != selected_ext: continue
                if search_text and search_text not in name.lower(): continue
                filtered_templates.append(template_dict)
            for template_dict in filtered_templates:
                name = template_dict.get('template_name', 'N/A'); lang = template_dict.get('language_code', 'N/A'); base_file_name = template_dict.get('base_file_name', 'N/A')
                item_text = f"{name} ({lang}) - {base_file_name}"; item = QListWidgetItem(item_text)
                # Store the whole template_dict for richer data access later
                item.setData(Qt.UserRole, template_dict); self.templates_list.addItem(item)
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{0}").format(str(e)))

    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items: QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer.")); return
        created_files_count = 0

        default_company_obj = db_manager.get_default_company()
        default_company_id = default_company_obj['company_id'] if default_company_obj else None
        if default_company_id is None:
            QMessageBox.warning(self, self.tr("Avertissement"), self.tr("Aucune société par défaut n'est définie. Les détails du vendeur peuvent être manquants."))
            # Allow proceeding, context will handle missing seller info gracefully

        client_id_for_context = self.client_info.get('client_id')
        # Initial project_id from client_info, can be overridden by additional_context
        project_id_for_context_arg = self.client_info.get('project_id', self.client_info.get('project_identifier'))

        for item in selected_items:
            template_data = item.data(Qt.UserRole)
            if not isinstance(template_data, dict): # Check if data is a dict
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Données de modèle invalides pour l'élément sélectionné."))
                continue

            db_template_name = template_data.get('template_name', 'N/A')
            db_template_lang = template_data.get('language_code', 'N/A')
            actual_template_filename = template_data.get('base_file_name', None)
            template_type = template_data.get('template_type', 'UNKNOWN')
            # template_id = template_data.get('template_id') # Available if needed

            target_dir_for_document = os.path.join(self.client_info["base_folder_path"], db_template_lang)
            os.makedirs(target_dir_for_document, exist_ok=True)

            if not actual_template_filename:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name)); continue

            template_file_found_abs = os.path.join(self.config["templates_dir"], db_template_lang, actual_template_filename)

            if os.path.exists(template_file_found_abs):
                target_path = os.path.join(target_dir_for_document, actual_template_filename)
                try:
                    shutil.copy(template_file_found_abs, target_path)

                    additional_context = {} # Initialize for each document
                    # Copy general client info that might be used as fallbacks by get_document_context_data
                    # or for non-packing list documents.
                    # For instance, project_id, invoice_id if they are top-level in self.client_info
                    if 'project_id' in self.client_info: additional_context['project_id'] = self.client_info['project_id']
                    if 'invoice_id' in self.client_info: additional_context['invoice_id'] = self.client_info['invoice_id'] # Example

                    if template_type == 'HTML_PACKING_LIST':
                        additional_context['document_type'] = 'packing_list'
                        additional_context['current_document_type_for_notes'] = 'HTML_PACKING_LIST' # Or template_type

                        packing_details_payload = {}
                        linked_products = db_manager.get_products_for_client_or_project(
                            client_id_for_context,
                            project_id=project_id_for_context_arg # Use client/project specific products
                        )
                        linked_products = linked_products if linked_products else []

                        packing_items_data = []
                        total_net_w = 0.0
                        total_gross_w = 0.0
                        total_pkg_count = 0

                        for idx, prod_data in enumerate(linked_products):
                            net_w = float(prod_data.get('weight', 0.0) or 0.0)
                            quantity = float(prod_data.get('quantity', 1.0) or 1.0)
                            gross_w = net_w * 1.05 # Example: 5% markup for packaging
                            dims = prod_data.get('dimensions', 'N/A')
                            num_pkgs = 1 # Default, could be based on quantity or product settings
                            pkg_type = 'Carton' # Default

                            packing_items_data.append({
                                'marks_nos': f'BOX {total_pkg_count + 1}',
                                'product_id': prod_data.get('product_id'),
                                'product_name_override': None, # Let context resolver handle name
                                'quantity_description': f"{quantity} {prod_data.get('unit_of_measure', 'unit(s)')}",
                                'num_packages': num_pkgs,
                                'package_type': pkg_type,
                                'net_weight_kg_item': net_w * quantity,
                                'gross_weight_kg_item': gross_w * quantity,
                                'dimensions_cm_item': dims
                            })
                            total_net_w += net_w * quantity
                            total_gross_w += gross_w * quantity
                            total_pkg_count += num_pkgs

                        if not linked_products:
                            packing_items_data.append({
                                'marks_nos': 'N/A', 'product_id': None, 'product_name_override': 'No products linked to client/project.',
                                'quantity_description': '', 'num_packages': 0, 'package_type': '',
                                'net_weight_kg_item': 0, 'gross_weight_kg_item': 0, 'dimensions_cm_item': ''
                            })

                        packing_details_payload['items'] = packing_items_data
                        packing_details_payload['total_packages'] = total_pkg_count
                        packing_details_payload['total_net_weight_kg'] = round(total_net_w, 2)
                        packing_details_payload['total_gross_weight_kg'] = round(total_gross_w, 2)
                        packing_details_payload['total_volume_cbm'] = 'N/A' # Placeholder, implement calculation if needed

                        # Override IDs for the packing list document itself
                        client_project_identifier = self.client_info.get('project_identifier', self.client_info.get('client_id', 'NOID')) # Fallback
                        timestamp_str = datetime.now().strftime('%Y%m%d')
                        additional_context['packing_list_id'] = f"PL-{client_project_identifier}-{timestamp_str}"
                        additional_context['invoice_id'] = f"INVREF-{client_project_identifier}-{timestamp_str}" # Reference invoice
                        additional_context['project_id'] = self.client_info.get('project_identifier', 'N/A') # Display project ID on doc

                        additional_context['packing_details'] = packing_details_payload
                    else:
                        # For non-packing lists, pass relevant parts of client_info
                        # or a more generic context.
                        # Making a copy to avoid modifying self.client_info if it's a shared object.
                        additional_context.update(self.client_info.copy())
                        additional_context['document_type'] = template_type
                        # Ensure current_document_type_for_notes is set if notes are used for other HTML docs
                        if template_type.startswith("HTML_"):
                             additional_context['current_document_type_for_notes'] = template_type


                    if target_path.lower().endswith(".docx"):
                        # For docx, additional_context might need to be self.client_info directly
                        # or a transformation of it, depending on populate_docx_template needs.
                        # For now, assuming populate_docx_template uses self.client_info format.
                        populate_docx_template(target_path, self.client_info)
                    elif target_path.lower().endswith(".html"):
                        with open(target_path, 'r', encoding='utf-8') as f: template_content = f.read()

                        document_context = db_manager.get_document_context_data(
                            client_id=client_id_for_context,
                            company_id=default_company_id,
                            target_language_code=db_template_lang,
                            project_id=project_id_for_context_arg, # Main project context
                            additional_context=additional_context # Contains overrides and specific data like packing_details
                        )
                        populated_content = HtmlEditor.populate_html_content(template_content, document_context)
                        with open(target_path, 'w', encoding='utf-8') as f: f.write(populated_content)

                    created_files_count += 1
                except Exception as e_create: QMessageBox.warning(self, self.tr("Erreur Création Document"), self.tr("Impossible de créer ou populer le document '{0}':\n{1}").format(actual_template_filename, e_create))
            else: QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))
        if created_files_count > 0: QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(created_files_count)); self.accept()
        elif not selected_items: pass
        else: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé. Vérifiez les erreurs précédentes."))

class CompilePdfDialog(QDialog):
    def __init__(self, client_info, config, app_root_dir, parent=None): # Added config and app_root_dir
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config
        self.app_root_dir = app_root_dir # Store app_root_dir
        self.setWindowTitle(self.tr("Compiler des PDF"))
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Sélectionnez les PDF à compiler:")))
        self.pdf_list = QTableWidget(); self.pdf_list.setColumnCount(4)
        self.pdf_list.setHorizontalHeaderLabels([self.tr("Sélection"), self.tr("Nom du fichier"), self.tr("Chemin"), self.tr("Pages (ex: 1-3,5)")])
        self.pdf_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.pdf_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pdf_list)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(self.tr("Ajouter PDF")); add_btn.setIcon(QIcon(":/icons/plus.svg")); add_btn.clicked.connect(self.add_pdf); btn_layout.addWidget(add_btn)
        remove_btn = QPushButton(self.tr("Supprimer")); remove_btn.setIcon(QIcon(":/icons/trash.svg")); remove_btn.clicked.connect(self.remove_selected); btn_layout.addWidget(remove_btn)
        move_up_btn = QPushButton(self.tr("Monter")); move_up_btn.setIcon(QIcon.fromTheme("go-up")); move_up_btn.clicked.connect(self.move_up); btn_layout.addWidget(move_up_btn) # go-up not in list
        move_down_btn = QPushButton(self.tr("Descendre")); move_down_btn.setIcon(QIcon.fromTheme("go-down")); move_down_btn.clicked.connect(self.move_down); btn_layout.addWidget(move_down_btn) # go-down not in list
        layout.addLayout(btn_layout)
        options_layout = QHBoxLayout(); options_layout.addWidget(QLabel(self.tr("Nom du fichier compilé:")))
        self.output_name = QLineEdit(f"{self.tr('compilation')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"); options_layout.addWidget(self.output_name); layout.addLayout(options_layout)
        action_layout = QHBoxLayout()
        compile_btn = QPushButton(self.tr("Compiler PDF")); compile_btn.setIcon(QIcon(":/icons/download.svg")); compile_btn.setObjectName("primaryButton")
        compile_btn.clicked.connect(self.compile_pdf); action_layout.addWidget(compile_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg")); cancel_btn.clicked.connect(self.reject); action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)
        self.load_existing_pdfs()

    def load_existing_pdfs(self):
        client_dir = self.client_info["base_folder_path"]; pdf_files = []
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.lower().endswith('.pdf'): pdf_files.append(os.path.join(root, file))
        self.pdf_list.setRowCount(len(pdf_files))
        for i, file_path in enumerate(pdf_files):
            chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(i, 0, chk)
            self.pdf_list.setItem(i, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(i, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(i, 3, pages_edit)

    def add_pdf(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des PDF"), "", self.tr("Fichiers PDF (*.pdf)"));
        if not file_paths: return
        current_row_count = self.pdf_list.rowCount(); self.pdf_list.setRowCount(current_row_count + len(file_paths))
        for i, file_path in enumerate(file_paths):
            row = current_row_count + i; chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(row, 0, chk)
            self.pdf_list.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path))); self.pdf_list.setItem(row, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(row, 3, pages_edit)

    def remove_selected(self):
        selected_rows = set(index.row() for index in self.pdf_list.selectedIndexes())
        for row in sorted(selected_rows, reverse=True): self.pdf_list.removeRow(row)

    def move_up(self):
        current_row = self.pdf_list.currentRow()
        if current_row > 0: self.swap_rows(current_row, current_row - 1); self.pdf_list.setCurrentCell(current_row - 1, 0)

    def move_down(self):
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.rowCount() - 1: self.swap_rows(current_row, current_row + 1); self.pdf_list.setCurrentCell(current_row + 1, 0)

    def swap_rows(self, row1, row2):
        for col in range(self.pdf_list.columnCount()):
            item1 = self.pdf_list.takeItem(row1, col); item2 = self.pdf_list.takeItem(row2, col)
            self.pdf_list.setItem(row1, col, item2); self.pdf_list.setItem(row2, col, item1)
        widget1 = self.pdf_list.cellWidget(row1,0); widget3 = self.pdf_list.cellWidget(row1,3); widget2 = self.pdf_list.cellWidget(row2,0); widget4 = self.pdf_list.cellWidget(row2,3)
        self.pdf_list.setCellWidget(row1,0,widget2); self.pdf_list.setCellWidget(row1,3,widget4); self.pdf_list.setCellWidget(row2,0,widget1); self.pdf_list.setCellWidget(row2,3,widget3)

    def compile_pdf(self):
        merger = PdfMerger(); output_name = self.output_name.text().strip()
        if not output_name: QMessageBox.warning(self, self.tr("Nom manquant"), self.tr("Veuillez spécifier un nom de fichier pour la compilation.")); return
        if not output_name.lower().endswith('.pdf'): output_name += '.pdf'
        output_path = os.path.join(self.client_info["base_folder_path"], output_name)
        cover_path = self.create_cover_page()
        if cover_path: merger.append(cover_path)
        for row in range(self.pdf_list.rowCount()):
            chk = self.pdf_list.cellWidget(row, 0)
            if chk and chk.isChecked():
                file_path = self.pdf_list.item(row, 2).text(); pages_spec = self.pdf_list.cellWidget(row, 3).text().strip()
                try:
                    if pages_spec.lower() == "all" or not pages_spec: merger.append(file_path)
                    else:
                        pages = [];
                        for part in pages_spec.split(','):
                            if '-' in part: start, end = part.split('-'); pages.extend(range(int(start), int(end)+1))
                            else: pages.append(int(part))
                        merger.append(file_path, pages=[p-1 for p in pages])
                except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de {0}:\n{1}").format(os.path.basename(file_path), str(e)))
        try:
            with open(output_path, 'wb') as f: merger.write(f)
            if cover_path and os.path.exists(cover_path): os.remove(cover_path)
            QMessageBox.information(self, self.tr("Compilation réussie"), self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(output_path))
            self.offer_download_or_email(output_path); self.accept()
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la compilation du PDF:\n{0}").format(str(e)))

    def create_cover_page(self):
        config_dict = {'title': self.tr("Compilation de Documents - Projet: {0}").format(self.client_info.get('project_identifier', self.tr('N/A'))),
                       'subtitle': self.tr("Client: {0}").format(self.client_info.get('client_name', self.tr('N/A'))),
                       'author': self.client_info.get('company_name', PAGEDEGRDE_APP_CONFIG.get('default_institution', self.tr('Votre Entreprise'))),
                       'institution': "", 'department': "", 'doc_type': self.tr("Compilation de Documents"),
                       'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'version': "1.0",
                       'font_name': PAGEDEGRDE_APP_CONFIG.get('default_font', 'Helvetica'), 'font_size_title': 20, 'font_size_subtitle': 16, 'font_size_author': 10,
                       'text_color': PAGEDEGRDE_APP_CONFIG.get('default_text_color', '#000000'), 'template_style': 'Moderne', 'show_horizontal_line': True, 'line_y_position_mm': 140,
                       'logo_data': None, 'logo_width_mm': 40, 'logo_height_mm': 40, 'logo_x_mm': 25, 'logo_y_mm': 297 - 25 - 40,
                       'margin_top': 25, 'margin_bottom': 25, 'margin_left': 20, 'margin_right': 20,
                       'footer_text': self.tr("Document compilé le {0}").format(datetime.now().strftime('%d/%m/%Y'))}
        logo_path = os.path.join(self.app_root_dir, "logo.png") # Use self.app_root_dir
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_logo: config_dict['logo_data'] = f_logo.read()
            except Exception as e_logo: print(self.tr("Erreur chargement logo.png: {0}").format(e_logo))
        try:
            pdf_bytes = generate_cover_page_logic(config_dict) # Uses imported generate_cover_page_logic
            base_temp_dir = self.client_info.get("base_folder_path", QDir.tempPath()); temp_cover_filename = f"cover_page_generated_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf"
            temp_cover_path = os.path.join(base_temp_dir, temp_cover_filename)
            with open(temp_cover_path, "wb") as f: f.write(pdf_bytes)
            return temp_cover_path
        except Exception as e: print(self.tr("Erreur lors de la génération de la page de garde via pagedegrde: {0}").format(e)); QMessageBox.warning(self, self.tr("Erreur Page de Garde"), self.tr("Impossible de générer la page de garde personnalisée: {0}").format(e)); return None

    def offer_download_or_email(self, pdf_path):
        msg_box = QMessageBox(self); msg_box.setWindowTitle(self.tr("Compilation réussie")); msg_box.setText(self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(pdf_path))
        download_btn = msg_box.addButton(self.tr("Télécharger"), QMessageBox.ActionRole); email_btn = msg_box.addButton(self.tr("Envoyer par email"), QMessageBox.ActionRole)
        close_btn = msg_box.addButton(self.tr("Fermer"), QMessageBox.RejectRole)
        msg_box.exec_()
        if msg_box.clickedButton() == download_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn: self.send_email(pdf_path)

    def send_email(self, pdf_path):
        primary_email = None; client_uuid = self.client_info.get("client_id")
        if client_uuid:
            contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
            if contacts_for_client:
                for contact in contacts_for_client:
                    if contact.get('is_primary_for_client'): primary_email = contact.get('email'); break
        email, ok = QInputDialog.getText(self, self.tr("Envoyer par email"), self.tr("Adresse email du destinataire:"), text=primary_email or "")
        if not ok or not email.strip(): return
        # Use self.config for SMTP settings
        if not self.config.get("smtp_server") or not self.config.get("smtp_user"): QMessageBox.warning(self, self.tr("Configuration manquante"), self.tr("Veuillez configurer les paramètres SMTP dans les paramètres de l'application.")); return
        msg = MIMEMultipart(); msg['From'] = self.config["smtp_user"]; msg['To'] = email; msg['Subject'] = self.tr("Documents compilés - {0}").format(self.client_info['client_name'])
        body = self.tr("Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe").format(self.client_info['project_identifier']); msg.attach(MIMEText(body, 'plain'))
        with open(pdf_path, 'rb') as f: part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'; msg.attach(part)
        try:
            server = smtplib.SMTP(self.config["smtp_server"], self.config.get("smtp_port", 587))
            if self.config.get("smtp_port", 587) == 587: server.starttls()
            server.login(self.config["smtp_user"], self.config["smtp_password"]); server.send_message(msg); server.quit()
            QMessageBox.information(self, self.tr("Email envoyé"), self.tr("Le document a été envoyé avec succès."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur d'envoi"), self.tr("Erreur lors de l'envoi de l'email:\n{0}").format(str(e)))

class EditClientDialog(QDialog):
    def __init__(self, client_info, config, parent=None): # Config is passed but not explicitly used in original for DB path
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.tr("Modifier Client")); self.setMinimumSize(500, 430)
        layout = QFormLayout(self); layout.setSpacing(10)
        self.client_name_input = QLineEdit(self.client_info.get('client_name', '')); layout.addRow(self.tr("Nom Client:"), self.client_name_input)
        self.company_name_input = QLineEdit(self.client_info.get('company_name', '')); layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)
        self.client_need_input = QLineEdit(self.client_info.get('primary_need_description', self.client_info.get('need',''))); layout.addRow(self.tr("Besoin Client:"), self.client_need_input)
        self.project_id_input_field = QLineEdit(self.client_info.get('project_identifier', '')); layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ "); self.final_price_input.setRange(0,10000000); self.final_price_input.setValue(float(self.client_info.get('price',0.0))); self.final_price_input.setReadOnly(True)
        price_info_label = QLabel(self.tr("Le prix final est calculé à partir des produits et n'est pas modifiable ici.")); price_info_label.setObjectName("priceInfoLabel")
        price_layout = QHBoxLayout(); price_layout.addWidget(self.final_price_input); price_layout.addWidget(price_info_label); layout.addRow(self.tr("Prix Final:"), price_layout)
        self.status_select_combo = QComboBox(); self.populate_statuses()
        current_status_id = self.client_info.get('status_id')
        if current_status_id is not None:
            index = self.status_select_combo.findData(current_status_id)
            if index >= 0: self.status_select_combo.setCurrentIndex(index)
        layout.addRow(self.tr("Statut Client:"), self.status_select_combo)
        self.category_input = QLineEdit(self.client_info.get('category', '')); layout.addRow(self.tr("Catégorie:"), self.category_input)
        self.notes_edit = QTextEdit(self.client_info.get('notes', '')); self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client...")); self.notes_edit.setFixedHeight(80); layout.addRow(self.tr("Notes:"), self.notes_edit)
        self.country_select_combo = QComboBox(); self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion); self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.populate_countries()
        current_country_id = self.client_info.get('country_id')
        if current_country_id is not None:
            index = self.country_select_combo.findData(current_country_id)
            if index >= 0:
                self.country_select_combo.setCurrentIndex(index)
            else:
                current_country_name = self.client_info.get('country')
                if current_country_name:
                    index_name = self.country_select_combo.findText(current_country_name)
                    if index_name >= 0:
                        self.country_select_combo.setCurrentIndex(index_name)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country_edit); layout.addRow(self.tr("Pays Client:"), self.country_select_combo)
        self.city_select_combo = QComboBox(); self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion); self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.load_cities_for_country_edit(self.country_select_combo.currentText())
        current_city_id = self.client_info.get('city_id')
        if current_city_id is not None:
            index = self.city_select_combo.findData(current_city_id)
            if index >= 0:
                self.city_select_combo.setCurrentIndex(index)
            else:
                current_city_name = self.client_info.get('city')
                if current_city_name:
                    index_name = self.city_select_combo.findText(current_city_name)
                    if index_name >= 0:
                        self.city_select_combo.setCurrentIndex(index_name)
        layout.addRow(self.tr("Ville Client:"), self.city_select_combo)
        self.language_select_combo = QComboBox()
        self.lang_display_to_codes_map = {self.tr("Français uniquement (fr)"): ["fr"], self.tr("Arabe uniquement (ar)"): ["ar"], self.tr("Turc uniquement (tr)"): ["tr"], self.tr("Toutes les langues (fr, ar, tr)"): ["fr", "ar", "tr"]}
        self.language_select_combo.addItems(list(self.lang_display_to_codes_map.keys()))
        current_lang_codes = self.client_info.get('selected_languages', ['fr'])
        if not isinstance(current_lang_codes, list): current_lang_codes = [code.strip() for code in str(current_lang_codes).split(',') if code.strip()]
        selected_display_string = None
        for display_string, codes_list in self.lang_display_to_codes_map.items():
            if sorted(codes_list) == sorted(current_lang_codes): selected_display_string = display_string; break
        if selected_display_string: self.language_select_combo.setCurrentText(selected_display_string)
        else: self.language_select_combo.setCurrentText(self.tr("Français uniquement (fr)"))
        layout.addRow(self.tr("Langues:"), self.language_select_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK")); button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject); layout.addRow(button_box)

    def populate_statuses(self):
        self.status_select_combo.clear()
        try:
            statuses = db_manager.get_all_status_settings(status_type='Client')
            if statuses is None: statuses = []
            for status_dict in statuses: self.status_select_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts client:\n{0}").format(str(e)))

    def populate_countries(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries: self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))

    def load_cities_for_country_edit(self, country_name_str):
        self.city_select_combo.clear();
        if not country_name_str: return
        selected_country_id = self.country_select_combo.currentData()
        if selected_country_id is None:
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name: selected_country_id = country_obj_by_name['country_id']
            else: return
        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities: self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def get_data(self) -> dict:
        data = {}; data['client_name'] = self.client_name_input.text().strip(); data['company_name'] = self.company_name_input.text().strip()
        data['primary_need_description'] = self.client_need_input.text().strip(); data['project_identifier'] = self.project_id_input_field.text().strip()
        data['price'] = self.final_price_input.value(); data['status_id'] = self.status_select_combo.currentData()
        data['category'] = self.category_input.text().strip(); data['notes'] = self.notes_edit.toPlainText().strip()
        country_id = self.country_select_combo.currentData()
        if country_id is None:
            country_name = self.country_select_combo.currentText().strip()
            if country_name:
                country_obj = db_manager.get_country_by_name(country_name)
                if country_obj: country_id = country_obj['country_id']
        data['country_id'] = country_id
        city_id = self.city_select_combo.currentData()
        if city_id is None:
            city_name = self.city_select_combo.currentText().strip()
            if city_name and data.get('country_id') is not None:
                city_obj = db_manager.get_city_by_name_and_country_id(city_name, data['country_id'])
                if city_obj: city_id = city_obj['city_id']
        data['city_id'] = city_id
        selected_lang_display_text = self.language_select_combo.currentText()
        lang_codes_list = self.lang_display_to_codes_map.get(selected_lang_display_text, ["fr"])
        data['selected_languages'] = ",".join(lang_codes_list)
        return data

# DIALOG CLASSES MOVED FROM MAIN.PY END HERE

class SendEmailDialog(QDialog):
    def __init__(self, client_email, config, client_id=None, parent=None): # Added client_id
        super().__init__(parent)
        self.client_email = client_email
        self.config = config
        self.client_id = client_id # Store client_id
        self.client_info = None
        if self.client_id:
            try:
                self.client_info = db_manager.get_client_by_id(self.client_id)
            except Exception as e:
                print(f"Error fetching client_info in SendEmailDialog: {e}")
                # Optionally, show a non-critical error to the user or log it
                # QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("Impossible de charger les informations du client."))
        self.attachments = []  # List to store paths of attachments
        self.active_template_type = None # Initialize active template type

        self.setWindowTitle(self.tr("Envoyer un Email"))
        self.setMinimumSize(600, 550) # Increased min height for new button
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        to_layout = QHBoxLayout() # Layout for "To" field and "Select Contacts" button
        self.to_edit = QLineEdit(self.client_email)
        to_layout.addWidget(self.to_edit)

        if self.client_id: # Only add button if client_id is available
            self.select_contacts_btn = QPushButton(self.tr("Sélectionner Contacts"))
            self.select_contacts_btn.setIcon(QIcon.fromTheme("address-book-new", QIcon(":/icons/user-plus.svg"))) # Example icon
            self.select_contacts_btn.clicked.connect(self.open_select_contacts_dialog)
            to_layout.addWidget(self.select_contacts_btn)

        form_layout.addRow(self.tr("À:"), to_layout)

        # Template Selection UI
        template_selection_layout = QHBoxLayout()
        form_layout.addRow(self.tr("Modèle d'Email:"), template_selection_layout)

        self.language_combo = QComboBox()
        self.language_combo.setPlaceholderText(self.tr("Langue..."))
        template_selection_layout.addWidget(self.language_combo)

        self.template_combo = QComboBox()
        self.template_combo.setPlaceholderText(self.tr("Sélectionner un modèle..."))
        template_selection_layout.addWidget(self.template_combo)

        # Subject and Body
        self.subject_edit = QLineEdit()
        form_layout.addRow(self.tr("Sujet:"), self.subject_edit)

        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText(self.tr("Saisissez votre message ici ou sélectionnez un modèle..."))
        form_layout.addRow(self.tr("Corps:"), self.body_edit)

        layout.addLayout(form_layout)

        # Initialize template related attributes
        self.email_template_types = ['EMAIL_BODY_HTML', 'EMAIL_BODY_TXT'] # Define here for clarity
        self.default_company_id = None
        try:
            default_company_obj = db_manager.get_default_company()
            if default_company_obj:
                self.default_company_id = default_company_obj.get('company_id')
        except Exception as e:
            print(f"Error fetching default company ID: {e}")

        # Connect signals for template selection
        self.language_combo.currentTextChanged.connect(self.load_email_templates)
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)

        # Load initial template data
        self.load_available_languages()
        # self.load_email_templates() will be called by load_available_languages signal or explicitly if needed
        # However, it's better to explicitly call it after languages are loaded if there's a default language.
        if self.language_combo.count() > 0: # If languages were loaded and one is selected
            self.load_email_templates(self.language_combo.currentText())


    def load_available_languages(self):
        self.language_combo.blockSignals(True)
        self.language_combo.clear()

        available_langs = set()
        try:
            for template_type in self.email_template_types:
                langs = db_manager.get_distinct_languages_for_template_type(template_type)
                if langs:
                    available_langs.update(lang_tuple[0] for lang_tuple in langs if lang_tuple and lang_tuple[0])
        except Exception as e:
            print(f"Error loading available languages for email templates: {e}")
            # Fallback to a default list or handle error
            available_langs.update(["fr", "en"]) # Default fallback

        sorted_langs = sorted(list(available_langs))
        self.language_combo.addItems(sorted_langs)

        preferred_lang_set = False
        if self.client_info and self.client_info.get('selected_languages'):
            client_langs_str = self.client_info['selected_languages']
            client_langs_list = [lang.strip() for lang in client_langs_str.split(',') if lang.strip()]
            if client_langs_list:
                first_client_lang = client_langs_list[0]
                if first_client_lang in sorted_langs:
                    self.language_combo.setCurrentText(first_client_lang)
                    preferred_lang_set = True

        if not preferred_lang_set and sorted_langs: # Default to first available if client pref not set/found
            self.language_combo.setCurrentIndex(0)

        self.language_combo.blockSignals(False)
        # Manually trigger template loading for the initially set language
        if self.language_combo.currentText():
             self.load_email_templates(self.language_combo.currentText())


    def load_email_templates(self, language_code):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem(self.tr("--- Aucun Modèle ---"), None) # "None" option

        if not language_code:
            self.template_combo.blockSignals(False)
            self.on_template_selected(0) # Trigger body clearing etc.
            return

        try:
            all_templates_for_lang = []
            for template_type in self.email_template_types:
                # Corrected function call: get_templates_by_type
                templates = db_manager.get_templates_by_type(
                    template_type=template_type,
                    language_code=language_code
                )
                if templates:
                    all_templates_for_lang.extend(templates)

            # Sort templates by name, for example
            all_templates_for_lang.sort(key=lambda x: x.get('template_name', ''))

            for template in all_templates_for_lang:
                self.template_combo.addItem(template['template_name'], template['template_id'])
        except Exception as e:
            print(f"Error loading email templates for lang {language_code}: {e}")
            QMessageBox.warning(self, self.tr("Erreur Modèles Email"),
                                self.tr("Impossible de charger les modèles d'email pour la langue {0}:\n{1}").format(language_code, str(e)))

        self.template_combo.blockSignals(False)
        self.on_template_selected(self.template_combo.currentIndex()) # Ensure consistent state after loading


    def on_template_selected(self, index):
        template_id = self.template_combo.itemData(index)
        self.active_template_type = None # Reset by default

        if template_id is None: # "--- Aucun Modèle ---" selected
            self.body_edit.setPlainText("")
            self.body_edit.setReadOnly(False)
            self.subject_edit.setText("") # Clear subject too
            # self.subject_edit.setReadOnly(False) # If subject was also read-only
            # self.active_template_type already None
            return

        try:
            template_details = db_manager.get_template_details_by_id(template_id) # Ensure this method exists and fetches all needed details
            if not template_details:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Détails du modèle non trouvés."))
                self.body_edit.setPlainText("")
                self.body_edit.setReadOnly(False)
                return

            template_lang = template_details.get('language_code')
            base_file_name = template_details.get('base_file_name')
            template_type = template_details.get('template_type')
            self.active_template_type = template_type # Store active template type
            email_subject_template = template_details.get('email_subject_template')

            if not self.config or "templates_dir" not in self.config:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le dossier des modèles n'est pas configuré."))
                return

            template_file_path = os.path.join(self.config["templates_dir"], template_lang, base_file_name)

            if not os.path.exists(template_file_path):
                QMessageBox.warning(self, self.tr("Erreur Fichier Modèle"),
                                    self.tr("Fichier modèle introuvable:\n{0}").format(template_file_path))
                self.body_edit.setPlainText("")
                self.body_edit.setReadOnly(False)
                return

            with open(template_file_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Fetch context data
            context_data = {}
            if self.client_info and self.client_info.get('client_id'):
                # Ensure get_document_context_data can handle None for project_id if not always present
                context_data = db_manager.get_document_context_data(
                    client_id=self.client_info['client_id'],
                    company_id=self.default_company_id, # Fetched in constructor
                    target_language_code=template_lang,
                    project_id=self.client_info.get('project_id') # Pass project_id if available
                )
            else: # Minimal context if no client_info (e.g. sending general email)
                if self.default_company_id:
                     company_details = db_manager.get_company_by_id(self.default_company_id)
                     if company_details : context_data['seller'] = company_details
                # Add other generic placeholders if needed

            # Populate content
            populated_body = ""
            if template_type == 'EMAIL_BODY_HTML':
                # HtmlEditor.populate_html_content expects client_info and company_id separately
                # We should adapt or use a more generic placeholder replacement for context_data
                # For now, let's assume HtmlEditor.populate_html_content can take a generic context_data dict
                # OR, we reconstruct the specific expected dict for it.
                # Let's try to make it work with a generic context_data for now.
                # A simple string replacement is safer if HtmlEditor is too specific.
                # For a robust solution, HtmlEditor.populate_html_content might need to be refactored
                # or a new utility for generic context dict population created.

                # Simple placeholder replacement for HTML (basic example)
                # More complex logic might be needed from HtmlEditor if it does more (e.g. loops, conditions)
                populated_body = template_content
                for key, value in context_data.items(): # context_data might have nested dicts
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                             placeholder = f"{{{{{key}.{sub_key}}}}}"
                             populated_body = populated_body.replace(placeholder, str(sub_value) if sub_value is not None else "")
                    else:
                        placeholder = f"{{{{{key}}}}}"
                        populated_body = populated_body.replace(placeholder, str(value) if value is not None else "")
                self.body_edit.setHtml(populated_body)

            elif template_type == 'EMAIL_BODY_TXT':
                populated_body = template_content
                for key, value in context_data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                             placeholder = f"{{{{{key}.{sub_key}}}}}"
                             populated_body = populated_body.replace(placeholder, str(sub_value) if sub_value is not None else "")
                    else:
                        placeholder = f"{{{{{key}}}}}"
                        populated_body = populated_body.replace(placeholder, str(value) if value is not None else "")
                self.body_edit.setPlainText(populated_body)
            else:
                self.body_edit.setPlainText(self.tr("Type de modèle non supporté pour l'aperçu."))

            self.body_edit.setReadOnly(True) # Make read-only when template is active

            # Populate Subject
            if email_subject_template:
                populated_subject = email_subject_template
                for key, value in context_data.items():
                     if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                             placeholder = f"{{{{{key}.{sub_key}}}}}"
                             populated_subject = populated_subject.replace(placeholder, str(sub_value) if sub_value is not None else "")
                     else:
                        placeholder = f"{{{{{key}}}}}"
                        populated_subject = populated_subject.replace(placeholder, str(value) if value is not None else "")
                self.subject_edit.setText(populated_subject)
            else:
                # If template has no subject, clear it or leave as is? Let's clear.
                self.subject_edit.setText("")
            # self.subject_edit.setReadOnly(True) # Optionally make subject read-only

        except Exception as e:
            print(f"Error applying email template (ID: {template_id}): {e}")
            QMessageBox.critical(self, self.tr("Erreur Application Modèle"),
                                 self.tr("Une erreur est survenue lors de l'application du modèle:\n{0}").format(str(e)))
            self.body_edit.setPlainText("")
            self.body_edit.setReadOnly(False)
            self.active_template_type = None # Reset on error


        attachment_buttons_layout = QHBoxLayout() # Renamed for clarity
        self.add_attachment_btn = QPushButton(self.tr("Ajouter Pièce Jointe (Fichier)"))
        self.add_attachment_btn.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/plus.svg")))
        self.add_attachment_btn.clicked.connect(self.add_attachment_from_file_system) # Renamed method
        attachment_buttons_layout.addWidget(self.add_attachment_btn)

        if self.client_info: # Only add "Add Client Document" button if client_info is available
            self.add_client_document_btn = QPushButton(self.tr("Ajouter Document Client"))
            self.add_client_document_btn.setIcon(QIcon.fromTheme("folder-open", QIcon(":/icons/folder.svg")))
            self.add_client_document_btn.clicked.connect(self.add_attachment_from_client_docs)
            attachment_buttons_layout.addWidget(self.add_client_document_btn)

        # Add Utility Document button
        self.add_utility_document_btn = QPushButton(self.tr("Ajouter Document Utilitaire"))
        self.add_utility_document_btn.setIcon(QIcon.fromTheme("document-properties", QIcon(":/icons/document.svg"))) # Example icon
        self.add_utility_document_btn.clicked.connect(self.add_attachment_from_utility_docs)
        attachment_buttons_layout.addWidget(self.add_utility_document_btn)

        self.remove_attachment_btn = QPushButton(self.tr("Supprimer Pièce Jointe"))
        self.remove_attachment_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg")))
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_buttons_layout.addWidget(self.remove_attachment_btn)
        layout.addLayout(attachment_buttons_layout) # Add the layout for attachment buttons

        self.attachments_list_widget = QListWidget()
        self.attachments_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel(self.tr("Pièces jointes:")))
        layout.addWidget(self.attachments_list_widget)

        button_box = QDialogButtonBox()
        send_button = button_box.addButton(self.tr("Envoyer"), QDialogButtonBox.AcceptRole)
        send_button.setIcon(QIcon.fromTheme("mail-send", QIcon(":/icons/bell.svg")))
        send_button.setObjectName("primaryButton")

        button_box.addButton(QDialogButtonBox.Cancel)

        button_box.accepted.connect(self.send_email_action)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def open_select_contacts_dialog(self):
        if not self.client_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("ID Client non disponible."))
            return

        dialog = SelectContactsDialog(self.client_id, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_emails = dialog.get_selected_emails()
            if selected_emails:
                current_text = self.to_edit.text().strip()
                current_emails = [email.strip() for email in current_text.split(',') if email.strip()]

                new_emails_to_add = []
                for email in selected_emails:
                    if email not in current_emails:
                        new_emails_to_add.append(email)

                if new_emails_to_add:
                    if current_text and not current_text.endswith(','):
                        prefix = ", " if current_emails else ""
                    elif not current_text:
                         prefix = ""
                    else:
                        prefix = " " if current_text else ""


                    self.to_edit.setText(current_text + prefix + ", ".join(new_emails_to_add))

    def add_attachment_from_client_docs(self):
        if not self.client_info:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Informations client non disponibles pour sélectionner des documents."))
            return

        dialog = SelectClientAttachmentDialog(self.client_info, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_files = dialog.get_selected_files()
            if selected_files:
                for file_path in selected_files:
                    if file_path not in self.attachments:
                        self.attachments.append(file_path)
                        self.attachments_list_widget.addItem(os.path.basename(file_path))
                    else:
                        QMessageBox.information(self, self.tr("Info"), self.tr("Le fichier '{0}' est déjà attaché.").format(os.path.basename(file_path)))

    def add_attachment_from_utility_docs(self):
        dialog = SelectUtilityAttachmentDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_files = dialog.get_selected_files()
            if selected_files:
                for file_path in selected_files:
                    if file_path not in self.attachments:
                        self.attachments.append(file_path)
                        self.attachments_list_widget.addItem(os.path.basename(file_path))
                    else:
                        QMessageBox.information(self, self.tr("Info"), self.tr("Le fichier '{0}' est déjà attaché.").format(os.path.basename(file_path)))

    def add_attachment_from_file_system(self): # Renamed from add_attachment
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des fichiers à joindre"), "", self.tr("Tous les fichiers (*.*)"))
        if files:
            for file_path in files:
                if file_path not in self.attachments:
                    self.attachments.append(file_path)
                    self.attachments_list_widget.addItem(os.path.basename(file_path))

    def remove_attachment(self):
        selected_items = self.attachments_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.attachments_list_widget.row(item)
            self.attachments_list_widget.takeItem(row)
            # Remove from self.attachments by matching basename, less robust if multiple files with same name from different paths
            # A more robust way would be to store full paths in item data or find by index if list order is guaranteed.
            # For simplicity, let's find by index.
            if 0 <= row < len(self.attachments):
                del self.attachments[row]
            else: # Fallback if index is out of sync (should not happen with SingleSelection)
                try:
                    # Attempt to remove by matching basename from the list
                    file_to_remove = item.text()
                    self.attachments = [att for att in self.attachments if os.path.basename(att) != file_to_remove]
                except ValueError:
                    pass # Item not found, already removed or error

    def send_email_action(self):
        to_email = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()

        body_content = ""
        mime_subtype = 'plain' # Default to plain text

        if self.active_template_type == 'EMAIL_BODY_HTML':
            body_content = self.body_edit.toHtml()
            mime_subtype = 'html'
        else: # Covers 'EMAIL_BODY_TXT', None (manual), or any other case
            body_content = self.body_edit.toPlainText().strip()
            # mime_subtype remains 'plain'

        if not to_email:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("L'adresse email du destinataire est requise."))
            return
        if not subject:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le sujet de l'email est requis."))
            return

        # Use self.config for SMTP settings
        smtp_server = self.config.get("smtp_server")
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config.get("smtp_user")
        smtp_password = self.config.get("smtp_password")

        if not smtp_server or not smtp_user: # Password can be empty for some configs
            QMessageBox.warning(self, self.tr("Configuration SMTP Manquante"),
                                self.tr("Veuillez configurer les détails du serveur SMTP dans les paramètres de l'application."))
            return

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_content, mime_subtype)) # Use determined content and subtype

        for attachment_path in self.attachments:
            try:
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Pièce Jointe"), self.tr("Impossible de joindre le fichier {0}:\
{1}").format(os.path.basename(attachment_path), str(e)))
                return # Stop if an attachment fails

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_port == 587: # Standard port for TLS
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            QMessageBox.information(self, self.tr("Email Envoyé"), self.tr("L'email a été envoyé avec succès."))
            self.accept() # Close dialog on success
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'Envoi Email"), self.tr("Une erreur est survenue lors de l'envoi de l'email:\
{0}").format(str(e)))


class ProductEquivalencyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gérer les Équivalences de Produits"))
        self.setMinimumSize(900, 700)

        self.current_selected_product_a_id = None
        self.current_selected_product_a_info = {} # To store name, lang
        self.current_selected_product_b_id = None
        self.current_selected_product_b_info = {} # To store name, lang

        self.setup_ui()
        self.load_equivalencies()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Display Existing Equivalencies ---
        display_group = QGroupBox(self.tr("Équivalences Existantes"))
        display_layout = QVBoxLayout(display_group)

        self.equivalencies_table = QTableWidget()
        self.equivalencies_table.setColumnCount(7) # Equivalence ID (hidden), P_A ID (hidden), Name A, Lang A, P_B ID (hidden), Name B, Lang B
        self.equivalencies_table.setHorizontalHeaderLabels([
            "Equiv. ID", "ID Prod. A", self.tr("Produit A"), self.tr("Langue A"),
            "ID Prod. B", self.tr("Produit B"), self.tr("Langue B")
        ])
        self.equivalencies_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.equivalencies_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.equivalencies_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.equivalencies_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.equivalencies_table.hideColumn(0) # Hide Equivalence ID
        self.equivalencies_table.hideColumn(1) # Hide Product A ID
        self.equivalencies_table.hideColumn(4) # Hide Product B ID
        self.equivalencies_table.itemSelectionChanged.connect(self._update_button_states)
        display_layout.addWidget(self.equivalencies_table)

        refresh_remove_layout = QHBoxLayout()
        self.refresh_button = QPushButton(self.tr("Actualiser la Liste"))
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.clicked.connect(self.load_equivalencies)
        refresh_remove_layout.addWidget(self.refresh_button)

        self.remove_button = QPushButton(self.tr("Supprimer l'Équivalence Sélectionnée"))
        self.remove_button.setIcon(QIcon.fromTheme("list-remove"))
        self.remove_button.setObjectName("dangerButton")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_selected_equivalency)
        refresh_remove_layout.addWidget(self.remove_button)
        display_layout.addLayout(refresh_remove_layout)
        main_layout.addWidget(display_group)

        # --- Add New Equivalency ---
        add_group = QGroupBox(self.tr("Ajouter Nouvelle Équivalence"))
        add_layout = QGridLayout(add_group)

        # Product A Selection
        add_layout.addWidget(QLabel(self.tr("Produit A:")), 0, 0)
        self.search_product_a_input = QLineEdit()
        self.search_product_a_input.setPlaceholderText(self.tr("Rechercher Produit A..."))
        self.search_product_a_input.textChanged.connect(self.search_product_a)
        add_layout.addWidget(self.search_product_a_input, 1, 0)
        self.results_product_a_list = QListWidget()
        self.results_product_a_list.itemClicked.connect(self.select_product_a)
        add_layout.addWidget(self.results_product_a_list, 2, 0)
        self.selected_product_a_label = QLabel(self.tr("Aucun produit A sélectionné"))
        add_layout.addWidget(self.selected_product_a_label, 3, 0)

        # Product B Selection
        add_layout.addWidget(QLabel(self.tr("Produit B:")), 0, 1)
        self.search_product_b_input = QLineEdit()
        self.search_product_b_input.setPlaceholderText(self.tr("Rechercher Produit B..."))
        self.search_product_b_input.textChanged.connect(self.search_product_b)
        add_layout.addWidget(self.search_product_b_input, 1, 1)
        self.results_product_b_list = QListWidget()
        self.results_product_b_list.itemClicked.connect(self.select_product_b)
        add_layout.addWidget(self.results_product_b_list, 2, 1)
        self.selected_product_b_label = QLabel(self.tr("Aucun produit B sélectionné"))
        add_layout.addWidget(self.selected_product_b_label, 3, 1)

        self.add_equivalency_button = QPushButton(self.tr("Ajouter Équivalence"))
        self.add_equivalency_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_equivalency_button.setObjectName("primaryButton")
        self.add_equivalency_button.setEnabled(False)
        self.add_equivalency_button.clicked.connect(self.add_new_equivalency)
        add_layout.addWidget(self.add_equivalency_button, 4, 0, 1, 2) # Span across 2 columns
        main_layout.addWidget(add_group)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.button(QDialogButtonBox.Close).setText(self.tr("Fermer"))
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _update_button_states(self):
        self.remove_button.setEnabled(bool(self.equivalencies_table.selectedItems()))
        self.add_equivalency_button.setEnabled(
            self.current_selected_product_a_id is not None and \
            self.current_selected_product_b_id is not None
        )

    def load_equivalencies(self):
        self.equivalencies_table.setRowCount(0)
        try:
            equivalencies = db_manager.get_all_product_equivalencies()
            if equivalencies is None: equivalencies = []

            for eq_data in equivalencies:
                row_pos = self.equivalencies_table.rowCount()
                self.equivalencies_table.insertRow(row_pos)

                # Store IDs in the first visible item (Product A Name) for simplicity, or use column 0 if shown
                name_a_item = QTableWidgetItem(eq_data.get('product_name_a', 'N/A'))
                name_a_item.setData(Qt.UserRole, eq_data.get('equivalence_id'))
                name_a_item.setData(Qt.UserRole + 1, eq_data.get('product_id_a'))
                name_a_item.setData(Qt.UserRole + 2, eq_data.get('product_id_b'))

                self.equivalencies_table.setItem(row_pos, 0, QTableWidgetItem(str(eq_data.get('equivalence_id','')))) # Hidden
                self.equivalencies_table.setItem(row_pos, 1, QTableWidgetItem(str(eq_data.get('product_id_a','')))) # Hidden
                self.equivalencies_table.setItem(row_pos, 2, name_a_item)
                self.equivalencies_table.setItem(row_pos, 3, QTableWidgetItem(eq_data.get('language_code_a', 'N/A')))
                self.equivalencies_table.setItem(row_pos, 4, QTableWidgetItem(str(eq_data.get('product_id_b','')))) # Hidden
                self.equivalencies_table.setItem(row_pos, 5, QTableWidgetItem(eq_data.get('product_name_b', 'N/A')))
                self.equivalencies_table.setItem(row_pos, 6, QTableWidgetItem(eq_data.get('language_code_b', 'N/A')))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les équivalences: {0}").format(str(e)))
        self._update_button_states()

    def remove_selected_equivalency(self):
        selected_items = self.equivalencies_table.selectedItems()
        if not selected_items:
            return

        equivalence_id = selected_items[0].data(Qt.UserRole) # Assuming stored in the first selected item of the row

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer cette équivalence (ID: {0})?").format(equivalence_id),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if db_manager.remove_product_equivalence(equivalence_id):
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Équivalence supprimée avec succès."))
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la suppression de l'équivalence."))
            except Exception as e:
                 QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la suppression: {0}").format(str(e)))
            finally:
                self.load_equivalencies()

    def _search_products(self, search_text, list_widget):
        list_widget.clear()
        if not search_text or len(search_text) < 2: # Avoid searching for too short strings
            return

        try:
            # Using get_all_products_for_selection_filtered for a broader search
            products = db_manager.get_all_products_for_selection_filtered(name_pattern=f"%{search_text}%")
            if products is None: products = []
            for prod in products:
                item_text = f"{prod.get('product_name')} ({prod.get('language_code')}) - ID: {prod.get('product_id')}"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, prod) # Store full product dict
                list_widget.addItem(list_item)
        except Exception as e:
            print(f"Error searching products: {e}") # Log to console for now

    def search_product_a(self):
        self._search_products(self.search_product_a_input.text(), self.results_product_a_list)

    def search_product_b(self):
        self._search_products(self.search_product_b_input.text(), self.results_product_b_list)

    def _select_product(self, item, label_widget, target_id_attr, target_info_attr):
        if not item:
            return
        product_data = item.data(Qt.UserRole)
        if product_data:
            setattr(self, target_id_attr, product_data.get('product_id'))
            info_dict = {'name': product_data.get('product_name'), 'lang': product_data.get('language_code')}
            setattr(self, target_info_attr, info_dict)
            label_widget.setText(self.tr("Sélectionné: {0} ({1})").format(info_dict['name'], info_dict['lang']))
        self._update_button_states()

    def select_product_a(self, item):
        self._select_product(item, self.selected_product_a_label,
                             'current_selected_product_a_id', 'current_selected_product_a_info')

    def select_product_b(self, item):
        self._select_product(item, self.selected_product_b_label,
                             'current_selected_product_b_id', 'current_selected_product_b_info')

    def add_new_equivalency(self):
        if self.current_selected_product_a_id is None or self.current_selected_product_b_id is None:
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner les deux produits pour créer une équivalence."))
            return

        if self.current_selected_product_a_id == self.current_selected_product_b_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Un produit ne peut pas être équivalent à lui-même."))
            return

        try:
            new_eq_id = db_manager.add_product_equivalence(self.current_selected_product_a_id, self.current_selected_product_b_id)
            if new_eq_id:
                QMessageBox.information(self, self.tr("Succès"),
                                        self.tr("Équivalence ajoutée avec succès (ID: {0}).").format(new_eq_id))
                self.load_equivalencies()
                # Clear selections
                self.current_selected_product_a_id = None
                self.current_selected_product_a_info = {}
                self.selected_product_a_label.setText(self.tr("Aucun produit A sélectionné"))
                self.search_product_a_input.clear()
                self.results_product_a_list.clear()

                self.current_selected_product_b_id = None
                self.current_selected_product_b_info = {}
                self.selected_product_b_label.setText(self.tr("Aucun produit B sélectionné"))
                self.search_product_b_input.clear()
                self.results_product_b_list.clear()
            else:
                # add_product_equivalence might return None if pair already exists (due to IntegrityError handling)
                # or due to other DB errors.
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter l'équivalence. Elle existe peut-être déjà ou une erreur s'est produite."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de l'équivalence: {0}").format(str(e)))
        finally:
            self._update_button_states()
class SelectContactsDialog(QDialog):
    def __init__(self, client_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.selected_emails = []

        self.setWindowTitle(self.tr("Sélectionner des Contacts"))
        self.setMinimumSize(400, 300)
        self.setup_ui()
        self.load_contacts()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.contacts_list_widget = QListWidget()
        self.contacts_list_widget.setSelectionMode(QAbstractItemView.NoSelection) # Manage selection via checkboxes
        layout.addWidget(QLabel(self.tr("Contacts disponibles :")))
        layout.addWidget(self.contacts_list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_contacts(self):
        contacts = db_manager.get_contacts_for_client(self.client_id)
        if contacts:
            for contact in contacts:
                name = contact.get("name", self.tr("N/A"))
                email = contact.get("email", self.tr("N/A"))
                if email == self.tr("N/A") or not email.strip(): # Skip contacts without a valid email
                    continue
                item_text = f"{name} <{email}>"
                list_item = QListWidgetItem(item_text)
                list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
                list_item.setCheckState(Qt.Unchecked)
                list_item.setData(Qt.UserRole, email) # Store email in UserRole
                self.contacts_list_widget.addItem(list_item)

    def accept_selection(self):
        self.selected_emails = []
        for i in range(self.contacts_list_widget.count()):
            item = self.contacts_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                email = item.data(Qt.UserRole)
                if email:
                    self.selected_emails.append(email)
        self.accept()

    def get_selected_emails(self):
        return self.selected_emails

class SelectClientAttachmentDialog(QDialog):
    def __init__(self, client_info, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.selected_files = []

        self.setWindowTitle(self.tr("Sélectionner Pièces Jointes du Client"))
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.load_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(self.tr("Filtrer par extension:")))
        self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([
            self.tr("Tous (*.*)"),
            self.tr("PDF (*.pdf)"),
            self.tr("DOCX (*.docx)"),
            self.tr("XLSX (*.xlsx)"),
            self.tr("Images (*.png *.jpg *.jpeg)"),
            self.tr("Autres")
        ])
        self.extension_filter_combo.currentTextChanged.connect(self.filter_documents)
        filter_layout.addWidget(self.extension_filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Tree widget for documents
        self.doc_tree_widget = QTreeWidget()
        self.doc_tree_widget.setColumnCount(3) # Name, Type, Path (hidden)
        self.doc_tree_widget.setHeaderLabels([self.tr("Nom du Fichier"), self.tr("Type"), self.tr("Date Modification")])
        self.doc_tree_widget.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.doc_tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.doc_tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.doc_tree_widget.setSortingEnabled(True) # Enable sorting
        self.doc_tree_widget.sortByColumn(0, Qt.AscendingOrder) # Default sort by name

        layout.addWidget(self.doc_tree_widget)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_documents(self):
        self.doc_tree_widget.clear()
        if not self.client_info or 'base_folder_path' not in self.client_info or 'selected_languages' not in self.client_info:
            return

        base_folder_path = self.client_info['base_folder_path']
        selected_languages = self.client_info['selected_languages']
        if isinstance(selected_languages, str): # Ensure it's a list
             selected_languages = [lang.strip() for lang in selected_languages.split(',') if lang.strip()]


        for lang_code in selected_languages:
            lang_folder_path = os.path.join(base_folder_path, lang_code)
            if os.path.isdir(lang_folder_path):
                lang_item = QTreeWidgetItem(self.doc_tree_widget, [f"{self.tr('Langue')}: {lang_code.upper()}"])
                lang_item.setData(0, Qt.UserRole, {"is_lang_folder": True}) # Mark as language folder
                # lang_item.setExpanded(True) # Optionally expand language folders by default

                for doc_name in os.listdir(lang_folder_path):
                    doc_path = os.path.join(lang_folder_path, doc_name)
                    if os.path.isfile(doc_path):
                        _, ext = os.path.splitext(doc_name)
                        ext = ext.lower()

                        mod_timestamp = os.path.getmtime(doc_path)
                        mod_date = datetime.fromtimestamp(mod_timestamp).strftime('%Y-%m-%d %H:%M')

                        doc_item = QTreeWidgetItem(lang_item, [doc_name, ext.replace(".","").upper(), mod_date])
                        doc_item.setFlags(doc_item.flags() | Qt.ItemIsUserCheckable)
                        doc_item.setCheckState(0, Qt.Unchecked)
                        doc_item.setData(0, Qt.UserRole, {"path": doc_path, "ext": ext, "is_lang_folder": False})

                        # Prioritize PDFs in sorting by adding a sort key (e.g., prefix)
                        # Or handle this in filter_documents if sorting is applied after filtering
                        if ext == ".pdf":
                            doc_item.setData(0, Qt.UserRole + 1, 0) # Lower number for higher priority
                        else:
                            doc_item.setData(0, Qt.UserRole + 1, 1)

        self.doc_tree_widget.sortItems(0, self.doc_tree_widget.header().sortIndicatorOrder()) # Apply initial sort
        self.filter_documents() # Apply initial filter

    def filter_documents(self):
        selected_filter_text = self.extension_filter_combo.currentText()

        for i in range(self.doc_tree_widget.topLevelItemCount()):
            lang_item = self.doc_tree_widget.topLevelItem(i)
            if not lang_item: continue

            has_visible_child = False
            for j in range(lang_item.childCount()):
                doc_item = lang_item.child(j)
                if not doc_item: continue

                item_data = doc_item.data(0, Qt.UserRole)
                if not item_data or item_data.get("is_lang_folder"): continue # Should not happen for doc_item

                doc_ext = item_data.get("ext", "")
                visible = False

                if self.tr("Tous (*.*)") in selected_filter_text:
                    visible = True
                elif self.tr("PDF (*.pdf)") in selected_filter_text and doc_ext == ".pdf":
                    visible = True
                elif self.tr("DOCX (*.docx)") in selected_filter_text and doc_ext == ".docx":
                    visible = True
                elif self.tr("XLSX (*.xlsx)") in selected_filter_text and doc_ext == ".xlsx":
                    visible = True
                elif self.tr("Images (*.png *.jpg *.jpeg)") in selected_filter_text and doc_ext in [".png", ".jpg", ".jpeg"]:
                    visible = True
                elif self.tr("Autres") in selected_filter_text and doc_ext not in [".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"]:
                    visible = True

                doc_item.setHidden(not visible)
                if visible:
                    has_visible_child = True
            lang_item.setHidden(not has_visible_child) # Hide lang folder if no children are visible

        # Re-apply sorting after filtering might change visibility
        # self.doc_tree_widget.sortItems(self.doc_tree_widget.sortColumn(), self.doc_tree_widget.header().sortIndicatorOrder())


    def accept_selection(self):
        self.selected_files = []
        for i in range(self.doc_tree_widget.topLevelItemCount()):
            lang_item = self.doc_tree_widget.topLevelItem(i)
            if not lang_item or lang_item.isHidden(): continue
            for j in range(lang_item.childCount()):
                doc_item = lang_item.child(j)
                if not doc_item or doc_item.isHidden(): continue

                if doc_item.checkState(0) == Qt.Checked:
                    item_data = doc_item.data(0, Qt.UserRole)
                    if item_data and not item_data.get("is_lang_folder"):
                        self.selected_files.append(item_data["path"])
        self.accept()

    def get_selected_files(self):
        return self.selected_files

class ManageProductMasterDialog(QDialog):
    def __init__(self, app_root_dir, parent=None): # Added app_root_dir
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gérer Produits Globaux"))
        self.setMinimumSize(1000, 700)
        self.app_root_dir = app_root_dir # Store app_root_dir
        # self.setup_ui() # setup_ui is called later
        self.selected_product_id = None
        self.load_products_triggered_by_text_change = False

        self.setup_ui() # setup_ui call moved after initializing all necessary attributes
        self.load_products()
        self._clear_form_and_disable_buttons()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Top layout for search and table
        top_layout = QHBoxLayout()

        # Left side: Product List and Search
        product_list_group = QGroupBox(self.tr("Liste des Produits"))
        product_list_layout = QVBoxLayout(product_list_group)

        self.search_product_input = QLineEdit()
        self.search_product_input.setPlaceholderText(self.tr("Rechercher par nom, catégorie..."))
        self.search_product_input.textChanged.connect(self._trigger_load_products_from_search)
        product_list_layout.addWidget(self.search_product_input)

        self.products_table = QTableWidget()
        # ID (hidden), Name, Category, Language, Base Price
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels([
            "ID", self.tr("Nom Produit"), self.tr("Catégorie"),
            self.tr("Langue"), self.tr("Prix de Base Unitaire")
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name column
        self.products_table.hideColumn(0) # Hide ID column
        self.products_table.itemSelectionChanged.connect(self.on_product_selection_changed)
        product_list_layout.addWidget(self.products_table)

        top_layout.addWidget(product_list_group, 2)

        # Right side: Product Form
        self.product_form_group = QGroupBox(self.tr("Détails du Produit"))
        self.product_form_group.setDisabled(True) # Disabled until "Add New" or selection
        form_layout = QFormLayout(self.product_form_group)

        self.name_input = QLineEdit()
        form_layout.addRow(self.tr("Nom:"), self.name_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.description_input)

        self.category_input = QLineEdit() # Could be QComboBox if categories are predefined
        form_layout.addRow(self.tr("Catégorie:"), self.category_input)

        self.language_code_combo = QComboBox()
        self.language_code_combo.addItems(["fr", "en", "ar", "tr", "pt"])
        form_layout.addRow(self.tr("Code Langue:"), self.language_code_combo)

        self.base_unit_price_input = QDoubleSpinBox()
        self.base_unit_price_input.setRange(0.0, 1_000_000_000.0)
        self.base_unit_price_input.setDecimals(2)
        self.base_unit_price_input.setPrefix("€ ") # Or use locale-specific currency
        form_layout.addRow(self.tr("Prix de Base Unitaire:"), self.base_unit_price_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setSuffix(" kg")
        self.weight_input.setRange(0.0, 10000.0)
        self.weight_input.setDecimals(3)
        form_layout.addRow(self.tr("Poids:"), self.weight_input)

        self.general_dimensions_input = QLineEdit()
        self.general_dimensions_input.setPlaceholderText(self.tr("ex: 100x50x25 cm"))
        form_layout.addRow(self.tr("Dimensions Générales (Produit):"), self.general_dimensions_input)

        top_layout.addWidget(self.product_form_group, 1) # Form takes 1/3 of width
        main_layout.addLayout(top_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.add_new_product_button = QPushButton(self.tr("Ajouter Nouveau Produit"))
        self.add_new_product_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_new_product_button.clicked.connect(self.on_add_new_product)
        buttons_layout.addWidget(self.add_new_product_button)

        self.save_product_button = QPushButton(self.tr("Enregistrer Modifications"))
        self.save_product_button.setIcon(QIcon.fromTheme("document-save"))
        self.save_product_button.setObjectName("primaryButton")
        # self.save_product_button.setDisabled(True) # Initial state handled by _clear_form_and_disable_buttons
        self.save_product_button.clicked.connect(self.on_save_product)
        buttons_layout.addWidget(self.save_product_button)

        self.manage_detailed_dimensions_button = QPushButton(self.tr("Gérer Dimensions Détaillées"))
        self.manage_detailed_dimensions_button.setIcon(QIcon.fromTheme("view-grid")) # Example icon
        # self.manage_detailed_dimensions_button.setDisabled(True) # Initial state
        self.manage_detailed_dimensions_button.clicked.connect(self.on_manage_detailed_dimensions)
        buttons_layout.addWidget(self.manage_detailed_dimensions_button)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # Dialog Button Box
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        dialog_button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        main_layout.addWidget(dialog_button_box)

        self.setLayout(main_layout)

    def _trigger_load_products_from_search(self):
        # This method helps manage how text changes trigger loading,
        # e.g., could add a small delay here if needed (QTimer.singleShot)
        # For now, direct call.
        self.load_products_triggered_by_text_change = True
        self.load_products()
        self.load_products_triggered_by_text_change = False


    def _clear_form_and_disable_buttons(self):
        self.name_input.clear()
        self.description_input.clear()
        self.category_input.clear()
        self.language_code_combo.setCurrentIndex(0) # Default to 'fr' or first item
        self.base_unit_price_input.setValue(0.0)
        self.weight_input.setValue(0.0)
        self.general_dimensions_input.clear()

        self.selected_product_id = None
        self.product_form_group.setDisabled(True)
        self.save_product_button.setDisabled(True)
        self.save_product_button.setText(self.tr("Enregistrer Modifications"))
        self.manage_detailed_dimensions_button.setDisabled(True)
        # self.products_table.clearSelection() # This might trigger selectionChanged again if not careful

    def load_products(self):
        current_selection_product_id = self.selected_product_id
        if self.load_products_triggered_by_text_change: # If search triggered load, don't keep old selection
            current_selection_product_id = None

        self.products_table.setSortingEnabled(False) # Disable sorting during population
        self.products_table.clearContents()
        self.products_table.setRowCount(0)

        search_text = self.search_product_input.text().strip()
        filters = None
        if search_text:
            filters = {'product_name': f'%{search_text}%'} # Search by name containing text

        try:
            products = db_manager.get_all_products(filters=filters)
            products = products if products else []

            for row_idx, product_data in enumerate(products):
                self.products_table.insertRow(row_idx)

                id_item = QTableWidgetItem(str(product_data['product_id']))
                id_item.setData(Qt.UserRole, product_data['product_id'])
                self.products_table.setItem(row_idx, 0, id_item) # Hidden ID

                self.products_table.setItem(row_idx, 1, QTableWidgetItem(product_data.get('product_name', '')))
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(product_data.get('category', '')))
                self.products_table.setItem(row_idx, 3, QTableWidgetItem(product_data.get('language_code', '')))

                price_str = f"{product_data.get('base_unit_price', 0.0):.2f}"
                price_item = QTableWidgetItem(price_str)
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 4, price_item)

                if product_data['product_id'] == current_selection_product_id:
                    self.products_table.selectRow(row_idx)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger les produits: {0}").format(str(e)))

        self.products_table.setSortingEnabled(True) # Re-enable sorting
        if not self.products_table.selectedItems(): # If no row is selected (e.g. after search)
            self._clear_form_and_disable_buttons()


    def on_product_selection_changed(self):
        selected_items = self.products_table.selectedItems()
        if not selected_items:
            self._clear_form_and_disable_buttons()
            return

        selected_row = selected_items[0].row()
        product_id_item = self.products_table.item(selected_row, 0) # ID is in hidden column 0
        if not product_id_item:
            self._clear_form_and_disable_buttons()
            return

        self.selected_product_id = product_id_item.data(Qt.UserRole)

        try:
            product_data = db_manager.get_product_by_id(self.selected_product_id)
            if product_data:
                self.product_form_group.setDisabled(False)
                self.name_input.setText(product_data.get('product_name', ''))
                self.description_input.setPlainText(product_data.get('description', ''))
                self.category_input.setText(product_data.get('category', ''))

                lang_idx = self.language_code_combo.findText(product_data.get('language_code', 'fr'))
                self.language_code_combo.setCurrentIndex(lang_idx if lang_idx != -1 else 0)

                base_price_from_db = product_data.get('base_unit_price')
                self.base_unit_price_input.setValue(float(base_price_from_db) if base_price_from_db is not None else 0.0)

                weight_from_db = product_data.get('weight')
                self.weight_input.setValue(float(weight_from_db) if weight_from_db is not None else 0.0)
                self.general_dimensions_input.setText(product_data.get('dimensions', ''))

                self.save_product_button.setText(self.tr("Enregistrer Modifications"))
                self.save_product_button.setEnabled(True)
                self.manage_detailed_dimensions_button.setEnabled(True)
            else:
                self._clear_form_and_disable_buttons()
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Produit non trouvé."))
        except Exception as e:
            self._clear_form_and_disable_buttons()
            QMessageBox.critical(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger les détails du produit: {0}").format(str(e)))


    def on_add_new_product(self):
        self._clear_form_and_disable_buttons() # Clear form and reset selection state
        self.products_table.clearSelection()    # Explicitly clear table selection

        self.product_form_group.setDisabled(False)
        self.save_product_button.setText(self.tr("Ajouter Produit"))
        self.save_product_button.setEnabled(True)
        self.manage_detailed_dimensions_button.setEnabled(False) # Can't manage dimensions for unsaved product
        self.name_input.setFocus()


    def on_save_product(self):
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        category = self.category_input.text().strip()
        language_code = self.language_code_combo.currentText()
        base_unit_price = self.base_unit_price_input.value()
        weight = self.weight_input.value()
        dimensions = self.general_dimensions_input.text().strip()

        if not name:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du produit est requis."))
            self.name_input.setFocus()
            return
        if not language_code: # Should not happen with QComboBox unless it's cleared
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le code langue est requis."))
            self.language_code_combo.setFocus()
            return
        # base_unit_price can be 0, so no strict check for > 0 unless business rule

        product_data_dict = {
            'product_name': name,
            'description': description,
            'category': category,
            'language_code': language_code,
            'base_unit_price': base_unit_price,
            'weight': weight,
            'dimensions': dimensions,
            'is_active': True # Default for new/updated products
        }

        try:
            if self.selected_product_id is None: # Add mode
                new_id = db_manager.add_product(product_data_dict)
                if new_id:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Produit ajouté avec succès (ID: {0}).").format(new_id))
                    self.load_products() # Refresh list
                    # Try to select the newly added product
                    for r in range(self.products_table.rowCount()):
                        if self.products_table.item(r, 0).data(Qt.UserRole) == new_id:
                            self.products_table.selectRow(r)
                            break
                    if not self.products_table.selectedItems(): # Fallback if not found or selection failed
                         self._clear_form_and_disable_buttons()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter le produit. Vérifiez les logs (doublon nom/langue?)."))
            else: # Edit mode
                success = db_manager.update_product(self.selected_product_id, product_data_dict)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Produit mis à jour avec succès."))
                    current_selected_row = self.products_table.currentRow()
                    self.load_products() # Refresh list
                    if current_selected_row >= 0 and current_selected_row < self.products_table.rowCount():
                         self.products_table.selectRow(current_selected_row) # Try to re-select
                    if not self.products_table.selectedItems():
                        self._clear_form_and_disable_buttons()

                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour le produit."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Base de Données"), self.tr("Une erreur est survenue: {0}").format(str(e)))


    def on_manage_detailed_dimensions(self):
        if self.selected_product_id is not None:
            dialog = ProductDimensionUIDialog(self.selected_product_id, self.app_root_dir, self, read_only=False)
            dialog.exec_()
            # Optionally, refresh product details if dimensions might affect display (e.g. a summary)
            # self.load_products()
            # self.on_product_selection_changed() # to reload form if needed
        else:
            QMessageBox.warning(self, self.tr("Aucun Produit Sélectionné"), self.tr("Veuillez sélectionner un produit pour gérer ses dimensions détaillées."))


class ClientDocumentNoteDialog(QDialog):
    def __init__(self, client_id, note_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.note_data = note_data # This will be None for "add" mode, or a dict for "edit" mode

        if self.note_data:
            self.setWindowTitle(self.tr("Modifier Note de Document"))
        else:
            self.setWindowTitle(self.tr("Ajouter Note de Document"))

        self.setMinimumWidth(450)
        self.setup_ui()

        if self.note_data:
            self.populate_form(self.note_data)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.document_type_combo = QComboBox()
        # Common types, can be expanded or made dynamic later
        self.document_type_combo.addItems([
            "Proforma", "Packing List", "Sales Conditions",
            "Certificate of Origin", "Bill of Lading", "Other"
        ])
        form_layout.addRow(self.tr("Type de Document:"), self.document_type_combo)

        self.language_code_combo = QComboBox()
        self.language_code_combo.addItems(["fr", "en", "ar", "tr", "pt"]) # Common languages
        form_layout.addRow(self.tr("Code Langue:"), self.language_code_combo)

        self.note_content_edit = QTextEdit()

        self.note_content_edit.setPlaceholderText(self.tr("Saisissez le contenu de la note ici. Chaque ligne sera affichée comme un élément d'une liste numérotée."))
        self.note_content_edit.setMinimumHeight(100)
        form_layout.addRow(self.tr("Contenu de la Note:"), self.note_content_edit)

        self.is_active_checkbox = QCheckBox(self.tr("Active"))
        self.is_active_checkbox.setChecked(True) # Default to active
        form_layout.addRow(self.is_active_checkbox)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def populate_form(self, note_data):
        self.document_type_combo.setCurrentText(note_data.get("document_type", ""))
        self.language_code_combo.setCurrentText(note_data.get("language_code", "fr"))
        self.note_content_edit.setPlainText(note_data.get("note_content", ""))
        self.is_active_checkbox.setChecked(note_data.get("is_active", True))

    def get_data(self) -> dict:
        data = {
            "client_id": self.client_id,
            "document_type": self.document_type_combo.currentText(),
            "language_code": self.language_code_combo.currentText(),
            "note_content": self.note_content_edit.toPlainText().strip(),
            "is_active": self.is_active_checkbox.isChecked()
        }
        if self.note_data and 'note_id' in self.note_data: # Include note_id if editing
            data['note_id'] = self.note_data['note_id']
        return data

    def accept(self):
        data = self.get_data()

        # Validation
        if not data["document_type"]:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le type de document est requis."))
            self.document_type_combo.setFocus()
            return
        if not data["language_code"]:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le code langue est requis."))
            self.language_code_combo.setFocus()
            return
        if not data["note_content"]:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le contenu de la note ne peut pas être vide."))
            self.note_content_edit.setFocus()
            return

        try:
            if self.note_data and 'note_id' in self.note_data: # Editing mode
                success = db_manager.update_client_document_note(self.note_data['note_id'], data)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Note de document mise à jour avec succès."))
                    super().accept()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour la note de document. Vérifiez pour les doublons (Client, Type, Langue) ou les erreurs de base de données."))
            else: # Adding mode
                note_id = db_manager.add_client_document_note(data)
                if note_id:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Note de document ajoutée avec succès (ID: {0}).").format(note_id))
                    super().accept()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter la note de document. Une note pour cette combinaison Client, Type et Langue existe peut-être déjà."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue: {0}").format(str(e)))


class ProductDimensionUIDialog(QDialog):
    def __init__(self, product_id, parent=None, read_only=False): # Added read_only parameter
        super().__init__(parent)
        self.product_id = product_id
        self.read_only = read_only # Store read_only state
        self.setWindowTitle(self.tr("Gérer Dimensions Détaillées du Produit") + f" (ID: {self.product_id})")
        self.setMinimumSize(500, 600)

        self.current_tech_image_path = None

        self.setup_ui()
        self.load_dimensions()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        form_group = QGroupBox(self.tr("Dimensions Spécifiques"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self.dimension_inputs = {}
        for dim_label in [f"dim_{chr(65 + i)}" for i in range(10)]: # dim_A to dim_J
            line_edit = QLineEdit()
            self.dimension_inputs[dim_label] = line_edit
            form_layout.addRow(self.tr(f"Dimension {dim_label[-1]}:"), line_edit)

        main_layout.addWidget(form_group)

        # Technical Image Section
        tech_image_group = QGroupBox(self.tr("Image Technique"))
        tech_image_layout = QVBoxLayout(tech_image_group)

        path_button_layout = QHBoxLayout()
        self.tech_image_path_input = QLineEdit()
        self.tech_image_path_input.setReadOnly(True)
        self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image sélectionnée"))
        path_button_layout.addWidget(self.tech_image_path_input)

        self.browse_tech_image_button = QPushButton(self.tr("Parcourir..."))
        self.browse_tech_image_button.setIcon(QIcon.fromTheme("document-open"))
        self.browse_tech_image_button.clicked.connect(self.handle_browse_tech_image)
        path_button_layout.addWidget(self.browse_tech_image_button)
        tech_image_layout.addLayout(path_button_layout)

        self.tech_image_preview_label = QLabel(self.tr("Aperçu de l'image non disponible."))
        self.tech_image_preview_label.setAlignment(Qt.AlignCenter)
        self.tech_image_preview_label.setMinimumSize(200, 200) # Minimum size for preview
        self.tech_image_preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        tech_image_layout.addWidget(self.tech_image_preview_label)

        main_layout.addWidget(tech_image_group)
        main_layout.addStretch()

        # Dialog Button Box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if self.read_only:
            for dim_input_widget in self.dimension_inputs.values():
                dim_input_widget.setReadOnly(True)
            self.browse_tech_image_button.setEnabled(False)
            save_button = self.button_box.button(QDialogButtonBox.Save)
            if save_button:
                save_button.setEnabled(False)
            # Optionally change text of Cancel to Close if Save is hidden, not just disabled
            # cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
            # if cancel_button:
            #     cancel_button.setText(self.tr("Fermer"))

        self.setLayout(main_layout)

    def load_dimensions(self):
        """Loads existing dimensions from the database and populates the form fields."""
        print(f"INFO: ProductDimensionUIDialog.load_dimensions() called for product_id: {self.product_id}.")
        try:
            dimension_data = db_manager.get_product_dimension(self.product_id)
            if dimension_data:
                for dim_ui_key, input_widget in self.dimension_inputs.items():
                    db_key = dim_ui_key.lower()
                    input_widget.setText(dimension_data.get(db_key, ""))

                technical_image_path_from_db = dimension_data.get('technical_image_path', '')
                self.current_tech_image_path = technical_image_path_from_db # Store relative path

                if technical_image_path_from_db:
                    self.tech_image_path_input.setText(technical_image_path_from_db) # Display relative path

                    # Construct absolute path for preview
                    if not hasattr(self, 'app_root_dir') or not self.app_root_dir:
                        # This case should ideally be prevented by __init__ or earlier checks
                        # if app_root_dir is critical for operation.
                        print("ERROR: app_root_dir not set in ProductDimensionUIDialog. Cannot form absolute path for image.")
                        self.tech_image_preview_label.setText(self.tr("Erreur configuration (chemin racine)."))
                        # self.current_tech_image_path = None # Path is unusable
                        return # Cannot proceed with image loading

                    absolute_image_path = os.path.join(self.app_root_dir, technical_image_path_from_db)

                    if os.path.exists(absolute_image_path):
                        pixmap = QPixmap(absolute_image_path)
                        if not pixmap.isNull():
                            self.tech_image_preview_label.setPixmap(
                                pixmap.scaled(
                                    self.tech_image_preview_label.size(),
                                    Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation
                                )
                            )
                        else:
                            self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide)."))
                    else:
                        self.tech_image_preview_label.setText(self.tr("Image non trouvée au chemin stocké."))
                        # self.current_tech_image_path = None # Optionally clear if path is broken
                else:
                    self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image technique définie."))
                    self.tech_image_preview_label.setText(self.tr("Aucune image technique."))
                    self.current_tech_image_path = None # Ensure it's None if DB path is empty
            else:
                # No data found, ensure form is clear (should be by default, but good practice)
                for input_widget in self.dimension_inputs.values():
                    input_widget.clear()
                self.tech_image_path_input.clear()
                self.tech_image_path_input.setPlaceholderText(self.tr("Aucune dimension détaillée trouvée pour ce produit."))
                self.tech_image_preview_label.setText(self.tr("Aperçu de l'image non disponible."))
                self.current_tech_image_path = None

        except Exception as e:
            print(f"ERROR: Failed to load product dimensions for product_id {self.product_id}: {e}")
            QMessageBox.critical(self, self.tr("Erreur de Chargement"),
                                 self.tr("Impossible de charger les dimensions du produit:\n{0}").format(str(e)))


    def handle_browse_tech_image(self):
        """Opens a QFileDialog to select an image and updates the path and preview."""
        # Use a more specific directory if available, e.g., from config or last used
        # For now, defaulting to home directory or current directory.
        # Consider storing and retrieving the last used directory.
        initial_dir = os.path.expanduser("~")

        source_file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner une Image Technique"),
            initial_dir,
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        )

        if source_file_path:
            base_product_images_dir_name = "product_technical_images"
            # Ensure app_root_dir is available, e.g., passed in __init__
            if not hasattr(self, 'app_root_dir') or not self.app_root_dir:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le chemin racine de l'application n'est pas configuré."))
                return

            target_product_dir = os.path.join(self.app_root_dir, base_product_images_dir_name, str(self.product_id))

            try:
                os.makedirs(target_product_dir, exist_ok=True)
                image_filename = os.path.basename(source_file_path)
                absolute_target_file_path = os.path.join(target_product_dir, image_filename)

                shutil.copy2(source_file_path, absolute_target_file_path) # Use shutil.copy2 to preserve metadata

                # Store and display the relative path
                relative_image_path = os.path.join(base_product_images_dir_name, str(self.product_id), image_filename)
                # Convert to platform-independent path separators (/) for DB consistency and display
                relative_image_path = relative_image_path.replace(os.sep, '/')

                self.tech_image_path_input.setText(relative_image_path)
                self.current_tech_image_path = relative_image_path # This is what gets saved to DB

                # Preview using the absolute path of the copied image
                pixmap = QPixmap(absolute_target_file_path)
                if not pixmap.isNull():
                    self.tech_image_preview_label.setPixmap(
                        pixmap.scaled(
                            self.tech_image_preview_label.size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                    )
                else:
                    self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide après copie)."))
                    self.current_tech_image_path = None # Clear if copy succeeded but image is invalid for display

            except shutil.Error as e_shutil:
                QMessageBox.critical(self, self.tr("Erreur de Copie"), self.tr("Impossible de copier l'image sélectionnée : {0}").format(str(e_shutil)))
                # Do not update self.current_tech_image_path or input field if copy fails
            except Exception as e_general:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue lors du traitement de l'image : {0}").format(str(e_general)))
                # Do not update self.current_tech_image_path or input field

    def accept(self):
        """Gathers data and calls db_manager.add_or_update_product_dimension()."""
        dimension_data_to_save = {}
        for dim_key, input_widget in self.dimension_inputs.items():
            dimension_data_to_save[dim_key.lower()] = input_widget.text().strip() # Store with lowercase keys for DB

        # Handle image path:
        # The actual file copying/management strategy is TBD.
        # For now, we save the selected path. If product-specific folders are used,
        # this path might be made relative to that folder or the file copied.
        # For this step, self.current_tech_image_path holds the selected path.
        dimension_data_to_save['technical_image_path'] = self.current_tech_image_path

        print(f"INFO: Attempting to save dimensions for product_id {self.product_id}: {dimension_data_to_save}")

        if self.read_only:
            super().accept() # Or self.done(QDialog.Accepted) if just closing
            return

        try:
            success = db_manager.add_or_update_product_dimension(self.product_id, dimension_data_to_save)
            if success:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Dimensions du produit enregistrées avec succès."))
                super().accept() # Call QDialog's accept to close the dialog
            else:
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'enregistrer les dimensions du produit. Vérifiez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue lors de l'enregistrement des dimensions:\n{0}").format(str(e)))
            # Do not call super().accept() on error, so dialog stays open


class SelectUtilityAttachmentDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_files = []
        self.utility_category_name = "Document Utilitaires" # Or make this configurable

        self.setWindowTitle(self.tr("Sélectionner Documents Utilitaires"))
        self.setMinimumSize(500, 350)
        self.setup_ui()
        self.load_utility_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.doc_table_widget = QTableWidget()
        self.doc_table_widget.setColumnCount(4) # Checkbox, Name, Language, Filename
        self.doc_table_widget.setHorizontalHeaderLabels([
            "", # For checkbox
            self.tr("Nom du Document"),
            self.tr("Langue"),
            self.tr("Nom de Fichier")
        ])
        self.doc_table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.doc_table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.doc_table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.doc_table_widget.setColumnWidth(0, 30) # Checkbox column width

        layout.addWidget(QLabel(self.tr("Documents utilitaires disponibles :")))
        layout.addWidget(self.doc_table_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok); ok_button.setText(self.tr("OK")); ok_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel); cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_utility_documents(self):
        self.doc_table_widget.setRowCount(0)
        category = db_manager.get_template_category_by_name(self.utility_category_name)
        if not category:
            QMessageBox.warning(self, self.tr("Erreur Catégorie"),
                                self.tr("La catégorie '{0}' est introuvable.").format(self.utility_category_name))
            return

        templates = db_manager.get_templates_by_category_id(category['category_id'])
        if not templates:
            QMessageBox.information(self, self.tr("Aucun Document"),
                                    self.tr("Aucun document utilitaire trouvé dans la catégorie '{0}'.").format(self.utility_category_name))
            return

        templates_dir = self.config.get("templates_dir")
        if not templates_dir:
            QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le dossier des modèles n'est pas configuré."))
            return

        for row_idx, template_data in enumerate(templates):
            self.doc_table_widget.insertRow(row_idx)

            # Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Unchecked)
            self.doc_table_widget.setItem(row_idx, 0, chk_item)

            # Document Name
            name_item = QTableWidgetItem(template_data.get('template_name', self.tr('N/A')))
            self.doc_table_widget.setItem(row_idx, 1, name_item)

            # Language
            lang_code = template_data.get('language_code', self.tr('N/A'))
            self.doc_table_widget.setItem(row_idx, 2, QTableWidgetItem(lang_code))

            # Filename
            base_file_name = template_data.get('base_file_name', self.tr('N/A'))
            self.doc_table_widget.setItem(row_idx, 3, QTableWidgetItem(base_file_name))

            # Store full path in UserRole of the name item (column 1)
            # Assuming 'common' as a potential subdirectory if language_code is generic or not applicable for some utility docs
            # Or using language_code directly if utility docs are language-specific under templates/<lang>/
            # For this subtask, we'll use the direct language_code from the template.
            # If a template has 'common' as language_code, it should be in templates/common/
            # If it has 'fr', it should be in templates/fr/
            # The problem statement implies utility docs might be in templates/utility/fr or templates/utility/common
            # This needs clarification. For now, let's assume templates_dir/language_code/base_file_name is the structure.
            # If 'utility' is a fixed subfolder, the path construction needs adjustment.
            # Based on "templates/utility/fr/" example, 'utility' seems like a sub-path within templates_dir
            # Let's assume for now that 'language_code' in DB for utility might be 'utility/fr' or 'utility/common'
            # OR that 'base_file_name' itself contains the 'utility/' prefix.
            # For simplicity, this code will assume templates_dir / template_language_code / base_file_name.
            # If 'utility' is a hardcoded part of the path for this category, it needs to be inserted.
            # The current template system does not have a concept of subdirectories within a language folder based on category.
            # Let's stick to the existing convention: templates_dir/language_code/base_file_name
            # If 'Document Utilitaires' are truly global, they might have a special lang_code like 'common' or 'all'.

            full_path = os.path.join(templates_dir, lang_code, base_file_name)
            if not os.path.exists(full_path):
                # Try a 'utility' subdirectory as a fallback, if that's the convention for these files
                # This is an assumption based on the example "templates/utility/fr/"
                alt_path = os.path.join(templates_dir, "utility", lang_code, base_file_name)
                if os.path.exists(alt_path):
                    full_path = alt_path
                else:
                    # Mark item as not selectable or indicate error
                    name_item.setForeground(QColor("red"))
                    name_item.setToolTip(self.tr("Fichier non trouvé: {0}").format(full_path))
                    chk_item.setFlags(chk_item.flags() & ~Qt.ItemIsEnabled) # Disable checkbox
                    full_path = None # Ensure it's not added if not found

            if full_path:
                 name_item.setData(Qt.UserRole, full_path)


    def accept_selection(self):
        self.selected_files = []
        for row in range(self.doc_table_widget.rowCount()):
            chk_item = self.doc_table_widget.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                name_item = self.doc_table_widget.item(row, 1)
                if name_item:
                    file_path = name_item.data(Qt.UserRole)
                    if file_path and os.path.exists(file_path): # Check again before adding
                        self.selected_files.append(file_path)
                    elif file_path: # Path was stored but file now missing
                        QMessageBox.warning(self, self.tr("Fichier Manquant"), self.tr("Le fichier {0} n'a pas pu être trouvé au moment de la sélection.").format(os.path.basename(file_path)))
        self.accept()

    def get_selected_files(self):
        return self.selected_files


class ClientProductDimensionDialog(QDialog):
    def __init__(self, client_id, product_id, app_root_dir, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.product_id = product_id
        self.app_root_dir = app_root_dir
        self.current_tech_image_path = None  # Store relative path to image

        self.setWindowTitle(self.tr("Gérer Dimensions Produit Client") + f" (Produit ID: {self.product_id})")
        self.setMinimumSize(500, 600) # Adjusted as per ProductDimensionUIDialog

        self.setup_ui()
        self.load_dimensions()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        form_group = QGroupBox(self.tr("Dimensions Spécifiques"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self.dimension_inputs = {}
        for i in range(10): # dim_A to dim_J
            dim_label_key = f"dim_{chr(65 + i)}" # e.g., dim_A
            line_edit = QLineEdit()
            self.dimension_inputs[dim_label_key] = line_edit
            form_layout.addRow(self.tr(f"Dimension {chr(65+i)}:"), line_edit)

        main_layout.addWidget(form_group)

        # Technical Image Section
        tech_image_group = QGroupBox(self.tr("Image Technique"))
        tech_image_layout = QVBoxLayout(tech_image_group)

        path_button_layout = QHBoxLayout()
        self.tech_image_path_input = QLineEdit()
        self.tech_image_path_input.setReadOnly(True)
        self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image sélectionnée"))
        path_button_layout.addWidget(self.tech_image_path_input)

        self.browse_tech_image_button = QPushButton(self.tr("Parcourir..."))
        self.browse_tech_image_button.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/folder.svg"))) # Fallback icon
        self.browse_tech_image_button.clicked.connect(self.handle_browse_tech_image)
        path_button_layout.addWidget(self.browse_tech_image_button)
        tech_image_layout.addLayout(path_button_layout)

        self.tech_image_preview_label = QLabel(self.tr("Aperçu de l'image non disponible."))
        self.tech_image_preview_label.setAlignment(Qt.AlignCenter)
        self.tech_image_preview_label.setMinimumSize(200, 200)
        self.tech_image_preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        tech_image_layout.addWidget(self.tech_image_preview_label)

        main_layout.addWidget(tech_image_group)
        main_layout.addStretch()

        # Dialog Button Box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))

        self.button_box.accepted.connect(self.accept) # Connected to overridden accept
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_dimensions(self):
        try:
            # For ClientProductDimensionDialog, we are editing dimensions specific to a product_id,
            # but these are still stored in the 'product_dimensions' table, keyed by product_id.
            # There isn't a separate table like 'client_product_dimensions'.
            # The context of 'client_id' is for potential future use or if behavior needs to differ,
            # but the data source is the global product_dimensions for this product_id.
            dimension_data = db_manager.get_product_dimension(self.product_id)
            if dimension_data:
                for dim_ui_key, input_widget in self.dimension_inputs.items():
                    db_key = dim_ui_key.lower() # e.g. "dim_a"
                    input_widget.setText(dimension_data.get(db_key, ""))

                technical_image_path_from_db = dimension_data.get('technical_image_path', '')
                self.current_tech_image_path = technical_image_path_from_db

                if technical_image_path_from_db:
                    self.tech_image_path_input.setText(technical_image_path_from_db)
                    # Construct absolute path for preview
                    absolute_image_path = os.path.join(self.app_root_dir, technical_image_path_from_db)
                    if os.path.exists(absolute_image_path):
                        pixmap = QPixmap(absolute_image_path)
                        if not pixmap.isNull():
                            self.tech_image_preview_label.setPixmap(
                                pixmap.scaled(
                                    self.tech_image_preview_label.width(), # Use label's current size
                                    self.tech_image_preview_label.height(),
                                    Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation
                                )
                            )
                        else:
                            self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide)."))
                    else:
                        self.tech_image_preview_label.setText(self.tr("Image non trouvée."))
                else:
                    self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image technique définie."))
                    self.tech_image_preview_label.setText(self.tr("Aucune image technique."))
                    self.current_tech_image_path = None
            else:
                for input_widget in self.dimension_inputs.values():
                    input_widget.clear()
                self.tech_image_path_input.clear()
                self.tech_image_preview_label.setText(self.tr("Aucune dimension pour ce produit."))
                self.current_tech_image_path = None
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement Dimensions"),
                                 self.tr("Impossible de charger les dimensions: {0}").format(str(e)))
            self.current_tech_image_path = None # Reset on error

    def handle_browse_tech_image(self):
        initial_dir = os.path.expanduser("~")
        source_file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner une Image Technique"),
            initial_dir,
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        )

        if source_file_path:
            base_product_images_dir_name = "product_technical_images"
            # Product-specific subfolder using product_id
            target_product_dir = os.path.join(self.app_root_dir, base_product_images_dir_name, str(self.product_id))

            try:
                os.makedirs(target_product_dir, exist_ok=True)
                image_filename = os.path.basename(source_file_path)
                # It's crucial that absolute_target_file_path uses os.path.join for platform compatibility
                absolute_target_file_path = os.path.join(target_product_dir, image_filename)

                shutil.copy2(source_file_path, absolute_target_file_path)

                # Store and display the relative path using forward slashes for consistency
                relative_image_path = os.path.join(base_product_images_dir_name, str(self.product_id), image_filename).replace(os.sep, '/')

                self.tech_image_path_input.setText(relative_image_path)
                self.current_tech_image_path = relative_image_path

                pixmap = QPixmap(absolute_target_file_path)
                if not pixmap.isNull():
                    self.tech_image_preview_label.setPixmap(
                        pixmap.scaled(
                            self.tech_image_preview_label.width(),
                            self.tech_image_preview_label.height(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation))
                else:
                    self.tech_image_preview_label.setText(self.tr("Aperçu non disponible."))
                    self.current_tech_image_path = None
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Copie Image"),
                                     self.tr("Impossible de copier l'image: {0}").format(str(e)))
                self.current_tech_image_path = None # Reset on error

    def accept(self):
        dimension_data_to_save = {}
        for dim_key, input_widget in self.dimension_inputs.items():
            dimension_data_to_save[dim_key.lower()] = input_widget.text().strip()

        dimension_data_to_save['technical_image_path'] = self.current_tech_image_path

        try:
            # The product_id is the global product_id. Dimensions are stored against this ID.
            # The client_id in this dialog is for context but not directly used for this DB operation
            # unless the DB schema for product_dimensions also includes client_id, which it doesn't seem to.
            success = db_manager.add_or_update_product_dimension(self.product_id, dimension_data_to_save)
            if success:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Dimensions du produit enregistrées avec succès."))
                super().accept()  # Call QDialog's accept to close
            else:
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'enregistrer les dimensions. Vérifiez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Enregistrement"),
                                 self.tr("Une erreur est survenue: {0}").format(str(e)))
# [end of dialogs.py]

# [end of dialogs.py]
