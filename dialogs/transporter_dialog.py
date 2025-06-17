# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets (e.g QPushButton via QDialogButtonBox).

import db as db_manager

class TransporterDialog(QDialog):
    def __init__(self, transporter_data=None, parent=None):
        super().__init__(parent)
        self.transporter_data = transporter_data
        self.setWindowTitle(self.tr("Ajouter/Modifier Transporteur"))
        self.setMinimumWidth(400)
        self.setup_ui()
        if self.transporter_data:
            self.load_transporter_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        form_layout.addRow(self.tr("Nom:"), self.name_input)
        self.contact_person_input = QLineEdit()
        form_layout.addRow(self.tr("Personne à contacter:"), self.contact_person_input)
        self.phone_input = QLineEdit()
        form_layout.addRow(self.tr("Téléphone:"), self.phone_input)
        self.email_input = QLineEdit()
        form_layout.addRow(self.tr("Email:"), self.email_input)
        self.address_input = QLineEdit()
        form_layout.addRow(self.tr("Adresse:"), self.address_input)
        self.service_area_input = QLineEdit()
        form_layout.addRow(self.tr("Zone de service:"), self.service_area_input)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Notes:"), self.notes_input)

        self.latitude_input = QLineEdit()
        form_layout.addRow(self.tr("Latitude:"), self.latitude_input)
        self.longitude_input = QLineEdit()
        form_layout.addRow(self.tr("Longitude:"), self.longitude_input)
        self.current_cargo_input = QTextEdit() # Using QTextEdit for potentially longer text
        self.current_cargo_input.setFixedHeight(60)
        form_layout.addRow(self.tr("Current Cargo:"), self.current_cargo_input)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_transporter_data(self):
        self.name_input.setText(self.transporter_data.get('name', ''))
        self.contact_person_input.setText(self.transporter_data.get('contact_person', ''))
        self.phone_input.setText(self.transporter_data.get('phone', ''))
        self.email_input.setText(self.transporter_data.get('email', ''))
        self.address_input.setText(self.transporter_data.get('address', ''))
        self.service_area_input.setText(self.transporter_data.get('service_area', ''))
        self.notes_input.setPlainText(self.transporter_data.get('notes', ''))
        # Load new fields
        self.latitude_input.setText(str(self.transporter_data.get('latitude', '')))
        self.longitude_input.setText(str(self.transporter_data.get('longitude', '')))
        self.current_cargo_input.setPlainText(self.transporter_data.get('current_cargo', ''))

    def get_data(self):
        latitude_text = self.latitude_input.text().strip()
        longitude_text = self.longitude_input.text().strip()
        latitude = None
        longitude = None

        if latitude_text:
            try:
                latitude = float(latitude_text)
            except ValueError:
                # Error will be handled in accept() by checking if data['latitude'] is None
                pass

        if longitude_text:
            try:
                longitude = float(longitude_text)
            except ValueError:
                # Error will be handled in accept() by checking if data['longitude'] is None
                pass

        return {
            "name": self.name_input.text().strip(),
            "contact_person": self.contact_person_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.text().strip(),
            "service_area": self.service_area_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
            "latitude": latitude,
            "longitude": longitude,
            "current_cargo": self.current_cargo_input.toPlainText().strip()
        }

    def accept(self):
        data = self.get_data()
        if not data['name']:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du transporteur est requis."))
            self.name_input.setFocus()
            return

        # Validate latitude
        latitude_text = self.latitude_input.text().strip()
        if latitude_text and data['latitude'] is None: # Check if text was non-empty but conversion failed
            QMessageBox.warning(self, self.tr("Validation"), self.tr("La latitude doit être un nombre valide (ex: 45.678) ou vide."))
            self.latitude_input.setFocus()
            return

        # Validate longitude
        longitude_text = self.longitude_input.text().strip()
        if longitude_text and data['longitude'] is None: # Check if text was non-empty but conversion failed
            QMessageBox.warning(self, self.tr("Validation"), self.tr("La longitude doit être un nombre valide (ex: -73.123) ou vide."))
            self.longitude_input.setFocus()
            return

        try:
            if self.transporter_data and 'transporter_id' in self.transporter_data:
                success = db_manager.update_transporter(self.transporter_data['transporter_id'], data)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Transporteur mis à jour avec succès."))
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour le transporteur."))
                    return
            else:
                new_id = db_manager.add_transporter(data)
                if new_id:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Transporteur ajouté avec succès (ID: {0}).").format(new_id))
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter le transporteur."))
                    return
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue: {0}").format(str(e)))
