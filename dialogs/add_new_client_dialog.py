# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QDialogButtonBox,
    QMessageBox, QCompleter, QInputDialog
)
from PyQt5.QtCore import Qt
# import db as db_manager # Removed
from controllers.client_controller import ClientController # Added

class AddNewClientDialog(QDialog):
    def __init__(self, parent=None, initial_country_name=None):
        super().__init__(parent)
        self.client_controller = ClientController() # Added
        self.initial_country_name = initial_country_name
        self.setWindowTitle(self.tr("Ajouter un Nouveau Client"))
        self.setMinimumSize(500, 400)
        # self.country_id = None # Removed, controller will handle ID resolution
        # self.city_id = None # Removed, controller will handle ID resolution
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
        # self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country_by_name) # Old connection
        self.country_select_combo.currentIndexChanged.connect(self.on_country_selected) # Use index change if data is ID
        self.country_select_combo.lineEdit().editingFinished.connect(self.on_country_text_changed) # Handle typed text

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

    def populate_from_voice_data(self, data: dict):
        self.client_name_input.setText(data.get('client_name', ''))
        self.company_name_input.setText(data.get('company_name', ''))
        self.client_need_input.setText(data.get('primary_need_description', ''))
        self.project_id_input_field.setText(data.get('project_identifier', ''))

        country_name = data.get('country_name')
        if country_name:
            self.country_select_combo.lineEdit().setText(country_name) # Set text
            self.on_country_text_changed() # Trigger city loading based on new text

        city_name = data.get('city_name')
        if city_name:
            self.city_select_combo.lineEdit().setText(city_name)


    def _handle_initial_country(self):
        if self.initial_country_name:
            self.country_select_combo.lineEdit().setText(self.initial_country_name)
            self.on_country_text_changed() # This will load cities if country is found or is new


    def load_countries_into_combo(self):
        current_country_text = self.country_select_combo.lineEdit().text()
        self.country_select_combo.blockSignals(True)
        self.country_select_combo.clear()
        try:
            countries = self.client_controller.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict['country_id'])

            # Try to restore selection or text
            if current_country_text:
                idx = self.country_select_combo.findText(current_country_text, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                if idx != -1:
                    self.country_select_combo.setCurrentIndex(idx)
                else:
                    self.country_select_combo.lineEdit().setText(current_country_text) # For new/typed country

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))
        finally:
            self.country_select_combo.blockSignals(False)

        # Trigger city loading for the current country (either selected or typed)
        # This needs to be done after signals are unblocked.
        if self.country_select_combo.currentIndex() >= 0 :
             self.on_country_selected(self.country_select_combo.currentIndex())
        elif current_country_text :
             self.on_country_text_changed()


    def on_country_selected(self, index):
        country_id = self.country_select_combo.itemData(index)
        if country_id is not None:
            self.load_cities_for_country_by_id(country_id)
        # If country_id is None, it might be a placeholder or an issue.
        # Consider if text changed should be called if itemData is None.

    def on_country_text_changed(self):
        """Handles loading cities when country text is manually changed or entered."""
        country_name = self.country_select_combo.lineEdit().text().strip()
        if not country_name:
            self.city_select_combo.clear()
            return

        # Check if this country name exists in the combo's items (implies it has an ID)
        found_idx = self.country_select_combo.findText(country_name, Qt.MatchFixedString | Qt.MatchCaseSensitive)
        if found_idx != -1:
            country_id = self.country_select_combo.itemData(found_idx)
            if country_id is not None:
                self.load_cities_for_country_by_id(country_id)
            else: # Should not happen if item has text and is found
                self.city_select_combo.clear()
        else:
            # Country name is new/typed, does not have an ID in the combo yet.
            # We won't query cities for a country not yet in the DB.
            # City combo can be cleared or stay as is, depending on desired UX for "new" country.
            self.city_select_combo.clear() # Clear cities if country is unrecognized/new

    def load_cities_for_country_by_id(self, country_id):
        current_city_text = self.city_select_combo.lineEdit().text()
        self.city_select_combo.blockSignals(True)
        self.city_select_combo.clear()
        if country_id is None:
            self.city_select_combo.blockSignals(False)
            return
        try:
            cities = self.client_controller.get_cities_for_country(country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict['city_id'])

            if current_city_text: # Try to restore if it was being edited or is new
                idx = self.city_select_combo.findText(current_city_text, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                if idx != -1:
                    self.city_select_combo.setCurrentIndex(idx)
                else:
                    self.city_select_combo.lineEdit().setText(current_city_text)

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))
        finally:
            self.city_select_combo.blockSignals(False)


    def add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                # Use controller, which should handle get_or_add logic
                country_data = self.client_controller.add_country(country_text.strip())
                if country_data and country_data.get('country_id') is not None:
                    self.load_countries_into_combo() # Reloads all countries
                    # Attempt to find and set the newly added country
                    new_country_id = country_data['country_id']
                    for i in range(self.country_select_combo.count()):
                        if self.country_select_combo.itemData(i) == new_country_id:
                            self.country_select_combo.setCurrentIndex(i)
                            break
                else:
                    QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur d'ajout du pays. Le pays existe peut-être déjà ou une erreur s'est produite."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def add_new_city_dialog(self):
        current_country_name = self.country_select_combo.currentText().strip()
        current_country_id = self.country_select_combo.currentData() # This might be None if country is new

        if not current_country_name:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner ou entrer un pays."))
            return

        # If country_id is not available from combo (e.g., new country typed),
        # try to get/add it using the controller.
        if current_country_id is None:
            country_obj = self.client_controller.add_country(current_country_name) # Effectively get_or_add
            if country_obj and 'country_id' in country_obj:
                current_country_id = country_obj['country_id']
                # Refresh country combo to include this new country and its ID
                self.load_countries_into_combo()
                # Try to re-select it
                for i in range(self.country_select_combo.count()):
                    if self.country_select_combo.itemData(i) == current_country_id:
                        self.country_select_combo.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(self, self.tr("Erreur Pays"), self.tr(f"Impossible de trouver ou créer le pays '{current_country_name}' pour y ajouter une ville."))
                return

        if not current_country_id: # Still no ID after trying to add
             QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Un ID de pays valide est requis pour ajouter une ville."))
             return


        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                city_data = self.client_controller.add_city(city_text.strip(), current_country_id)
                if city_data and city_data.get('city_id') is not None:
                    self.load_cities_for_country_by_id(current_country_id) # Reload cities for the relevant country ID
                    new_city_id = city_data['city_id']
                    for i in range(self.city_select_combo.count()):
                        if self.city_select_combo.itemData(i) == new_city_id:
                            self.city_select_combo.setCurrentIndex(i)
                            break
                else:
                    QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur d'ajout de la ville. La ville existe peut-être déjà dans ce pays ou une erreur s'est produite."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def accept(self):
        # Perform UI validation only
        client_name = self.client_name_input.text().strip()
        if not client_name:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du client est requis."))
            self.client_name_input.setFocus()
            return

        country_name = self.country_select_combo.currentText().strip()
        if not country_name:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du pays est requis."))
            self.country_select_combo.setFocus()
            return

        # City is optional, so no validation needed unless specific rules apply
        # project_id is optional based on current setup

        super().accept() # This will allow get_data to be called

    def get_data(self):
        # Return raw text for country and city. Controller will handle resolution.
        client_name = self.client_name_input.text().strip()
        company_name = self.company_name_input.text().strip()
        client_need = self.client_need_input.text().strip()
        project_id_text = self.project_id_input_field.text().strip()

        country_name = self.country_select_combo.currentText().strip()
        city_name = self.city_select_combo.currentText().strip()

        selected_lang_display_text = self.language_select_combo.currentText()
        selected_languages_list = self.language_options_map.get(selected_lang_display_text, ["fr"])

        return {
            "client_name": client_name,
            "company_name": company_name,
            "primary_need_description": client_need,
            "country_name": country_name, # Raw name
            "city_name": city_name,       # Raw name
            "project_identifier": project_id_text,
            "selected_languages": ",".join(selected_languages_list)
            # client_status_id can be defaulted by the controller or main window
        }

```
