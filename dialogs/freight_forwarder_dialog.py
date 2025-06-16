# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

import db as db_manager

class FreightForwarderDialog(QDialog):
    def __init__(self, forwarder_data=None, parent=None):
        super().__init__(parent)
        self.forwarder_data = forwarder_data
        self.setWindowTitle(self.tr("Ajouter/Modifier Transitaire"))
        self.setMinimumWidth(400)
        self.setup_ui()
        if self.forwarder_data:
            self.load_forwarder_data()

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
        self.services_offered_input = QTextEdit()
        self.services_offered_input.setFixedHeight(60)
        form_layout.addRow(self.tr("Services Offerts:"), self.services_offered_input)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(60)
        form_layout.addRow(self.tr("Notes:"), self.notes_input)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_forwarder_data(self):
        self.name_input.setText(self.forwarder_data.get('name', ''))
        self.contact_person_input.setText(self.forwarder_data.get('contact_person', ''))
        self.phone_input.setText(self.forwarder_data.get('phone', ''))
        self.email_input.setText(self.forwarder_data.get('email', ''))
        self.address_input.setText(self.forwarder_data.get('address', ''))
        self.services_offered_input.setPlainText(self.forwarder_data.get('services_offered', ''))
        self.notes_input.setPlainText(self.forwarder_data.get('notes', ''))

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "contact_person": self.contact_person_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.text().strip(),
            "services_offered": self.services_offered_input.toPlainText().strip(),
            "notes": self.notes_input.toPlainText().strip()
        }

    def accept(self):
        data = self.get_data()
        if not data['name']:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom du transitaire est requis."))
            self.name_input.setFocus()
            return

        try:
            if self.forwarder_data and 'forwarder_id' in self.forwarder_data:
                success = db_manager.update_freight_forwarder(self.forwarder_data['forwarder_id'], data)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Transitaire mis à jour avec succès."))
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour le transitaire."))
                    return
            else:
                new_id = db_manager.add_freight_forwarder(data)
                if new_id:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Transitaire ajouté avec succès (ID: {0}).").format(new_id))
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter le transitaire."))
                    return
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue: {0}").format(str(e)))
