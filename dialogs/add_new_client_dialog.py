# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QDialogButtonBox,
    QMessageBox, QCompleter, QInputDialog
)
from PyQt5.QtCore import Qt
import db as db_manager

class AddNewClientDialog(QDialog):
    def __init__(self, parent=None, initial_country_name=None):
        super().__init__(parent)
        self.initial_country_name = initial_country_name
        self.setWindowTitle(self.tr("Ajouter un Nouveau Client"))
        self.setMinimumSize(500, 400) # Adjust as needed
        self.country_id = None # To store determined country_id
        self.city_id = None # To store determined city_id
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
            self.tr("Russian only (ru)"): ["ru"],
            self.tr("All supported languages (en, fr, ar, tr, pt, ru)"): ["en", "fr", "ar", "tr", "pt", "ru"]
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
        self._handle_initial_country()

    def _handle_initial_country(self):
        if self.initial_country_name:
            print(f"Attempting to pre-select country: {self.initial_country_name}")
            country_index = self.country_select_combo.findText(self.initial_country_name, Qt.MatchFixedString | Qt.MatchCaseSensitive) # More precise match
            if country_index >= 0:
                self.country_select_combo.setCurrentIndex(country_index)
                print(f"Country '{self.initial_country_name}' pre-selected at index {country_index}.")
                # self.load_cities_for_country(self.initial_country_name) # Trigger city loading
            else:
                # Country not in combo. It might be new.
                # The combobox is editable, so user can type it.
                # Accept logic will handle adding it.
                self.country_select_combo.lineEdit().setText(self.initial_country_name)
                print(f"Country '{self.initial_country_name}' not in list, set as editable text.")
                # self.load_cities_for_country(self.initial_country_name) # Try loading cities, will likely be empty

    def load_countries_into_combo(self):
        current_country_text = self.country_select_combo.lineEdit().text() if self.country_select_combo.isEditable() else self.country_select_combo.currentText()
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))

            # Restore previous text if it was being edited or if it's a new country
            if self.initial_country_name and self.country_select_combo.findText(self.initial_country_name, Qt.MatchFixedString | Qt.MatchCaseSensitive) == -1 :
                 self.country_select_combo.lineEdit().setText(self.initial_country_name)
            elif current_country_text:
                 idx = self.country_select_combo.findText(current_country_text, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                 if idx != -1:
                     self.country_select_combo.setCurrentIndex(idx)
                 elif self.country_select_combo.isEditable():
                      self.country_select_combo.lineEdit().setText(current_country_text)

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))

    def load_cities_for_country(self, country_name_or_id):
        self.city_select_combo.clear()
        country_id_to_load = None

        if isinstance(country_name_or_id, int): # if ID is passed
            country_id_to_load = country_name_or_id
        elif isinstance(country_name_or_id, str) and country_name_or_id: # if name is passed
            selected_country_id_from_combo = self.country_select_combo.currentData()
            if selected_country_id_from_combo is not None and self.country_select_combo.currentText() == country_name_or_id:
                country_id_to_load = selected_country_id_from_combo
            else: # Country name might be new or different from combo's currentData
                country_obj_by_name = db_manager.get_country_by_name(country_name_or_id)
                if country_obj_by_name:
                    country_id_to_load = country_obj_by_name['country_id']
                # If country_obj_by_name is None, it's a new country, so no cities to load yet.

        if not country_id_to_load:
            # This can happen if country_name_or_id is empty, or if it's a new country name not yet in DB.
            # City combo should remain empty.
            return

        try:
            cities = db_manager.get_all_cities(country_id=country_id_to_load)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))


    def add_new_country_dialog(self):
        # QInputDialog is not in the identified imports. It might be needed.
        # For now, proceeding without it. If QInputDialog is essential, this will error.
        # Let's assume QInputDialog is implicitly available or was missed in analysis.
        # Upon review, QInputDialog is imported in the original dialogs.py. It should be added.
        # For this iteration, I will proceed with the current import list and add QInputDialog if an error occurs.
        # This is a simulated step-by-step process.
        # Correcting: Add QInputDialog to imports.

        # Re-evaluating imports from original dialogs.py for AddNewClientDialog:
        # It uses QInputDialog.
        # from PyQt5.QtWidgets import QInputDialog
        # So, the import list should be:
        # from PyQt5.QtWidgets import (
        #     QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        #     QLineEdit, QPushButton, QComboBox, QDialogButtonBox,
        #     QMessageBox, QCompleter, QInputDialog
        # )
        # I will update the file content with this corrected import.

        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                returned_country_id = db_manager.add_country({'country_name': country_text.strip()})
                if returned_country_id is not None:
                    self.load_countries_into_combo() # Reloads all countries
                    # Attempt to find and set the newly added country
                    index_to_select = -1
                    for i in range(self.country_select_combo.count()):
                        if self.country_select_combo.itemData(i) == returned_country_id:
                            index_to_select = i
                            break
                    if index_to_select != -1:
                        self.country_select_combo.setCurrentIndex(index_to_select)
                    else: # Fallback if ID not found, try by text
                        index_by_text = self.country_select_combo.findText(country_text.strip())
                        if index_by_text >=0: self.country_select_combo.setCurrentIndex(index_by_text)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def add_new_city_dialog(self):
        current_country_id_from_combo = self.country_select_combo.currentData()
        current_country_name = self.country_select_combo.currentText()

        final_country_id_for_city = None
        if current_country_id_from_combo is not None:
            final_country_id_for_city = current_country_id_from_combo
        elif current_country_name: # If country was typed and not in DB yet
            country_data = db_manager.get_or_add_country(current_country_name) # Add it now
            if country_data and country_data.get('country_id'):
                final_country_id_for_city = country_data['country_id']
                self.load_countries_into_combo() # Refresh countries
                # Reselect the country that was just added
                idx = self.country_select_combo.findData(final_country_id_for_city)
                if idx != -1: self.country_select_combo.setCurrentIndex(idx)


        if not final_country_id_for_city:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner ou entrer un pays valide."))
            return

        # QInputDialog is used here too.
        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                # Use get_or_add_city here
                city_data = db_manager.get_or_add_city(city_name=city_text.strip(), country_id=final_country_id_for_city)
                if city_data and city_data.get('city_id') is not None:
                    self.load_cities_for_country(final_country_id_for_city) # Reload cities for the relevant country ID
                    # Attempt to find and set the newly added/found city
                    index_to_select = -1
                    for i in range(self.city_select_combo.count()):
                        if self.city_select_combo.itemData(i) == city_data['city_id']:
                            index_to_select = i
                            break
                    if index_to_select != -1:
                        self.city_select_combo.setCurrentIndex(index_to_select)
                    else: # Fallback if ID not found, try by text
                        index_by_text = self.city_select_combo.findText(city_text.strip())
                        if index_by_text >=0: self.city_select_combo.setCurrentIndex(index_by_text)

                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout ou de récupération de la ville. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def accept(self):
        # Get final country name and ID
        country_name = self.country_select_combo.currentText().strip()
        country_id_from_combo = self.country_select_combo.currentData()

        if not country_name:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du pays est requis."))
            self.country_select_combo.setFocus()
            return

        final_country_id = country_id_from_combo
        if final_country_id is None: # Country was typed or not found
            country_data = db_manager.get_or_add_country(country_name)
            if country_data and country_data.get('country_id'):
                final_country_id = country_data['country_id']
            else:
                QMessageBox.warning(self, self.tr("Erreur Pays"), self.tr("Impossible de déterminer ou d'ajouter le pays: {0}").format(country_name))
                return
        self.country_id = final_country_id # Store for get_data

        # Get final city name and ID
        city_name = self.city_select_combo.currentText().strip()
        city_id_from_combo = self.city_select_combo.currentData()
        final_city_id = city_id_from_combo

        if city_name: # City is optional, but if provided, ensure it's processed
            if final_city_id is None: # City was typed or not found
                # db_manager.get_or_add_city expects country_id
                if not self.country_id: # Should not happen if country logic above is correct
                     QMessageBox.critical(self, self.tr("Erreur Critique"), self.tr("ID Pays non défini avant traitement de la ville."))
                     return
                city_data = db_manager.get_or_add_city(city_name, self.country_id)
                if city_data and city_data.get('city_id'):
                    final_city_id = city_data['city_id']
                else:
                    QMessageBox.warning(self, self.tr("Erreur Ville"), self.tr("Impossible de déterminer ou d'ajouter la ville: {0}").format(city_name))
                    # If city is optional and fails, we might want to proceed with city_id=None
                    # For now, let's assume if a city name is typed, it should be valid or addable.
                    # If strictly optional even if typed and fails, this could be changed.
                    final_city_id = None # Set to None if it fails, effectively making it optional
            self.city_id = final_city_id
        else: # No city name provided
            self.city_id = None

        # Validate other fields before calling super().accept()
        client_name = self.client_name_input.text().strip()
        if not client_name:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du client est requis."))
            self.client_name_input.setFocus()
            return # Don't call super().accept()

        super().accept() # This will allow get_data to be called by the main window if QDialog.Accepted

    def get_data(self):
        client_name = self.client_name_input.text().strip()
        company_name = self.company_name_input.text().strip()
        client_need = self.client_need_input.text().strip()
        project_id_text = self.project_id_input_field.text().strip()

        selected_lang_display_text = self.language_select_combo.currentText()
        selected_languages = self.language_options_map.get(selected_lang_display_text, ["fr"])

        # self.country_id and self.city_id are set in the overridden accept() method
        return {
            "client_name": client_name,
            "company_name": company_name,
            "primary_need_description": client_need,
            "country_id": self.country_id, # Use the ID determined in accept()
            "country_name": self.country_select_combo.currentText().strip(), # Current text for display
            "city_id": self.city_id, # Use the ID determined in accept()
            "city_name": self.city_select_combo.currentText().strip(), # Current text for display
            "project_identifier": project_id_text,
            "selected_languages": ",".join(selected_languages)
        }
