# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt

class MapClientDialog(QDialog):
    def __init__(self, country_name, parent=None):
        super().__init__(parent)
        self.country_name = country_name
        self.setWindowTitle(self.tr("Ajouter un Client pour ") + country_name)
        self.setMinimumWidth(400) # Set a reasonable minimum width
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Country Display (Non-editable)
        self.country_display_label = QLabel(self.country_name)
        # Optionally, style it to look different, e.g., slightly grayer background or bold
        # self.country_display_label.setStyleSheet("background-color: #f0f0f0; padding: 4px; border-radius: 3px;")
        form_layout.addRow(self.tr("Pays:"), self.country_display_label)

        # Input Fields
        self.client_name_input = QLineEdit()
        form_layout.addRow(self.tr("Nom du Client: *"), self.client_name_input)

        self.company_name_input = QLineEdit()
        form_layout.addRow(self.tr("Nom de l'Entreprise (Optionnel):"), self.company_name_input)

        self.city_input = QLineEdit()
        form_layout.addRow(self.tr("Ville: *"), self.city_input)

        self.project_identifier_input = QLineEdit()
        form_layout.addRow(self.tr("Identifiant Projet (Optionnel):"), self.project_identifier_input)

        self.primary_need_input = QLineEdit()
        form_layout.addRow(self.tr("Besoin Principal (Optionnel):"), self.primary_need_input)

        self.selected_languages_input = QLineEdit()
        self.selected_languages_input.setPlaceholderText(self.tr("ex: en,fr,ar"))
        form_layout.addRow(self.tr("Langues (séparées par virgule):"), self.selected_languages_input)

        main_layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Enregistrer"))
        self.save_button.clicked.connect(self.accept_dialog)
        self.cancel_button = QPushButton(self.tr("Annuler"))
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch() # Push buttons to the right
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def accept_dialog(self):
        client_name = self.client_name_input.text().strip()
        city_name = self.city_input.text().strip()

        if not client_name:
            QMessageBox.warning(self, self.tr("Champ Requis Manquant"), self.tr("Le nom du client ne peut pas être vide."))
            self.client_name_input.setFocus()
            return

        if not city_name:
            QMessageBox.warning(self, self.tr("Champ Requis Manquant"), self.tr("Le nom de la ville ne peut pas être vide."))
            self.city_input.setFocus()
            return

        self.accept()

    def get_data(self):
        return {
            "client_name": self.client_name_input.text().strip(),
            "company_name": self.company_name_input.text().strip(),
            "country_name": self.country_name, # Pre-filled country
            "city_name": self.city_input.text().strip(),
            "project_identifier": self.project_identifier_input.text().strip(),
            "primary_need_description": self.primary_need_input.text().strip(),
            "selected_languages": self.selected_languages_input.text().strip()
        }

if __name__ == '__main__':
    # Example Usage (for testing the dialog directly)
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = MapClientDialog("France")
    if dialog.exec_() == QDialog.Accepted:
        print("Dialog Accepted. Data:")
        print(dialog.get_data())
    else:
        print("Dialog Cancelled.")
    sys.exit(app.exec_())
