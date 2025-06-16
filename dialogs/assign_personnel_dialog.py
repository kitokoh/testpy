# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

import db as db_manager

class AssignPersonnelDialog(QDialog):
    def __init__(self, client_id, role_filter, company_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.role_filter = role_filter
        self.company_id = company_id

        self.setWindowTitle(self.tr("Assigner Personnel au Client"))
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_available_personnel()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.personnel_combo = QComboBox()
        form_layout.addRow(self.tr("Personnel Disponible:"), self.personnel_combo)

        self.role_in_project_edit = QLineEdit()
        self.role_in_project_edit.setPlaceholderText(self.tr("Ex: Vendeur principal, Support Technique"))
        form_layout.addRow(self.tr("Rôle pour ce Client/Projet:"), self.role_in_project_edit)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Assigner"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_available_personnel(self):
        self.personnel_combo.clear()
        try:
            personnel_list = db_manager.get_personnel_for_company(self.company_id, role=self.role_filter)
            if not personnel_list: # personnel_list could be None or empty list
                self.personnel_combo.addItem(self.tr("Aucun personnel disponible pour ce filtre."), None)
                self.personnel_combo.setEnabled(False)
                return

            self.personnel_combo.setEnabled(True) # Ensure it's enabled if there was data
            for p in personnel_list:
                display_text = f"{p.get('name', 'N/A')} ({p.get('role', 'N/A')})"
                self.personnel_combo.addItem(display_text, p.get('personnel_id'))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de charger le personnel: {0}").format(str(e)))
            self.personnel_combo.setEnabled(False)

    def accept(self):
        selected_personnel_id = self.personnel_combo.currentData()
        role_in_project_text = self.role_in_project_edit.text().strip()

        if selected_personnel_id is None: # Check if data is None (e.g. "Aucun personnel..." item)
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez sélectionner un membre du personnel."))
            self.personnel_combo.setFocus()
            return

        if not role_in_project_text:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez définir un rôle pour ce personnel pour ce client/projet."))
            self.role_in_project_edit.setFocus()
            return

        try:
            assignment_id = db_manager.assign_personnel_to_client(
                client_id=self.client_id,
                personnel_id=selected_personnel_id,
                role_in_project=role_in_project_text
            )
            if assignment_id:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Personnel assigné avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec Assignation"),
                                    self.tr("Impossible d'assigner le personnel. Vérifiez s'il est déjà assigné avec ce rôle ou consultez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue: {0}").format(str(e)))
