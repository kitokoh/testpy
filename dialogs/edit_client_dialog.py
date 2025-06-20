# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, QPushButton,
    QDialogButtonBox, QDoubleSpinBox, QMessageBox, QComboBox,
    QHBoxLayout, QLabel, QCompleter
)
from PyQt5.QtCore import Qt # For QCompleter flags and other Qt specific attributes

import db as db_manager
from db.cruds.templates_crud import get_all_templates # Added for template selection

class EditClientDialog(QDialog):
    def __init__(self, client_info, config, parent=None): # Config is passed
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config, though not directly used in snippet
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
        self.load_cities_for_country_edit(self.country_select_combo.currentText()) # Initial load based on selected country
        current_city_id = self.client_info.get('city_id')
        if current_city_id is not None:
            index = self.city_select_combo.findData(current_city_id)
            if index >= 0:
                self.city_select_combo.setCurrentIndex(index)
            else: # Fallback to name if ID not found (e.g. if city was manually entered and not in DB initially)
                current_city_name = self.client_info.get('city')
                if current_city_name:
                    index_name = self.city_select_combo.findText(current_city_name)
                    if index_name >=0:
                         self.city_select_combo.setCurrentIndex(index_name)
        layout.addRow(self.tr("Ville Client:"), self.city_select_combo)

        self.language_select_combo = QComboBox()
        self.lang_display_to_codes_map = {
            self.tr("Français uniquement (fr)"): ["fr"],
            self.tr("English only (en)"): ["en"],
            self.tr("Arabe uniquement (ar)"): ["ar"],
            self.tr("Turc uniquement (tr)"): ["tr"],
            self.tr("Portuguese only (pt)"): ["pt"],
            self.tr("Russian only (ru)"): ["ru"],
            self.tr("Toutes les langues (fr, en, ar, tr, pt, ru)"): ["fr", "en", "ar", "tr", "pt", "ru"]
        }
        self.language_select_combo.addItems(list(self.lang_display_to_codes_map.keys()))
        current_lang_codes_str = self.client_info.get('selected_languages', 'fr') # Default to 'fr' string
        current_lang_codes = [code.strip() for code in str(current_lang_codes_str).split(',') if code.strip()]
        if not current_lang_codes: current_lang_codes = ['fr'] # Ensure at least 'fr' if empty after split

        selected_display_string = None
        for display_string, codes_list in self.lang_display_to_codes_map.items():
            if sorted(codes_list) == sorted(current_lang_codes):
                selected_display_string = display_string; break
        if selected_display_string: self.language_select_combo.setCurrentText(selected_display_string)
        else: self.language_select_combo.setCurrentText(self.tr("Français uniquement (fr)")) # Fallback
        layout.addRow(self.tr("Langues:"), self.language_select_combo)

        self.default_template_combo = QComboBox()
        layout.addRow(self.tr("Default Template:"), self.default_template_combo)
        self.populate_template_combo() # Populate before trying to set
        current_default_template_id = self.client_info.get('default_template_id')
        if current_default_template_id is not None:
            index = self.default_template_combo.findData(current_default_template_id)
            if index >= 0:
                self.default_template_combo.setCurrentIndex(index)
        else: # If None, ensure "-- No Default --" is selected if it exists and is the first item
            if self.default_template_combo.count() > 0 and self.default_template_combo.itemData(0) is None:
                 self.default_template_combo.setCurrentIndex(0)


        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK")); button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject); layout.addRow(button_box)

    def populate_template_combo(self):
        self.default_template_combo.clear()
        self.default_template_combo.addItem(self.tr("-- No Default --"), None)
        try:
            templates = get_all_templates() # Assuming get_all_templates can be called without args or with None conn
            if templates:
                for template in templates:
                    self.default_template_combo.addItem(template['template_name'], template['template_id'])
        except Exception as e:
            QMessageBox.warning(self, self.tr("Template Loading Error"), self.tr("Could not load templates: {0}").format(str(e)))

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
        if not country_name_str: return # Do nothing if country name is empty

        selected_country_id = self.country_select_combo.currentData() # This is country_id from combo's UserRole

        # If currentData is None (e.g. user typed a new country not yet in DB), try to get ID by name
        if selected_country_id is None:
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name:
                selected_country_id = country_obj_by_name['country_id']
            else: # Country name not in DB, so no cities to load
                return

        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities: self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def get_data(self) -> dict:
        data = {};
        data['client_name'] = self.client_name_input.text().strip();
        data['company_name'] = self.company_name_input.text().strip()
        data['primary_need_description'] = self.client_need_input.text().strip();
        data['project_identifier'] = self.project_id_input_field.text().strip()
        data['price'] = self.final_price_input.value();
        data['status_id'] = self.status_select_combo.currentData()
        data['category'] = self.category_input.text().strip();
        data['notes'] = self.notes_edit.toPlainText().strip()

        country_id = self.country_select_combo.currentData()
        country_name = self.country_select_combo.currentText().strip()
        if country_id is None and country_name: # Country was typed or is not in DB
            country_obj = db_manager.get_or_add_country(country_name) # Use get_or_add
            if country_obj: country_id = country_obj['country_id']
        data['country_id'] = country_id

        city_id = self.city_select_combo.currentData()
        city_name = self.city_select_combo.currentText().strip()
        if city_id is None and city_name and data.get('country_id') is not None: # City was typed or not in DB
            city_obj = db_manager.get_or_add_city(city_name, data['country_id']) # Use get_or_add
            if city_obj: city_id = city_obj['city_id']
        data['city_id'] = city_id

        selected_lang_display_text = self.language_select_combo.currentText()
        lang_codes_list = self.lang_display_to_codes_map.get(selected_lang_display_text, ["fr"])
        data['selected_languages'] = ",".join(lang_codes_list)
        data['default_template_id'] = self.default_template_combo.currentData()
        return data

    # The accept method for EditClientDialog was not in the provided dialogs.py snippet.
    # It would typically call get_data() and then db_manager.update_client(self.client_info['client_id'], updated_data)
    # For now, this refactoring will keep it as is. If an accept method is needed, it would be:
    # def accept(self):
    #     updated_data = self.get_data()
    #     # Call to db_manager.update_client or similar clients_crud_instance method
    #     # clients_crud_instance.update_client(self.client_info['client_id'], updated_data)
    #     super().accept()
    # This is not added as it's not in the source. The dialog will likely be accepted/rejected by caller.
    # However, standard QDialog practice is to handle accept locally if it performs actions.
    # The original EditClientDialog in main.py might have its accept connected externally.
    # For consistency with other dialogs, let's assume it should have its own accept logic.
    # Re-checking dialogs.py, EditClientDialog does not have an accept method. It's handled by the caller.
    # So, no accept method will be added here.
