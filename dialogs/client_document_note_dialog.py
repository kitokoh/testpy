# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QCheckBox, QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

import db as db_manager

class ClientDocumentNoteDialog(QDialog):
    def __init__(self, client_id, note_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.note_data = note_data

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
        self.document_type_combo.addItems([
            "Proforma", "Packing List", "Sales Conditions",
            "Certificate of Origin", "Bill of Lading", "Other"
        ])
        form_layout.addRow(self.tr("Type de Document:"), self.document_type_combo)

        self.language_code_combo = QComboBox()
        self.language_code_combo.addItems(["fr", "en", "ar", "tr", "pt"])
        form_layout.addRow(self.tr("Code Langue:"), self.language_code_combo)

        self.note_content_edit = QTextEdit()
        self.note_content_edit.setPlaceholderText(self.tr("Saisissez le contenu de la note ici. Chaque ligne sera affichée comme un élément d'une liste numérotée."))
        self.note_content_edit.setMinimumHeight(100)
        form_layout.addRow(self.tr("Contenu de la Note:"), self.note_content_edit)

        self.is_active_checkbox = QCheckBox(self.tr("Active"))
        self.is_active_checkbox.setChecked(True)
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
        if self.note_data and 'note_id' in self.note_data:
            data['note_id'] = self.note_data['note_id']
        return data

    def accept(self):
        data = self.get_data()

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
            if self.note_data and 'note_id' in self.note_data:
                success = db_manager.update_client_document_note(self.note_data['note_id'], data)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Note de document mise à jour avec succès."))
                    super().accept()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de mettre à jour la note de document. Vérifiez pour les doublons (Client, Type, Langue) ou les erreurs de base de données."))
            else:
                note_id = db_manager.add_client_document_note(data)
                if note_id:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Note de document ajoutée avec succès (ID: {0}).").format(note_id))
                    super().accept()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'ajouter la note de document. Une note pour cette combinaison Client, Type et Langue existe peut-être déjà."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue: {0}").format(str(e)))
