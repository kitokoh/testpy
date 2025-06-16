# -*- coding: utf-8 -*-
"""
Module for the StatisticsAddClientDialog class.
A multi-step wizard for adding a new client with detailed information.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton,
    QLabel, QFormLayout, QLineEdit, QComboBox, QProgressBar, QWidget,
    QMessageBox, QInputDialog, QCompleter
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt

# Attempt to import db_manager, provide a mock if it fails for standalone testing.
try:
    import db as db_manager # Assuming db.py contains all db_manager functions
    # Or from database import db_manager if that's the structure
except ImportError:
    print("WARNING: db_manager not found. Using mock db_manager for dialogs/statistics_add_client_dialog.py")
    class MockDBManager:
        def get_all_countries(self): return [{"country_name": "MockCountry1", "country_id": 1}, {"country_name": "MockCountry2", "country_id": 2}]
        def get_cities_by_country_id_alpha_sorted(self, country_id): return [{"city_name": f"MockCity{country_id}A", "city_id": 10+country_id}, {"city_name": f"MockCity{country_id}B", "city_id": 20+country_id}]
        def get_or_add_country(self, country_name): return {"country_name": country_name, "country_id": hash(country_name) % 1000}
        def get_or_add_city(self, city_name, country_id): return {"city_name": city_name, "city_id": hash(city_name) % 1000, "country_id": country_id}
        def get_country_by_name(self, country_name):
            if country_name == "MockCountry1": return {"country_name": "MockCountry1", "country_id": 1}
            if country_name == self._initial_country_name and hasattr(self, '_initial_country_name'):
                 return {"country_name": self._initial_country_name, "country_id": hash(self._initial_country_name) % 1000}
            return None
        def add_country(self, country_data): # Simpler version for the add dialog
            print(f"Mock adding country: {country_data['country_name']}")
            return hash(country_data['country_name']) % 1000
        def get_all_cities(self, country_id): # adapting from add_new_client_dialog
            return self.get_cities_by_country_id_alpha_sorted(country_id)


    db_manager = MockDBManager()


class StatisticsAddClientDialog(QDialog):
    """
    Dialog for adding a new client to the statistics.
    It's a multi-step wizard.
    """
    LANGUAGE_OPTIONS_MAP = {
        "English only (en)": ["en"],
        "French only (fr)": ["fr"],
        "Arabic only (ar)": ["ar"],
        "Turkish only (tr)": ["tr"],
        "Portuguese only (pt)": ["pt"],
        "Russian only (ru)": ["ru"],
        "All supported languages (en, fr, ar, tr, pt, ru)": ["en", "fr", "ar", "tr", "pt", "ru"]
    }
    # Fallback language if selection fails
    DEFAULT_LANGUAGES = ["fr"]


    def __init__(self, initial_country_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Client Wizard")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)

        self._initial_country_name = initial_country_name
        if hasattr(db_manager, isinstance(db_manager, object)) and not isinstance(db_manager, type): # Check if it's an instance
             db_manager._initial_country_name = initial_country_name # For mock

        self._current_step = 0
        self._client_data = {}
        self.country_id = None
        self.city_id = None

        self.setup_ui()
        self._load_countries_into_combo() # Load countries initially
        self._handle_initial_country() # Handle pre-selection after countries are loaded

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 3)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.step_titles_label = QLabel()
        self.step_titles_label.setAlignment(Qt.AlignCenter)
        font = self.step_titles_label.font()
        font.setBold(True)
        self.step_titles_label.setFont(font)
        main_layout.addWidget(self.step_titles_label)

        self.stacked_widget = QStackedWidget(self)
        main_layout.addWidget(self.stacked_widget)

        self._step1_widget = self._setup_step1_client_project_info()
        self._step2_widget = self._setup_step2_location_info()
        self._step3_widget = self._setup_step3_language_selection()
        self._step4_widget = self._setup_step4_summary()

        self.stacked_widget.addWidget(self._step1_widget)
        self.stacked_widget.addWidget(self._step2_widget)
        self.stacked_widget.addWidget(self._step3_widget)
        self.stacked_widget.addWidget(self._step4_widget)

        buttons_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self._go_to_previous_step)
        buttons_layout.addWidget(self.prev_button)
        buttons_layout.addStretch()
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._go_to_next_step)
        buttons_layout.addWidget(self.next_button)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.finish_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        self._update_button_states()
        self._update_step_title_and_progress()

    def _setup_step1_client_project_info(self) -> QWidget:
        page_widget = QWidget()
        layout = QFormLayout(page_widget)
        layout.setSpacing(10)

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Client's full name or key identifier")
        layout.addRow("Client Name*:", self.client_name_input)

        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Company name (optional)")
        layout.addRow("Company Name:", self.company_name_input)

        self.client_need_input = QLineEdit()
        self.client_need_input.setPlaceholderText("Brief description of client's primary need")
        layout.addRow("Client Need:", self.client_need_input)

        self.project_identifier_input = QLineEdit()
        self.project_identifier_input.setPlaceholderText("Unique project ID or code (optional)")
        layout.addRow("Project ID:", self.project_identifier_input)

        page_widget.setLayout(layout)
        return page_widget

    def _setup_step2_location_info(self) -> QWidget:
        page_widget = QWidget()
        layout = QFormLayout(page_widget)
        layout.setSpacing(10)

        country_hbox_layout = QHBoxLayout()
        self.country_select_combo = QComboBox()
        self.country_select_combo.setEditable(True)
        self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.currentTextChanged.connect(self._on_country_selected)
        country_hbox_layout.addWidget(self.country_select_combo)

        self.add_country_button = QPushButton("+")
        self.add_country_button.setFixedSize(30, self.country_select_combo.sizeHint().height())
        self.add_country_button.setToolTip("Add a new country")
        self.add_country_button.clicked.connect(self._add_new_country_dialog)
        country_hbox_layout.addWidget(self.add_country_button)
        layout.addRow("Country*:", country_hbox_layout)

        city_hbox_layout = QHBoxLayout()
        self.city_select_combo = QComboBox()
        self.city_select_combo.setEditable(True)
        self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)

        self.add_city_button = QPushButton("+")
        self.add_city_button.setFixedSize(30, self.city_select_combo.sizeHint().height())
        self.add_city_button.setToolTip("Add a new city")
        self.add_city_button.clicked.connect(self._add_new_city_dialog)
        city_hbox_layout.addWidget(self.add_city_button)
        layout.addRow("City (Optional):", city_hbox_layout)

        page_widget.setLayout(layout)
        return page_widget

    def _setup_step3_language_selection(self) -> QWidget:
        page_widget = QWidget()
        layout = QFormLayout(page_widget)
        layout.setSpacing(10)

        self.language_select_combo = QComboBox()
        self.language_select_combo.setToolTip("Select languages for document folders and template generation.")
        self.language_select_combo.addItems(list(self.LANGUAGE_OPTIONS_MAP.keys()))
        layout.addRow("Languages:", self.language_select_combo)

        page_widget.setLayout(layout)
        return page_widget

    def _setup_step4_summary(self) -> QWidget:
        page_widget = QWidget()
        layout = QVBoxLayout(page_widget)
        self.summary_label = QLabel("Review your entries before finishing.")
        self.summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        page_widget.setLayout(layout)
        return page_widget

    def _load_countries_into_combo(self):
        current_country_text = self.country_select_combo.lineEdit().text() if self.country_select_combo.isEditable() else self.country_select_combo.currentText()
        self.country_select_combo.blockSignals(True)
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))

            # Restore previous text if it was being edited or if it's a new country
            if self._initial_country_name and self.country_select_combo.findText(self._initial_country_name, Qt.MatchFixedString | Qt.MatchCaseSensitive) == -1 :
                 if self.country_select_combo.lineEdit(): self.country_select_combo.lineEdit().setText(self._initial_country_name)
            elif current_country_text:
                 idx = self.country_select_combo.findText(current_country_text, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                 if idx != -1:
                     self.country_select_combo.setCurrentIndex(idx)
                 elif self.country_select_combo.isEditable() and self.country_select_combo.lineEdit():
                      self.country_select_combo.lineEdit().setText(current_country_text)
        except Exception as e:
            QMessageBox.warning(self, "DB Error", f"Error loading countries:\n{str(e)}")
        finally:
            self.country_select_combo.blockSignals(False)
            # Manually trigger city loading if a country is now selected (e.g. initial or restored)
            if self.country_select_combo.currentText():
                self._on_country_selected(self.country_select_combo.currentText())


    def _handle_initial_country(self):
        if self._initial_country_name:
            country_index = self.country_select_combo.findText(self._initial_country_name, Qt.MatchFixedString | Qt.MatchCaseSensitive)
            if country_index >= 0:
                self.country_select_combo.setCurrentIndex(country_index)
                # _on_country_selected will be called due to currentTextChanged via setCurrentIndex
            else:
                if self.country_select_combo.lineEdit(): # Check if lineEdit exists
                    self.country_select_combo.lineEdit().setText(self._initial_country_name)
                # _on_country_selected will be called for the typed text

    def _on_country_selected(self, country_text: str):
        self.city_select_combo.clear() # Clear cities when country changes
        country_id_to_load = None

        selected_country_id_from_combo = self.country_select_combo.currentData()
        if selected_country_id_from_combo is not None and self.country_select_combo.currentText() == country_text:
            country_id_to_load = selected_country_id_from_combo
        elif country_text: # Country name might be new or different from combo's currentData
            country_obj_by_name = db_manager.get_country_by_name(country_text)
            if country_obj_by_name:
                country_id_to_load = country_obj_by_name['country_id']

        if country_id_to_load:
            self._load_cities_for_country(country_id_to_load)
        # If no country_id_to_load, city combo remains empty (new country not yet in DB)

    def _load_cities_for_country(self, country_id):
        current_city_text = self.city_select_combo.lineEdit().text() if self.city_select_combo.isEditable() else self.city_select_combo.currentText()
        self.city_select_combo.blockSignals(True)
        self.city_select_combo.clear()
        try:
            # Assuming get_all_cities(country_id=...) is preferred, like in add_new_client_dialog.py
            cities = db_manager.get_all_cities(country_id=country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))

            if current_city_text: # Try to restore previous city text
                idx = self.city_select_combo.findText(current_city_text, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                if idx != -1:
                    self.city_select_combo.setCurrentIndex(idx)
                elif self.city_select_combo.isEditable() and self.city_select_combo.lineEdit():
                    self.city_select_combo.lineEdit().setText(current_city_text)

        except Exception as e:
            QMessageBox.warning(self, "DB Error", f"Error loading cities:\n{str(e)}")
        finally:
            self.city_select_combo.blockSignals(False)

    def _add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, "New Country", "Enter new country name:")
        if ok and country_text.strip():
            try:
                # In the original dialog, it was db_manager.add_country({'country_name': ...})
                # Let's assume db_manager.get_or_add_country is robust for this.
                country_data = db_manager.get_or_add_country(country_text.strip())
                if country_data and country_data.get('country_id') is not None:
                    self._load_countries_into_combo() # Reload all countries
                    index = self.country_select_combo.findData(country_data['country_id'])
                    if index >= 0:
                        self.country_select_combo.setCurrentIndex(index)
                    else: # Fallback to text match if ID not found (should not happen if data is consistent)
                        index_by_text = self.country_select_combo.findText(country_text.strip())
                        if index_by_text >=0: self.country_select_combo.setCurrentIndex(index_by_text)

                else:
                    QMessageBox.critical(self, "DB Error", "Failed to add country. Check logs.")
            except Exception as e:
                QMessageBox.critical(self, "Unexpected Error", f"An error occurred: {str(e)}")

    def _add_new_city_dialog(self):
        current_country_id = self.country_select_combo.currentData()
        current_country_name = self.country_select_combo.currentText()

        final_country_id_for_city = current_country_id
        if not final_country_id_for_city and current_country_name: # Country typed but not in DB yet
            country_data = db_manager.get_or_add_country(current_country_name)
            if country_data and country_data.get('country_id'):
                final_country_id_for_city = country_data['country_id']
                self._load_countries_into_combo() # Refresh countries
                idx = self.country_select_combo.findData(final_country_id_for_city)
                if idx != -1: self.country_select_combo.setCurrentIndex(idx)
            else:
                 QMessageBox.warning(self, "Country Required", "Please select or add a valid country first.")
                 return

        if not final_country_id_for_city:
            QMessageBox.warning(self, "Country Required", "Please select or add a valid country first.")
            return

        city_text, ok = QInputDialog.getText(self, "New City", f"Enter new city name for {current_country_name}:")
        if ok and city_text.strip():
            try:
                city_data = db_manager.get_or_add_city(city_name=city_text.strip(), country_id=final_country_id_for_city)
                if city_data and city_data.get('city_id') is not None:
                    self._load_cities_for_country(final_country_id_for_city) # Reload cities for this country
                    index = self.city_select_combo.findData(city_data['city_id'])
                    if index >= 0:
                        self.city_select_combo.setCurrentIndex(index)
                    else: # Fallback
                        index_by_text = self.city_select_combo.findText(city_text.strip())
                        if index_by_text >=0: self.city_select_combo.setCurrentIndex(index_by_text)

                else:
                    QMessageBox.critical(self, "DB Error", "Failed to add or retrieve city. Check logs.")
            except Exception as e:
                QMessageBox.critical(self, "Unexpected Error", f"An error occurred: {str(e)}")

    def _validate_current_step(self) -> bool:
        if self._current_step == 0: # Client & Project Info
            if not self.client_name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Client Name is required.")
                self.client_name_input.setFocus()
                return False
        elif self._current_step == 1: # Location Info
            if not self.country_select_combo.currentText().strip():
                QMessageBox.warning(self, "Validation Error", "Country is required.")
                self.country_select_combo.setFocus()
                return False
        # Add more step validations as needed
        return True

    def _update_button_states(self):
        self.prev_button.setEnabled(self._current_step > 0)
        is_last_step = self._current_step == self.stacked_widget.count() - 1

        self.next_button.setVisible(not is_last_step)
        self.finish_button.setVisible(is_last_step)
        # Finish button should only be enabled if validation of summary (or all data) passes
        # For now, just enable it on the last step. Real validation happens in accept().
        self.finish_button.setEnabled(is_last_step)
        self.next_button.setEnabled(not is_last_step)

    def _update_step_title_and_progress(self):
        self.progress_bar.setValue(self._current_step)
        step_titles = [
            "Step 1/4: Client & Project Information",
            "Step 2/4: Location Information",
            "Step 3/4: Language Selection",
            "Step 4/4: Summary & Confirmation"
        ]
        if 0 <= self._current_step < len(step_titles):
            self.step_titles_label.setText(step_titles[self._current_step])
            self.progress_bar.setFormat(f"{step_titles[self._current_step]}")


    @pyqtSlot()
    def _go_to_next_step(self):
        if not self._validate_current_step():
            return

        if self._current_step < self.stacked_widget.count() - 1:
            self._current_step += 1
            self.stacked_widget.setCurrentIndex(self._current_step)
            self._update_button_states()
            self._update_step_title_and_progress()
            if self._current_step == self.stacked_widget.count() - 1: # Summary step
                self._update_summary_tab()

    @pyqtSlot()
    def _go_to_previous_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self.stacked_widget.setCurrentIndex(self._current_step)
            self._update_button_states()
            self._update_step_title_and_progress()

    def _update_summary_tab(self):
        client_name = self.client_name_input.text().strip()
        company_name = self.company_name_input.text().strip()
        client_need = self.client_need_input.text().strip()
        project_id = self.project_identifier_input.text().strip()
        country = self.country_select_combo.currentText().strip()
        city = self.city_select_combo.currentText().strip()
        language_display = self.language_select_combo.currentText()

        summary_text = (
            f"<b>Client Name:</b> {client_name or 'N/A'}<br/>"
            f"<b>Company Name:</b> {company_name or 'N/A'}<br/>"
            f"<b>Client Need:</b> {client_need or 'N/A'}<br/>"
            f"<b>Project ID:</b> {project_id or 'N/A'}<br/>"
            f"<b>Country:</b> {country or 'N/A'}<br/>"
            f"<b>City:</b> {city or 'N/A'}<br/>"
            f"<b>Languages:</b> {language_display or 'N/A'}<br/><br/>"
            "Please review the information above. Click 'Finish' to add the client."
        )
        self.summary_label.setText(summary_text)

    def accept(self):
        # Final validation before accepting
        if not self.client_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Client Name is required. Please go back to Step 1.")
            self.stacked_widget.setCurrentIndex(0) # Go to step 1
            self._current_step = 0
            self._update_button_states()
            self._update_step_title_and_progress()
            return

        country_name = self.country_select_combo.currentText().strip()
        if not country_name:
            QMessageBox.warning(self, "Validation Error", "Country is required. Please go back to Step 2.")
            self.stacked_widget.setCurrentIndex(1) # Go to step 2
            self._current_step = 1
            self._update_button_states()
            self._update_step_title_and_progress()
            return

        # Process country
        country_id_from_combo = self.country_select_combo.currentData()
        final_country_id = country_id_from_combo
        if final_country_id is None or self.country_select_combo.currentText() != self.country_select_combo.itemText(self.country_select_combo.currentIndex()): # Check if text was typed or doesn't match item
            try:
                country_data = db_manager.get_or_add_country(country_name)
                if country_data and country_data.get('country_id'):
                    final_country_id = country_data['country_id']
                else:
                    QMessageBox.warning(self, "Country Error", f"Could not determine or add country: {country_name}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "DB Error", f"Error processing country: {str(e)}")
                return
        self.country_id = final_country_id

        # Process city (optional, but if provided, process it)
        city_name = self.city_select_combo.currentText().strip()
        final_city_id = None # Default to None for city
        if city_name:
            city_id_from_combo = self.city_select_combo.currentData()
            final_city_id = city_id_from_combo
            if final_city_id is None or self.city_select_combo.currentText() != self.city_select_combo.itemText(self.city_select_combo.currentIndex()):
                try:
                    city_data = db_manager.get_or_add_city(city_name, self.country_id)
                    if city_data and city_data.get('city_id'):
                        final_city_id = city_data['city_id']
                    # If city adding fails for an optional city, we might allow it to be None
                    # For now, if typed, we expect it to be processed or it's an issue.
                    elif city_name: # Only warn if user actually typed something that failed
                         QMessageBox.warning(self, "City Error", f"Could not determine or add city: {city_name}. It will be left blank.")
                         final_city_id = None
                except Exception as e:
                    QMessageBox.critical(self, "DB Error", f"Error processing city: {str(e)}")
                    # Decide if this is a fatal error for the dialog
                    final_city_id = None # Treat as non-fatal, city becomes None

        self.city_id = final_city_id

        super().accept() # All good, proceed to close the dialog with QDialog.Accepted

    def get_data(self) -> dict:
        client_name = self.client_name_input.text().strip()
        company_name = self.company_name_input.text().strip()
        client_need = self.client_need_input.text().strip()
        project_identifier = self.project_identifier_input.text().strip()

        selected_lang_display_text = self.language_select_combo.currentText()
        # Use .get with a default value for safety, though keys should exist
        selected_languages_list = self.LANGUAGE_OPTIONS_MAP.get(selected_lang_display_text, self.DEFAULT_LANGUAGES)

        return {
            "client_name": client_name,
            "company_name": company_name,
            "primary_need_description": client_need,
            "project_identifier": project_identifier,
            "country_id": self.country_id,
            "country_name": self.country_select_combo.currentText().strip(), # Current text for display
            "city_id": self.city_id,
            "city_name": self.city_select_combo.currentText().strip(), # Current text for display
            "selected_languages": ",".join(selected_languages_list) # Store as comma-separated string
        }

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Test without initial country
    dialog1 = StatisticsAddClientDialog()
    # dialog1.show() # Uncomment to test

    # Test with an initial country that might be in the mock DB
    dialog2 = StatisticsAddClientDialog(initial_country_name="MockCountry1")
    # dialog2.show() # Uncomment to test

    # Test with an initial country that is new
    dialog3 = StatisticsAddClientDialog(initial_country_name="NewTestCountry")
    dialog3.show()

    sys.exit(app.exec_())
